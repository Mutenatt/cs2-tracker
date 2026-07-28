"""
Onboarding de registro (wizard post-login): encuesta demográfica corta
(estudio de mercado) + auto-fetch de matchmaking + amistad con el bot de
Steam, los tres obligatorios antes de dar por completado el registro.

La obligatoriedad se enforcea acá, server-side, releyendo la DB en
`/complete` -- nunca se confía en lo que mande el cliente.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import DemographicsIn, OnboardingStatusOut
from cs2tracker.auth import get_current_steamid
from cs2tracker.config import settings
from cs2tracker.db import User
from cs2tracker.db.session import get_engine
from cs2tracker.infra.gc_client import get_bot_steamid

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _demographics_completed(user: User) -> bool:
    return bool(user.age_bucket and user.country and user.acquisition_channel and user.primary_goal)


def _status_out(user: User) -> OnboardingStatusOut:
    return OnboardingStatusOut(
        demographics_completed=_demographics_completed(user),
        autofetch_linked=user.autofetch_status == "active",
        bot_friend_added_at=user.bot_friend_added_at,
        bot_steamid=get_bot_steamid(base_url=settings.gc_sidecar_url),
        onboarding_completed_at=user.onboarding_completed_at,
    )


@router.get("/status", response_model=OnboardingStatusOut)
def onboarding_status(steamid: str = Depends(get_current_steamid)) -> OnboardingStatusOut:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        return _status_out(user)


@router.post("/demographics", response_model=OnboardingStatusOut)
def onboarding_demographics(
    body: DemographicsIn, steamid: str = Depends(get_current_steamid)
) -> OnboardingStatusOut:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        user.age_bucket = body.age_bucket
        user.country = body.country.strip()
        user.acquisition_channel = body.acquisition_channel
        user.primary_goal = body.primary_goal
        s.commit()
        return _status_out(user)


@router.post("/complete", response_model=OnboardingStatusOut)
def onboarding_complete(steamid: str = Depends(get_current_steamid)) -> OnboardingStatusOut:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")

        faltan = []
        if not _demographics_completed(user):
            faltan.append("encuesta demográfica")
        if user.autofetch_status != "active":
            faltan.append("conectar matchmaking")
        if not user.bot_friend_added_at:
            faltan.append("agregar de amigo al bot de Steam")
        if faltan:
            raise HTTPException(400, f"faltan pasos: {', '.join(faltan)}")

        user.onboarding_completed_at = datetime.now(UTC).isoformat()
        s.commit()
        return _status_out(user)
