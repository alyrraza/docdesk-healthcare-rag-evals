"""Tests for auth/passwords.py (AC-AUTH-01)."""

from __future__ import annotations

from docdesk.auth.passwords import hash_password, verify_password


def test_ac_auth_01_password_is_hashed() -> None:
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert "correct horse" not in hashed


def test_ac_auth_01_hash_is_salted() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_ac_auth_01_correct_password_verifies() -> None:
    assert verify_password("s3cret-pass", hash_password("s3cret-pass")) is True


def test_ac_auth_01_wrong_password_fails() -> None:
    assert verify_password("wrong", hash_password("s3cret-pass")) is False


def test_ac_auth_01_malformed_hash_fails_instead_of_raising() -> None:
    assert verify_password("anything", "not-a-real-hash") is False
