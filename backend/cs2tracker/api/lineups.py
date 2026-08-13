"""
Line ups (granadas) por mapa: fuente única para el explorador web
(frontend/src/views/LineUps.tsx) y el overlay de escritorio (ver app/).
Solo lectura por ahora -- la curación de contenido sigue viviendo en el
seed (scripts/seed_lineups.py); no hay endpoints de escritura todavía
porque no existe un concepto de rol admin en este proyecto.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import LineupMapEntry, LineupMapsResponse, LineupOut
from cs2tracker.auth import get_current_actor
from cs2tracker.db import Lineup
from cs2tracker.db.session import get_engine
from cs2tracker.infra.r2 import presigned_video_url

router = APIRouter(prefix="/lineups", tags=["lineups"])


def _to_out(row: Lineup) -> LineupOut:
    # video_url sale presignado (URL absoluta y temporal) porque el bucket es
    # privado -- ver infra/r2.py. Sin credenciales R2 configuradas (dev sin
    # .env completo) queda el path crudo tal cual estaba en la fila; no
    # sirve para reproducir el video, pero no rompe el resto de la respuesta.
    video_url = presigned_video_url(row.video_url) or row.video_url
    return LineupOut(
        id=row.id,
        map=row.map,
        category=row.category,
        team=row.team,
        label=row.label,
        x=row.x,
        y=row.y,
        start_x=row.start_x,
        start_y=row.start_y,
        video_url=video_url,
        instructions=row.instructions,
        crosshair_note=row.crosshair_note,
    )


@router.get("", response_model=list[LineupOut])
def list_lineups(
    map: str | None = None,
    team: str | None = None,
    category: str | None = None,
    _actor: str = Depends(get_current_actor),
) -> list[LineupOut]:
    with Session(get_engine()) as s:
        q = select(Lineup)
        if map is not None:
            q = q.where(Lineup.map == map)
        if team is not None:
            q = q.where(Lineup.team == team)
        if category is not None:
            q = q.where(Lineup.category == category)
        rows = s.execute(q.order_by(Lineup.label)).scalars().all()
        return [_to_out(r) for r in rows]


@router.get("/maps", response_model=LineupMapsResponse)
def list_lineup_maps(_actor: str = Depends(get_current_actor)) -> LineupMapsResponse:
    """Mapas con al menos un lineup cargado y cuántos -- así el overlay puede
    armar su selector de mapa sin traer todas las filas primero."""
    with Session(get_engine()) as s:
        rows = s.execute(
            select(Lineup.map, func.count()).group_by(Lineup.map).order_by(Lineup.map)
        ).all()
        return LineupMapsResponse(maps=[LineupMapEntry(map=m, count=c) for m, c in rows])
