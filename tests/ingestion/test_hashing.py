"""The content hash is how identical uploads are recognised (AC-ING-04)."""

from __future__ import annotations

from docdesk.ingestion.hashing import content_hash


def test_ac_ing_04_hash_matches_the_published_sha256_of_abc() -> None:
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert content_hash(b"abc") == expected


def test_ac_ing_04_identical_bytes_give_identical_hashes() -> None:
    assert content_hash(b"Aspirin label") == content_hash(b"Aspirin label")


def test_ac_ing_04_one_changed_byte_gives_a_different_hash() -> None:
    assert content_hash(b"Aspirin label") != content_hash(b"Aspirin labeL")


def test_ac_ing_04_hash_fits_the_64_character_column() -> None:
    digest = content_hash(b"")
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")
