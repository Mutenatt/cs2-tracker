"""Test de las rutas /auth/* de login por email+contraseña en api/account.py
(register, verify-email, resend-verification, login, forgot-password,
reset-password). Cero cobertura previa -- test_auth.py solo cubre el flujo
Steam OpenID. send_email se mockea en vez de pegarle a SMTP real, mismo
criterio que fetch_profile ya mockeado en test_auth.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth_password import (
    PENDING_COOKIE_NAME,
    create_password_reset_token,
    create_pending_cookie,
    hash_password,
)
from cs2tracker.db import AccountSignup, Player, User
from cs2tracker.db.session import init_db


@pytest.fixture()
def engine(tmp_path):
    return init_db(f"sqlite:///{tmp_path}/t.sqlite")


@pytest.fixture()
def client(engine):
    return TestClient(app)


@pytest.fixture()
def sent_emails(monkeypatch):
    """Captura las llamadas a send_email en vez de pegarle a SMTP real."""
    calls = []

    def fake_send_email(to, subject, body):
        calls.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr("cs2tracker.api.account.send_email", fake_send_email)
    return calls


def _make_pending(engine, *, email="pendiente@test.local", password="password123", verified=False):
    with Session(engine) as s:
        pending = AccountSignup(
            email=email,
            password_hash=hash_password(password),
            email_verified_at=datetime.now(UTC).isoformat() if verified else None,
            created_at=datetime.now(UTC).isoformat(),
        )
        s.add(pending)
        s.commit()
        s.refresh(pending)
        return pending.id


def _make_user(
    engine, *, steamid="76561198000000001", email="user@test.local", password="password123"
):
    with Session(engine) as s:
        s.add(Player(steamid=steamid, name="Ana"))
        s.add(
            User(
                steamid=steamid,
                display_name="Ana",
                email=email,
                password_hash=hash_password(password),
                email_verified_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()


# --- register ---------------------------------------------------------


def test_register_feliz_crea_pending_y_manda_email(client, engine, sent_emails):
    r = client.post("/auth/register", json={"email": "nueva@test.local", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["pending"] is True
    assert body["email"] == "nueva@test.local"
    assert PENDING_COOKIE_NAME in r.cookies

    with Session(engine) as s:
        pending = s.query(AccountSignup).filter(AccountSignup.email == "nueva@test.local").first()
        assert pending is not None
        assert pending.email_verified_at is None

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "nueva@test.local"


def test_register_email_duplicado_en_users_409(client, engine, sent_emails):
    _make_user(engine, email="ya-existe@test.local")
    r = client.post(
        "/auth/register", json={"email": "ya-existe@test.local", "password": "password123"}
    )
    assert r.status_code == 409


def test_register_email_duplicado_en_pending_409(client, engine, sent_emails):
    _make_pending(engine, email="pendiente@test.local")
    r = client.post(
        "/auth/register", json={"email": "pendiente@test.local", "password": "password123"}
    )
    assert r.status_code == 409


def test_register_password_corta_400(client, sent_emails):
    r = client.post("/auth/register", json={"email": "nueva@test.local", "password": "corta"})
    assert r.status_code == 400
    assert len(sent_emails) == 0


def test_register_email_invalido_400(client, sent_emails):
    r = client.post("/auth/register", json={"email": "no-es-un-email", "password": "password123"})
    assert r.status_code == 400


# --- verify-email -------------------------------------------------------


def test_verify_email_feliz_redirige_con_verified(client, engine):
    from cs2tracker.auth_password import create_email_verify_token

    pending_id = _make_pending(engine)
    token = create_email_verify_token(pending_id)
    r = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "verified=1" in r.headers["location"]

    with Session(engine) as s:
        pending = s.get(AccountSignup, pending_id)
        assert pending.email_verified_at is not None


def test_verify_email_token_invalido_redirige_con_error(client):
    r = client.get("/auth/verify-email?token=no-es-valido", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "verify_error=invalid_or_expired" in r.headers["location"]


# --- resend-verification -------------------------------------------------


def test_resend_verification_requiere_sesion_pending(client):
    r = client.post("/auth/resend-verification")
    assert r.status_code == 401


def test_resend_verification_manda_email(client, engine, sent_emails):
    pending_id = _make_pending(engine)
    client.cookies.set(PENDING_COOKIE_NAME, create_pending_cookie(pending_id))
    r = client.post("/auth/resend-verification")
    assert r.status_code == 200
    assert len(sent_emails) == 1


def test_resend_verification_ya_verificado_no_manda_email(client, engine, sent_emails):
    pending_id = _make_pending(engine, verified=True)
    client.cookies.set(PENDING_COOKIE_NAME, create_pending_cookie(pending_id))
    r = client.post("/auth/resend-verification")
    assert r.status_code == 200
    assert len(sent_emails) == 0


# --- login ---------------------------------------------------------------


def test_login_user_real_feliz(client, engine):
    _make_user(engine, email="user@test.local", password="password123")
    r = client.post("/auth/login", json={"email": "user@test.local", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is False
    assert body["me"]["pending"] is False
    assert body["me"]["email"] == "user@test.local"
    assert body["me"]["totp_enabled"] is False


def test_login_pending_sin_vincular_feliz(client, engine):
    _make_pending(engine, email="pendiente@test.local", password="password123", verified=True)
    r = client.post(
        "/auth/login", json={"email": "pendiente@test.local", "password": "password123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is False
    assert body["me"]["pending"] is True


def test_login_password_incorrecta_401(client, engine):
    _make_user(engine, email="user@test.local", password="password123")
    r = client.post("/auth/login", json={"email": "user@test.local", "password": "incorrecta"})
    assert r.status_code == 401


def test_login_email_inexistente_401(client, engine):
    r = client.post("/auth/login", json={"email": "no-existe@test.local", "password": "cualquiera"})
    assert r.status_code == 401


# --- forgot-password (no-enumeración) ------------------------------------


def test_forgot_password_email_existente_manda_email(client, engine, sent_emails):
    _make_user(engine, email="user@test.local")
    r = client.post("/auth/forgot-password", json={"email": "user@test.local"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert len(sent_emails) == 1


def test_forgot_password_email_inexistente_misma_respuesta_sin_mandar_email(client, sent_emails):
    r = client.post("/auth/forgot-password", json={"email": "no-existe@test.local"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert len(sent_emails) == 0


def test_forgot_password_pending_tambien_manda_email(client, engine, sent_emails):
    _make_pending(engine, email="pendiente@test.local", verified=True)
    r = client.post("/auth/forgot-password", json={"email": "pendiente@test.local"})
    assert r.status_code == 200
    assert len(sent_emails) == 1


# --- reset-password --------------------------------------------------------


def test_reset_password_feliz_user(client, engine):
    _make_user(engine, steamid="76561198000000002", email="user2@test.local", password="vieja12345")
    token = create_password_reset_token("user", "76561198000000002")
    r = client.post("/auth/reset-password", json={"token": token, "new_password": "nueva12345"})
    assert r.status_code == 200

    r2 = client.post("/auth/login", json={"email": "user2@test.local", "password": "nueva12345"})
    assert r2.status_code == 200


def test_reset_password_token_invalido_400(client):
    r = client.post(
        "/auth/reset-password", json={"token": "no-es-valido", "new_password": "nueva12345"}
    )
    assert r.status_code == 400


def test_reset_password_corta_400(client, engine):
    _make_user(engine, steamid="76561198000000003", email="user3@test.local")
    token = create_password_reset_token("user", "76561198000000003")
    r = client.post("/auth/reset-password", json={"token": token, "new_password": "corta"})
    assert r.status_code == 400


# --- rate limiting / lockout ------------------------------------------------


def test_login_bloquea_cuenta_tras_5_fallos(client, engine):
    _make_user(engine, email="lockout@test.local", password="password123")
    for _ in range(5):
        r = client.post(
            "/auth/login", json={"email": "lockout@test.local", "password": "incorrecta"}
        )
        assert r.status_code == 401
    # 6to intento: la cuenta ya está bloqueada, ni siquiera se verifica la
    # password (incluso con la password CORRECTA, sigue bloqueada).
    r = client.post("/auth/login", json={"email": "lockout@test.local", "password": "password123"})
    assert r.status_code == 423


def test_login_exitoso_resetea_el_contador_de_fallos(client, engine):
    _make_user(engine, email="reset@test.local", password="password123")
    for _ in range(4):
        client.post("/auth/login", json={"email": "reset@test.local", "password": "incorrecta"})
    r = client.post("/auth/login", json={"email": "reset@test.local", "password": "password123"})
    assert r.status_code == 200

    with Session(engine) as s:
        user = s.query(User).filter(User.email == "reset@test.local").first()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


def test_login_supera_rate_limit_por_ip_429(client, engine):
    _make_user(engine, email="rl@test.local", password="password123")
    for _ in range(20):
        client.post("/auth/login", json={"email": "rl@test.local", "password": "password123"})
    r = client.post("/auth/login", json={"email": "rl@test.local", "password": "password123"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_register_supera_rate_limit_por_ip_429(client, sent_emails):
    for i in range(5):
        client.post(
            "/auth/register", json={"email": f"nueva{i}@test.local", "password": "password123"}
        )
    r = client.post(
        "/auth/register", json={"email": "unamas@test.local", "password": "password123"}
    )
    assert r.status_code == 429


def test_forgot_password_supera_rate_limit_por_email_429(client, engine, sent_emails):
    _make_user(engine, email="forgot-rl@test.local")
    for _ in range(3):
        client.post("/auth/forgot-password", json={"email": "forgot-rl@test.local"})
    r = client.post("/auth/forgot-password", json={"email": "forgot-rl@test.local"})
    assert r.status_code == 429


def test_resend_verification_supera_rate_limit_por_pending_429(client, engine, sent_emails):
    pending_id = _make_pending(engine)
    client.cookies.set(PENDING_COOKIE_NAME, create_pending_cookie(pending_id))
    for _ in range(3):
        client.post("/auth/resend-verification")
    r = client.post("/auth/resend-verification")
    assert r.status_code == 429


# --- logout-all --------------------------------------------------------


def test_logout_all_invalida_otras_sesiones_no_la_propia(client, engine):
    from cs2tracker.auth import COOKIE_NAME

    _make_user(engine, steamid="76561198000000010", email="multi@test.local")
    r1 = client.post("/auth/login", json={"email": "multi@test.local", "password": "password123"})
    session_a_cookie = r1.cookies.get(COOKIE_NAME)

    other_client = TestClient(app)
    other_client.cookies.set(COOKIE_NAME, session_a_cookie)
    assert other_client.get("/auth/me").status_code == 200

    client.cookies.set(COOKIE_NAME, session_a_cookie)
    r2 = client.post("/auth/logout-all")
    assert r2.status_code == 200
    new_cookie = r2.cookies.get(COOKIE_NAME)
    assert new_cookie != session_a_cookie

    # La otra sesión (cookie vieja, nunca actualizada) queda invalidada.
    assert other_client.get("/auth/me").status_code == 401

    # El dispositivo que ejecutó logout-all sigue logueado con la cookie nueva.
    client.cookies.set(COOKIE_NAME, new_cookie)
    assert client.get("/auth/me").status_code == 200


def test_logout_all_requiere_sesion(client):
    r = client.post("/auth/logout-all")
    assert r.status_code == 401


# --- audit log (login_events) + login-history + notificación -------------


def test_login_exitoso_crea_login_event(client, engine):
    from cs2tracker.db import LoginEvent

    _make_user(engine, steamid="76561198000000020", email="events@test.local")
    client.post("/auth/login", json={"email": "events@test.local", "password": "password123"})

    with Session(engine) as s:
        events = s.query(LoginEvent).filter(LoginEvent.steamid == "76561198000000020").all()
        assert len(events) == 1
        assert events[0].success is True
        assert events[0].reason == "ok"


def test_login_fallido_crea_login_event_bad_password(client, engine):
    from cs2tracker.db import LoginEvent

    _make_user(engine, steamid="76561198000000021", email="events2@test.local")
    client.post("/auth/login", json={"email": "events2@test.local", "password": "incorrecta"})

    with Session(engine) as s:
        events = s.query(LoginEvent).filter(LoginEvent.steamid == "76561198000000021").all()
        assert len(events) == 1
        assert events[0].success is False
        assert events[0].reason == "bad_password"


def test_login_history_solo_devuelve_eventos_propios(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000030", email="owner@test.local")
    _make_user(engine, steamid="76561198000000031", email="other@test.local")

    client.post("/auth/login", json={"email": "owner@test.local", "password": "password123"})
    client.post("/auth/login", json={"email": "other@test.local", "password": "password123"})

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000030", epoch=0))
    r = client.get("/auth/login-history")
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 1
    assert events[0]["reason"] == "ok"


def test_login_manda_notificacion_de_ip_nueva_una_sola_vez(client, engine, sent_emails):
    _make_user(engine, steamid="76561198000000040", email="notify@test.local")
    client.post("/auth/login", json={"email": "notify@test.local", "password": "password123"})
    assert len(sent_emails) == 1
    assert "Nuevo inicio de sesión" in sent_emails[0]["subject"]

    sent_emails.clear()
    client.post("/auth/login", json={"email": "notify@test.local", "password": "password123"})
    assert len(sent_emails) == 0


# --- change-password ---------------------------------------------------


def test_change_password_requiere_sesion(client):
    r = client.post(
        "/auth/change-password",
        json={"current_password": "x", "new_password": "nueva12345"},
    )
    assert r.status_code == 401


def test_change_password_feliz_invalida_otras_sesiones(client, engine):
    from cs2tracker.auth import COOKIE_NAME

    _make_user(engine, steamid="76561198000000050", email="cp@test.local", password="vieja12345")
    r_login = client.post("/auth/login", json={"email": "cp@test.local", "password": "vieja12345"})
    old_cookie = r_login.cookies.get(COOKIE_NAME)

    other_client = TestClient(app)
    other_client.cookies.set(COOKIE_NAME, old_cookie)
    assert other_client.get("/auth/me").status_code == 200

    client.cookies.set(COOKIE_NAME, old_cookie)
    r = client.post(
        "/auth/change-password",
        json={"current_password": "vieja12345", "new_password": "nueva12345"},
    )
    assert r.status_code == 200
    new_cookie = r.cookies.get(COOKIE_NAME)
    assert new_cookie != old_cookie

    # otra sesión con la cookie vieja queda invalidada
    assert other_client.get("/auth/me").status_code == 401

    # el dispositivo que hizo el cambio sigue logueado con la cookie nueva
    client.cookies.set(COOKIE_NAME, new_cookie)
    assert client.get("/auth/me").status_code == 200

    # la password nueva funciona para loguear de nuevo
    r2 = client.post("/auth/login", json={"email": "cp@test.local", "password": "nueva12345"})
    assert r2.status_code == 200


def test_change_password_actual_incorrecta_401(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000051", email="cp2@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000051", epoch=0))
    r = client.post(
        "/auth/change-password",
        json={"current_password": "incorrecta", "new_password": "nueva12345"},
    )
    assert r.status_code == 401


def test_change_password_corta_400(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000052", email="cp3@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000052", epoch=0))
    r = client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "corta"},
    )
    assert r.status_code == 400


# --- change-email --------------------------------------------------------


def test_change_email_requiere_sesion(client):
    r = client.post("/auth/change-email", json={"new_email": "nuevo@test.local", "password": "x"})
    assert r.status_code == 401


def test_change_email_no_cambia_hasta_confirmar(client, engine, sent_emails):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000060", email="old@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000060", epoch=0))
    r = client.post(
        "/auth/change-email", json={"new_email": "new@test.local", "password": "password123"}
    )
    assert r.status_code == 200
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "new@test.local"

    with Session(engine) as s:
        user = s.get(User, "76561198000000060")
        assert user.email == "old@test.local"
        assert user.pending_email == "new@test.local"

    # todavía se loguea con el email viejo, no con el nuevo
    r2 = client.post("/auth/login", json={"email": "old@test.local", "password": "password123"})
    assert r2.status_code == 200


def test_change_email_password_incorrecta_401(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000061", email="pw@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000061", epoch=0))
    r = client.post(
        "/auth/change-email", json={"new_email": "nuevo@test.local", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_change_email_duplicado_409(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000062", email="a@test.local")
    _make_user(engine, steamid="76561198000000063", email="b@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000062", epoch=0))
    r = client.post(
        "/auth/change-email", json={"new_email": "b@test.local", "password": "password123"}
    )
    assert r.status_code == 409


def test_verify_email_change_feliz_aplica_el_cambio(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie
    from cs2tracker.auth_password import create_email_change_token

    _make_user(engine, steamid="76561198000000064", email="old2@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000064", epoch=0))
    client.post(
        "/auth/change-email", json={"new_email": "new2@test.local", "password": "password123"}
    )

    token = create_email_change_token("76561198000000064", "new2@test.local")
    r = client.get(f"/auth/verify-email-change?token={token}", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "email_changed=1" in r.headers["location"]

    with Session(engine) as s:
        user = s.get(User, "76561198000000064")
        assert user.email == "new2@test.local"
        assert user.pending_email is None

    r2 = client.post("/auth/login", json={"email": "new2@test.local", "password": "password123"})
    assert r2.status_code == 200


def test_verify_email_change_token_obsoleto_rechazado(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie
    from cs2tracker.auth_password import create_email_change_token

    _make_user(engine, steamid="76561198000000065", email="old3@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000065", epoch=0))
    # token para un cambio a "primero@test.local"...
    stale_token = create_email_change_token("76561198000000065", "primero@test.local")
    # ...pero el usuario después pidió cambiar a otra dirección distinta.
    client.post(
        "/auth/change-email", json={"new_email": "segundo@test.local", "password": "password123"}
    )

    r = client.get(f"/auth/verify-email-change?token={stale_token}", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "email_change_error=invalid_or_expired" in r.headers["location"]

    with Session(engine) as s:
        user = s.get(User, "76561198000000065")
        assert user.email == "old3@test.local"


# --- delete-account --------------------------------------------------------


def test_delete_account_requiere_sesion(client):
    r = client.post("/auth/delete-account", json={"password": "x"})
    assert r.status_code == 401


def test_delete_account_password_incorrecta_401(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000070", email="del@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000070", epoch=0))
    r = client.post("/auth/delete-account", json={"password": "incorrecta"})
    assert r.status_code == 401

    with Session(engine) as s:
        assert s.get(User, "76561198000000070") is not None


def test_delete_account_no_rompe_historial_compartido(client, engine):
    """Caso crítico: borrar la cuenta de A no debe afectar la visibilidad
    de B sobre una partida que jugaron juntos -- matches/match_players
    FKean a players.steamid, no a users.steamid."""
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie
    from cs2tracker.db import Match, MatchPlayer

    _make_user(engine, steamid="76561198000000071", email="a@shared.local", password="password123")
    _make_user(engine, steamid="76561198000000072", email="b@shared.local", password="password123")

    with Session(engine) as s:
        s.add(
            Match(
                match_id="shared1",
                demo_file="x.dem",
                map="de_ancient",
                n_rounds=20,
                ingested_at="2026-01-01T00:00:00Z",
            )
        )
        s.add(MatchPlayer(match_id="shared1", steamid="76561198000000071", team_num=2))
        s.add(MatchPlayer(match_id="shared1", steamid="76561198000000072", team_num=3))
        s.commit()

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000071", epoch=0))
    r = client.post("/auth/delete-account", json={"password": "password123"})
    assert r.status_code == 200

    with Session(engine) as s:
        assert s.get(User, "76561198000000071") is None
        # el steamid de A sigue existiendo como Player (no se borra)
        assert s.get(Player, "76561198000000071") is not None

    # B (que sigue existiendo) todavía puede ver la partida compartida
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000072", epoch=0))
    r2 = client.get("/matches/shared1")
    assert r2.status_code == 200


def test_delete_account_borra_clips_del_usuario(client, engine, tmp_path):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie
    from cs2tracker.db import ClipJob, Match

    _make_user(
        engine, steamid="76561198000000073", email="clips@test.local", password="password123"
    )
    clip_file = tmp_path / "clip_1.mp4"
    clip_file.write_bytes(b"fake mp4")

    with Session(engine) as s:
        s.add(
            Match(
                match_id="m_clip",
                demo_file="x.dem",
                map="de_ancient",
                n_rounds=20,
                ingested_at="2026-01-01T00:00:00Z",
            )
        )
        s.add(
            ClipJob(
                steamid="76561198000000073",
                match_id="m_clip",
                round_num=1,
                label="ace",
                status="done",
                file_path=str(clip_file),
                created_at="2026-01-01T00:00:00Z",
            )
        )
        s.commit()

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000073", epoch=0))
    r = client.post("/auth/delete-account", json={"password": "password123"})
    assert r.status_code == 200
    assert not clip_file.exists()

    with Session(engine) as s:
        assert s.query(ClipJob).filter(ClipJob.steamid == "76561198000000073").count() == 0


# --- steam relink -----------------------------------------------------


def _relink_fake_async_client(new_steamid):
    """Mismo patrón de mock que test_auth.py: verify_callback llama a
    httpx.AsyncClient para chequear la respuesta de Steam server-to-server."""

    class _FakeResponse:
        def __init__(self, text):
            self.text = text
            self.status_code = 200

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None):
            return _FakeResponse("is_valid:true\n")

    return lambda **kw: _FakeAsyncClient()


def test_steam_relink_start_requiere_sesion(client):
    r = client.post("/auth/steam/relink/start", json={"password": "x"})
    assert r.status_code == 401


def test_steam_relink_start_password_incorrecta_401(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie

    _make_user(engine, steamid="76561198000000080", email="relink@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000080", epoch=0))
    r = client.post("/auth/steam/relink/start", json={"password": "incorrecta"})
    assert r.status_code == 401


def test_steam_relink_start_feliz_devuelve_redirect_url(client, engine):
    from cs2tracker.auth import COOKIE_NAME, create_session_cookie
    from cs2tracker.auth_password import RELINK_COOKIE_NAME

    _make_user(engine, steamid="76561198000000081", email="relink2@test.local")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000081", epoch=0))
    r = client.post("/auth/steam/relink/start", json={"password": "password123"})
    assert r.status_code == 200
    assert "steamcommunity.com" in r.json()["redirect_url"]
    assert RELINK_COOKIE_NAME in r.cookies


def test_steam_relink_callback_feliz_migra_la_cuenta(client, engine, monkeypatch):
    from cs2tracker.auth_password import RELINK_COOKIE_NAME, create_relink_cookie

    _make_user(
        engine,
        steamid="76561198000000090",
        email="migrate@test.local",
        password="password123",
    )

    async def fake_fetch_profile(steamid):
        return ("Nuevo Nombre", "https://x/avatar.jpg", None)

    monkeypatch.setattr("cs2tracker.api.account.fetch_profile", fake_fetch_profile)
    monkeypatch.setattr(
        "cs2tracker.auth.httpx.AsyncClient", _relink_fake_async_client("76561198000000091")
    )

    client.cookies.set(RELINK_COOKIE_NAME, create_relink_cookie("76561198000000090"))
    claimed_id = "https://steamcommunity.com/openid/id/76561198000000091"
    r = client.get(
        f"/auth/steam/relink/callback?openid.claimed_id={claimed_id}", follow_redirects=False
    )
    assert r.status_code in (302, 307)
    assert "relinked=1" in r.headers["location"]

    with Session(engine) as s:
        assert s.get(User, "76561198000000090") is None
        new_user = s.get(User, "76561198000000091")
        assert new_user is not None
        assert new_user.email == "migrate@test.local"
        assert new_user.display_name == "Nuevo Nombre"
        # el steamid viejo sigue existiendo como Player
        assert s.get(Player, "76561198000000090") is not None

    # la cuenta migrada sigue logueando con el mismo email/password
    r2 = client.post("/auth/login", json={"email": "migrate@test.local", "password": "password123"})
    assert r2.status_code == 200
    assert r2.json()["me"]["steamid"] == "76561198000000091"


def test_steam_relink_callback_steamid_ya_usado_por_otra_cuenta(client, engine, monkeypatch):
    from cs2tracker.auth_password import RELINK_COOKIE_NAME, create_relink_cookie

    _make_user(engine, steamid="76561198000000092", email="own@test.local")
    _make_user(engine, steamid="76561198000000093", email="taken@test.local")

    monkeypatch.setattr(
        "cs2tracker.auth.httpx.AsyncClient", _relink_fake_async_client("76561198000000093")
    )

    client.cookies.set(RELINK_COOKIE_NAME, create_relink_cookie("76561198000000092"))
    claimed_id = "https://steamcommunity.com/openid/id/76561198000000093"
    r = client.get(
        f"/auth/steam/relink/callback?openid.claimed_id={claimed_id}", follow_redirects=False
    )
    assert r.status_code in (302, 307)
    assert "relink_error=steam_already_linked_elsewhere" in r.headers["location"]

    with Session(engine) as s:
        assert s.get(User, "76561198000000092") is not None


def test_steam_relink_callback_mismo_steamid_es_noop(client, engine, monkeypatch):
    from cs2tracker.auth_password import RELINK_COOKIE_NAME, create_relink_cookie

    _make_user(engine, steamid="76561198000000094", email="same@test.local")
    monkeypatch.setattr(
        "cs2tracker.auth.httpx.AsyncClient", _relink_fake_async_client("76561198000000094")
    )
    client.cookies.set(RELINK_COOKIE_NAME, create_relink_cookie("76561198000000094"))
    claimed_id = "https://steamcommunity.com/openid/id/76561198000000094"
    r = client.get(
        f"/auth/steam/relink/callback?openid.claimed_id={claimed_id}", follow_redirects=False
    )
    assert r.status_code in (302, 307)
    assert "relink_noop=1" in r.headers["location"]

    with Session(engine) as s:
        assert s.get(User, "76561198000000094") is not None
