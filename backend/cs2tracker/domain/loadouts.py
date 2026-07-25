"""
Tabla LOADOUTS de la landing de armas (estilo tracker.gg): agrega K/D,
ADR, ACS, DDΔ, KAST%, ESR%, kills y deaths POR TIPO DE COMPRA
(pistol/full_buy/semi_buy/eco). PURA -- recibe filas ya resueltas por
ronda (ver api/queries.py::loadout_breakdown_inputs).

Umbrales propios de ESTA vista (LOADOUT_FULL_MIN/LOADOUT_SEMI_MIN),
deliberadamente separados de economia.py::clasificar_tipo_compra (que
sirve a los badges con otros cortes) para no romper esa clasificación si
mañana se ajusta esta tabla.
"""

from __future__ import annotations

LOADOUT_FULL_MIN = 3900
LOADOUT_SEMI_MIN = 1000

# Asume Premier/MR12 estándar (mitad a la ronda 12) -- el demo no expone la
# config real de MR. Overtime en CS2 es MR3 por lado, arranca en la ronda
# 24 y se repite cada 6. Limitación conocida: un MR no estándar puede
# clasificar mal el pistol de la 2da mitad/OT (no bloqueante para esta
# vista, es una tabla informativa, no un badge).
REGULATION_HALF_LEN = 12
OT_HALF_LEN = 3
OT_START = 2 * REGULATION_HALF_LEN

TIERS = ("pistol", "full_buy", "semi_buy", "eco")

# ACS/DDΔ no existen como dato real del juego -- son métricas propias de
# Riot/tracker.gg sin fórmula pública. Esto es una aproximación PROPIA, NO
# el ACS oficial de ningún juego: combina el ADR de ese tier con un bonus
# por ronda de kills/assists, en una escala parecida a un ADR típico para
# que se lea similar a lo que muestra tracker.gg.
ACS_KILL_BONUS = 70
ACS_ASSIST_BONUS = 20


def is_pistol_round(round_num: int) -> bool:
    """Ronda de arranque de mitad (regulation o cualquier OT)."""
    if round_num in (0, REGULATION_HALF_LEN):
        return True
    if round_num < OT_START:
        return False
    return (round_num - OT_START) % OT_HALF_LEN == 0


def loadout_tier(round_num: int, equip_value: int) -> str:
    """'pistol' | 'full_buy' | 'semi_buy' | 'eco'. Pistol pisa a los demás
    cortes por equip_value: es la ronda, no la plata, lo que la define."""
    if is_pistol_round(round_num):
        return "pistol"
    if equip_value >= LOADOUT_FULL_MIN:
        return "full_buy"
    if equip_value >= LOADOUT_SEMI_MIN:
        return "semi_buy"
    return "eco"


def aggregate_loadout_stats(rows: list[dict], lifetime_adr: float) -> list[dict]:
    """`rows`: una fila por (partida, ronda, jugador) ya resuelta, con
    `tier`, `kills`, `deaths`, `assists`, `damage`, `kast` (bool),
    `entry_attempt`/`entry_win` (bool). Devuelve SIEMPRE las 4 filas de
    TIERS, aunque el jugador tenga 0 rondas en alguna (la tabla del
    frontend siempre muestra Pistol/Full/Semi/Eco)."""
    by_tier: dict[str, list[dict]] = {t: [] for t in TIERS}
    for r in rows:
        if r.get("tier") in by_tier:
            by_tier[r["tier"]].append(r)

    out = []
    for tier in TIERS:
        trows = by_tier[tier]
        n = len(trows)
        kills = sum(r["kills"] for r in trows)
        deaths = sum(r["deaths"] for r in trows)
        assists = sum(r.get("assists", 0) for r in trows)
        damage = sum(r["damage"] for r in trows)
        kast_n = sum(1 for r in trows if r.get("kast"))
        entry_attempts = sum(1 for r in trows if r.get("entry_attempt"))
        entry_wins = sum(1 for r in trows if r.get("entry_win"))

        adr = round(damage / n, 1) if n else 0.0
        kills_per_round = kills / n if n else 0.0
        assists_per_round = assists / n if n else 0.0
        acs = (
            round(adr + kills_per_round * ACS_KILL_BONUS + assists_per_round * ACS_ASSIST_BONUS, 1)
            if n
            else 0.0
        )

        out.append(
            {
                "tier": tier,
                "rounds": n,
                "kills": kills,
                "deaths": deaths,
                "kd": round(kills / deaths, 2) if deaths else float(kills),
                "adr": adr,
                "acs": acs,
                "dd": round(adr - lifetime_adr, 1) if n else 0.0,
                "kast_pct": round(100.0 * kast_n / n, 1) if n else 0.0,
                "esr_pct": round(100.0 * entry_wins / entry_attempts, 1) if entry_attempts else 0.0,
            }
        )
    return out
