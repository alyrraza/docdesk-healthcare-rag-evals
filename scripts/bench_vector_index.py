"""Measure exact search, HNSW and IVFFlat on random vectors in the TEST database (T027).

Why this exists: the index choice in DECISIONS.md must come from a measurement, not a guess.
Server side execution time is read from EXPLAIN ANALYZE so the network round trip to the
hosted database does not hide the difference between indexes.

Usage:
    python scripts/bench_vector_index.py [rows] [queries]

It only reads TEST_DATABASE_URL and drops its own temporary table when done.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import psycopg
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

DIM = 384
K = 10
TABLE = "bench_vectors"


def connect_to_test_database() -> psycopg.Connection:
    """Open a connection to TEST_DATABASE_URL and refuse any database not ending in _test."""
    url = make_url(dotenv_values(Path(".env"))["TEST_DATABASE_URL"])
    if not (url.database or "").endswith("_test"):
        raise SystemExit("refusing to run: database name must end in _test")
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    return psycopg.connect(dsn, autocommit=True)


def clustered_unit_vectors(count: int, seed: int) -> np.ndarray:
    """Make unit vectors grouped around 200 topics, like real embeddings (not uniform noise).

    Uniform random vectors have no structure, which is the worst case for approximate
    indexes and would understate their recall. The topic centers use a fixed seed so
    documents and queries share the same topics.
    """
    centers = np.random.default_rng(0).normal(size=(200, DIM)).astype(np.float32)
    rng = np.random.default_rng(seed)
    picked = centers[rng.integers(0, len(centers), size=count)]
    vectors = picked + 0.6 * rng.normal(size=(count, DIM)).astype(np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def literal(vector: np.ndarray) -> str:
    """Format a vector the way pgvector reads text input."""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


def load_rows(conn: psycopg.Connection, vectors: np.ndarray) -> None:
    """Create the temporary table and bulk load the vectors with COPY."""
    conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
    conn.execute(f"CREATE TABLE {TABLE} (id int PRIMARY KEY, embedding vector({DIM}))")
    with conn.cursor().copy(f"COPY {TABLE} (id, embedding) FROM STDIN") as copy:
        for row_id, vector in enumerate(vectors):
            copy.write_row((row_id, literal(vector)))
    conn.execute(f"ANALYZE {TABLE}")


def top_ids(conn: psycopg.Connection, query: np.ndarray) -> list[int]:
    """Return the ids of the K nearest rows by cosine distance."""
    sql = f"SELECT id FROM {TABLE} ORDER BY embedding <=> %s::vector LIMIT {K}"
    return [row[0] for row in conn.execute(sql, (literal(query),)).fetchall()]


def server_ms(conn: psycopg.Connection, query: np.ndarray) -> float:
    """Read the server side execution time of one search from EXPLAIN ANALYZE."""
    sql = (
        f"EXPLAIN (ANALYZE, FORMAT JSON) SELECT id FROM {TABLE} "
        f"ORDER BY embedding <=> %s::vector LIMIT {K}"
    )
    plan = conn.execute(sql, (literal(query),)).fetchone()[0]
    plan = plan if isinstance(plan, list) else json.loads(plan)
    return float(plan[0]["Execution Time"])


def measure(conn: psycopg.Connection, queries: np.ndarray, truth: list[set[int]]) -> dict:
    """Time every query and compute recall@K against the exact answers."""
    times = [server_ms(conn, q) for q in queries]
    pairs = zip(queries, truth, strict=True)
    hits = [len(set(top_ids(conn, q)) & expected) / K for q, expected in pairs]
    ordered = sorted(times)
    return {
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(ordered[int(0.95 * (len(ordered) - 1))], 2),
        "recall_at_10": round(statistics.mean(hits), 3),
    }


def build(conn: psycopg.Connection, sql: str) -> float:
    """Run an index build and return the seconds it took."""
    start = time.perf_counter()
    conn.execute(sql)
    return round(time.perf_counter() - start, 1)


def main(rows: int, query_count: int) -> None:
    """Load data, measure each index type and print one JSON report."""
    conn = connect_to_test_database()
    load_rows(conn, clustered_unit_vectors(rows, seed=1))
    queries = clustered_unit_vectors(query_count, seed=2)
    report: dict[str, dict] = {}
    try:
        truth = [set(top_ids(conn, q)) for q in queries]
        report["exact_no_index"] = measure(conn, queries, truth)
        ops = "embedding vector_cosine_ops"
        seconds = build(
            conn,
            f"CREATE INDEX bench_hnsw ON {TABLE} USING hnsw ({ops}) "
            "WITH (m = 16, ef_construction = 64)",
        )
        for ef_search in (40, 100):
            conn.execute(f"SET hnsw.ef_search = {ef_search}")
            report[f"hnsw_m16_ef{ef_search}"] = {
                "build_s": seconds, **measure(conn, queries, truth)
            }
        conn.execute("DROP INDEX bench_hnsw")
        lists = max(10, int(rows**0.5))
        seconds = build(
            conn,
            f"CREATE INDEX bench_ivf ON {TABLE} USING ivfflat ({ops}) WITH (lists = {lists})",
        )
        for probes in (1, 10, 30):
            conn.execute(f"SET ivfflat.probes = {probes}")
            report[f"ivfflat_lists{lists}_probes{probes}"] = {
                "build_s": seconds, **measure(conn, queries, truth)
            }
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
        conn.close()
    summary = {"rows": rows, "queries": query_count, "dim": DIM, "results": report}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    row_count = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    main(row_count, int(sys.argv[2]) if len(sys.argv) > 2 else 50)
