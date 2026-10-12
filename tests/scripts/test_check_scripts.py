"""Tests for the three enforcement scripts in scripts/."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_commit_msg as commit  # noqa: E402
import check_docs_style as docs  # noqa: E402
import check_file_length as length  # noqa: E402

EM = "—"
EN = "–"


def test_file_over_limit_is_reported(tmp_path: Path) -> None:
    big = tmp_path / "src" / "big.py"
    big.parent.mkdir()
    big.write_text("x = 1\n" * (length.SRC_LIMIT + 1), encoding="utf-8")
    assert length.find_offenders([big])


def test_file_at_limit_passes(tmp_path: Path) -> None:
    ok = tmp_path / "src" / "ok.py"
    ok.parent.mkdir()
    ok.write_text("x = 1\n" * length.SRC_LIMIT, encoding="utf-8")
    assert length.find_offenders([ok]) == []


def test_tests_get_a_larger_limit(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_big.py"
    t.parent.mkdir()
    t.write_text("x = 1\n" * (length.SRC_LIMIT + 50), encoding="utf-8")
    assert length.find_offenders([t]) == []


def test_unchecked_suffix_is_ignored(tmp_path: Path) -> None:
    f = tmp_path / "notes.txt"
    f.write_text("x\n" * 5000, encoding="utf-8")
    assert length.find_offenders([f]) == []


def test_em_dash_is_flagged(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text(f"hello {EM} world\n", encoding="utf-8")
    assert docs.scan_file(f) == [(1, "em dash")]


def test_en_dash_is_flagged(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text(f"pages 1{EN}5\n", encoding="utf-8")
    assert docs.scan_file(f) == [(1, "en dash")]


def test_plain_hyphen_is_fine(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("well-known - fine\n", encoding="utf-8")
    assert docs.scan_file(f) == []


def test_good_commit_subject() -> None:
    assert commit.check_subject("feat(auth): add password hashing module") is None


def test_scope_is_optional() -> None:
    assert commit.check_subject("docs: update plan") is None


def test_bad_type_is_rejected() -> None:
    assert commit.check_subject("update stuff") is not None


def test_long_subject_is_rejected() -> None:
    assert commit.check_subject("feat: " + "x" * 80) is not None


def test_merge_commits_pass_through() -> None:
    assert commit.check_subject("Merge branch 'main'") is None


def test_comment_lines_are_skipped_when_reading_subject() -> None:
    assert commit.first_line("# comment\n\nfix(api): handle 401\n") == "fix(api): handle 401"


def test_cache_dir_is_skipped_by_both_scans(tmp_path: Path, monkeypatch) -> None:
    cached = tmp_path / ".cache" / "tmp"
    cached.mkdir(parents=True)
    (cached / "a.md").write_text(f"x {EM} y\n", encoding="utf-8")
    (cached / "big.py").write_text("x = 1\n" * 500, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert docs.collect([]) == []
    assert length.find_offenders([cached / "big.py"]) == []
