"""Test de auth_password.py: login por email+contraseña, tokens firmados
(pending-session, email-verify, password-reset). Cero cobertura previa --
ver auth_password.py::_serializer, cada token usa un salt propio derivado
del mismo CS2_SESSION_SECRET, así que el caso más importante acá es probar
que un token de un tipo NUNCA pasa la verificación de otro tipo."""

from __future__ import annotations

import pytest

from cs2tracker.auth_password import (
    create_email_verify_token,
    create_password_reset_token,
    create_pending_cookie,
    hash_password,
    is_valid_email,
    normalize_email,
    read_email_verify_token,
    read_password_reset_token,
    read_pending_cookie,
    verify_password,
)


def test_normalize_email_recorta_y_pone_en_minuscula():
    assert normalize_email("  Ana@Test.LOCAL  ") == "ana@test.local"


@pytest.mark.parametrize(
    "email,valid",
    [
        ("ana@test.local", True),
        ("ana.b+tag@test.local", True),
        ("no-arroba", False),
        ("sin-tld@localhost", False),
        ("@test.local", False),
        ("ana@", False),
    ],
)
def test_is_valid_email(email, valid):
    assert is_valid_email(email) is valid


def test_hash_password_no_guarda_en_claro():
    h = hash_password("una-password-segura")
    assert h != "una-password-segura"
    assert verify_password("una-password-segura", h) is True


def test_verify_password_rechaza_password_incorrecta():
    h = hash_password("correcta")
    assert verify_password("incorrecta", h) is False


def test_pending_cookie_roundtrip():
    cookie = create_pending_cookie(42)
    assert read_pending_cookie(cookie) == 42


def test_pending_cookie_invalida():
    assert read_pending_cookie("no-es-valida") is None
    assert read_pending_cookie(None) is None


def test_email_verify_token_roundtrip():
    token = create_email_verify_token(7)
    assert read_email_verify_token(token) == 7


def test_email_verify_token_invalido():
    assert read_email_verify_token("no-es-valido") is None


def test_password_reset_token_roundtrip_user():
    token = create_password_reset_token("user", "76561198000000000")
    assert read_password_reset_token(token) == ("user", "76561198000000000")


def test_password_reset_token_roundtrip_pending():
    token = create_password_reset_token("pending", "7")
    assert read_password_reset_token(token) == ("pending", "7")


def test_password_reset_token_invalido():
    assert read_password_reset_token("no-es-valido") is None


def test_tokens_de_distinto_tipo_no_son_intercambiables():
    """El motivo de tener 3 serializers con salt propio: un token pending no
    debe pasar como email-verify, y viceversa, aunque el payload interno
    (un id numérico) sea compatible en forma."""
    pending_token = create_pending_cookie(1)
    assert read_email_verify_token(pending_token) is None
    assert read_password_reset_token(pending_token) is None

    verify_token = create_email_verify_token(1)
    assert read_pending_cookie(verify_token) is None
    assert read_password_reset_token(verify_token) is None

    reset_token = create_password_reset_token("user", "1")
    assert read_pending_cookie(reset_token) is None
    assert read_email_verify_token(reset_token) is None
