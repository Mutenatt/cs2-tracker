"""
Clasificación de economía por ronda y badges derivados (Force buy ganador,
Eco frag, Millonario, Ahorra bien). PURA -- recibe agregados ya resueltos
(ver api/queries.py), no toca la DB.

Fuente de datos real (verificada contra demoparser2 0.41.4 con una demo
real, no asumida): el doc de diseño original suponía un evento
"item_purchase" que NO existe en esta versión de la librería. Lo que sí
expone son props de tick (`CCSPlayerPawn.m_unFreezetimeEndEquipmentValue`,
mismo mecanismo que ya usan team_num/rank en infra/parser.py) -- el
equipment value YA con lo comprado esa ronda, muestreado al cierre de la
ventana de compra. No hace falta un evento de compra discreto para
clasificar full_buy/force_buy/semi_eco/eco.
"""

from __future__ import annotations

from cs2tracker.domain.profile import WEAPON_CATEGORY

FULL_BUY_MIN = 4000
FORCE_BUY_MIN = 2000
SEMI_ECO_MIN = 1000

MILLONARIO_MIN_PRICE = 4750  # AWP, el arma más cara del buy menu estándar

# Precios de buy-menu de CS2 (constantes del juego, no algo que exponga el
# parser). Solo se listan las armas -- granadas/armadura no participan de
# "Millonario". Alcanza con las relevantes para el umbral de arriba, pero
# se completa el resto por si se necesita para otro badge más adelante.
WEAPON_PRICE: dict[str, int] = {
    "awp": 4750,
    "g3sg1": 5000,
    "scar20": 5000,
    "m4a1": 3100,
    "ak47": 2700,
    "m4a1_silencer": 2900,
    "aug": 3300,
    "sg556": 3000,
    "famas": 2050,
    "galilar": 1800,
    "ssg08": 1700,
    "p90": 2350,
    "mp7": 1500,
    "mp5sd": 1500,
    "ump45": 1200,
    "bizon": 1400,
    "mac10": 1050,
    "mp9": 1250,
    "xm1014": 2000,
    "mag7": 1300,
    "nova": 1050,
    "sawedoff": 1100,
    "negev": 1700,
    "deagle": 700,
    "revolver": 600,
    "tec9": 500,
    "fiveseven": 500,
    "p250": 300,
    "elite": 300,
    "hkp2000": 200,
    "usp_silencer": 200,
    "glock": 200,
}


def clasificar_tipo_compra(equip_value: int) -> str:
    """'full_buy' | 'force_buy' | 'semi_eco' | 'eco', por umbrales de
    equipment value (ya con lo comprado esa ronda)."""
    if equip_value >= FULL_BUY_MIN:
        return "full_buy"
    if equip_value >= FORCE_BUY_MIN:
        return "force_buy"
    if equip_value >= SEMI_ECO_MIN:
        return "semi_eco"
    return "eco"


def tasa_buena_economia(clasificaciones: list[str]) -> float:
    """% de rondas donde NO estuvo en eco total (full_buy/force_buy/semi_eco
    cuentan como "gestión razonable"). Proxy simple para "Ahorra bien":
    rara vez llega a estar completamente en la lona."""
    if not clasificaciones:
        return 0.0
    ok = sum(1 for c in clasificaciones if c != "eco")
    return round(100.0 * ok / len(clasificaciones), 1)


def detectar_eco_frag(kills_ronda: list[dict], tipo_compra: dict[str, str]) -> list[str]:
    """steamids que mataron a alguien en full_buy estando ellos mismos en
    eco, en esta ronda. `kills_ronda`: [{"attacker","victim"}]. Excluye
    suicidio (attacker == victim, ya filtrado por el caller si hace
    falta)."""
    return [
        k["attacker"]
        for k in kills_ronda
        if k.get("attacker")
        and k.get("victim")
        and tipo_compra.get(k["attacker"]) == "eco"
        and tipo_compra.get(k["victim"]) == "full_buy"
    ]


def filtrar_compras_reales(
    purchases: list[dict],
    round_freeze_ticks: dict[int, int],
    round_economy: list[dict],
) -> dict[tuple[int, str], list[str]]:
    """(round_num, steamid) -> armas que pasan DOS filtros de "compra real"
    (demoparser2 no distingue compra de recogida en item_pickup, esto lo
    desambigua por heurística):
    1. Ventana de compra: el pickup ocurrió antes del fin de freezetime
       (tick <= round_freeze_ticks[round]) -- descarta drops levantados a
       mitad de ronda (compañero muerto, arma del rival).
    2. Gasto suficiente: cash_spent de esa ronda >= precio del arma -- si
       no gastó al menos lo que cuesta, no la compró (descarta también el
       auto-equip de pistola inicial en jugadores que no compraron nada).
    Rondas sin round_freeze_end en el demo quedan sin compras (no se
    inventa una ventana)."""
    cash = {(e["round_num"], e["steamid"]): e["cash_spent"] for e in round_economy}
    out: dict[tuple[int, str], list[str]] = {}
    for c in purchases:
        item = c.get("item")
        if not item or item not in WEAPON_CATEGORY:
            continue
        freeze = round_freeze_ticks.get(c["round_num"])
        if freeze is None or c["tick"] > freeze:
            continue
        if cash.get((c["round_num"], c["steamid"]), 0) < WEAPON_PRICE.get(item, 0):
            continue
        out.setdefault((c["round_num"], c["steamid"]), []).append(item)
    return out


def detectar_millonario(compras_ronda: list[dict], tipo_compra: dict[str, str]) -> list[dict]:
    """Jugadores que compraron un arma de precio >= MILLONARIO_MIN_PRICE
    estando en eco/semi_eco esa ronda (el clásico "eco AWP"). Devuelve
    [{"steamid","arma"}]. `compras_ronda`: [{"steamid","item"}] -- item ya
    pasado por los dos filtros de filtrar_compras_reales (ventana de
    compra + gasto suficiente), así que "compró" es una afirmación con
    respaldo heurístico, no una adivinanza sobre pickups crudos."""
    out = []
    for c in compras_ronda:
        sid, item = c.get("steamid"), c.get("item")
        if not sid or not item:
            continue
        if WEAPON_PRICE.get(item, 0) < MILLONARIO_MIN_PRICE:
            continue
        if tipo_compra.get(sid) in ("eco", "semi_eco"):
            out.append({"steamid": sid, "arma": item})
    return out


def es_arma_real(item: str) -> bool:
    """True si `item` (de item_pickup) es un arma de fuego real, no
    utilidad/armadura/defuser -- mismo set que domain/profile.py::
    WEAPON_CATEGORY, la lista canónica de armas ya usada por
    TopWeaponsPanel."""
    return item in WEAPON_CATEGORY
