"""
Percentiles globales entre jugadores y tags de perfil derivados de
comparar la ventana de un usuario contra esos percentiles. PURA -- recibe
listas/dicts ya agregados (ver api/queries.py::recompute_global_percentiles),
no toca la DB.

Los percentiles se calculan en Python (no func.percentile_cont) a
propósito: portable SQLite/Postgres, y la cantidad de jugadores es chica
(una fila por jugador, no por partida).
"""

from __future__ import annotations

# Con menos jugadores que esto en la base, un percentil global no significa
# nada ("estás en el p90 de 4 personas") -- mismo espíritu que MIN_SAMPLE /
# MIN_JUGADORES_RELATIVO.
MIN_JUGADORES_GLOBAL = 20

PERCENTILES = (25, 50, 75, 90)


def calcular_percentiles(valores: list[float]) -> dict[str, float]:
    """{p25, p50, p75, p90} por interpolación lineal (mismo método que
    numpy.percentile default). Lista vacía -> todos 0.0."""
    if not valores:
        return {f"p{p}": 0.0 for p in PERCENTILES}
    orden = sorted(valores)
    n = len(orden)
    out = {}
    for p in PERCENTILES:
        pos = (p / 100) * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out[f"p{p}"] = round(orden[lo] + (orden[hi] - orden[lo]) * frac, 2)
    return out


# Tags emitidos comparando el promedio de la ventana del usuario contra el
# percentil global de esa métrica. (tag_id, métrica, percentil de corte).
# `juega_sin_apoyo` y `rotaciones` NO están acá: necesitan datos que aún no
# existen (correlación muerte<->utilidad previa del equipo; cambios de zona
# por ronda vía `place`) -- bloqueados igual que economía en el doc
# original, no se fabrican con proxies débiles.
TAGS_GLOBALES: list[tuple[str, str, str]] = [
    ("jugador_agresivo", "entry_attempts", "p75"),
    ("maquina_de_dano", "adr", "p75"),
    ("alta_participacion", "kill_participation", "p75"),
]

TAG_LABELS: dict[str, str] = {
    "jugador_agresivo": "Jugador agresivo",
    "maquina_de_dano": "Máquina de daño",
    "alta_participacion": "Alta participación en bajas",
}


def evaluar_tags_globales(
    stats_usuario: dict[str, float],
    percentiles_globales: dict[str, dict[str, float]],
    n_players: int,
) -> list[dict]:
    """Tags que el usuario merece según su ventana vs. los percentiles
    globales. `stats_usuario`: métrica -> promedio de su ventana.
    `percentiles_globales`: métrica -> {p25..p90}. Con muestra global
    chica no se emite nada (guardrail, no un cálculo degradado)."""
    if n_players < MIN_JUGADORES_GLOBAL:
        return []
    out = []
    for tag_id, metrica, corte in TAGS_GLOBALES:
        valor = stats_usuario.get(metrica)
        umbral = percentiles_globales.get(metrica, {}).get(corte)
        if valor is None or umbral is None:
            continue
        if valor >= umbral:
            out.append(
                {
                    "tag_id": tag_id,
                    "detalle": {"valor": round(valor, 2), "umbral": umbral, "percentil": corte},
                }
            )
    return out
