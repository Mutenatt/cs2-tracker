"""
Wrapper de demoparser2. Extrae eventos crudos del .dem y los devuelve como
estructuras planas (dicts). NO toca la DB ni calcula stats: eso es de las
capas domain/ingest. Aísla la dependencia del parser en un solo lugar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


def _iter_rows(df):
    """demoparser2 devuelve una lista vacía (no un DataFrame vacío) cuando un
    tipo de evento no ocurrió ni una vez en la demo (p.ej. nadie tiró una
    decoy). Normaliza para poder iterar sin romper con AttributeError."""
    if not hasattr(df, "iterrows"):
        return []
    return df.iterrows()


def _val(row, name):
    try:
        v = row[name]
    except (KeyError, IndexError):
        return None
    if v is None or (isinstance(v, float) and v != v):  # NaN
        return None
    return v


def match_id_from_name(demo_file: str) -> str:
    """match730_<reservation>_<tv>_<n>.dem -> <reservation> (id estable)."""
    m = re.search(r"match\d+_(\d+)_", demo_file)
    return m.group(1) if m else Path(demo_file).stem


@dataclass
class ParsedDemo:
    match_id: str
    demo_file: str
    map: str | None
    n_rounds: int
    players: dict[str, str] = field(default_factory=dict)  # steamid -> name
    kills: list[dict] = field(default_factory=list)
    damages: list[dict] = field(default_factory=list)
    teams: dict[str, int] = field(default_factory=dict)  # steamid -> roster (2/3)
    rounds: list[dict] = field(default_factory=list)  # {round_num,tick,winner_roster}
    score: dict[int, int] = field(default_factory=dict)  # roster -> rondas ganadas
    grenades: list[dict] = field(default_factory=list)
    blinds: list[dict] = field(default_factory=list)
    # round_num (mismo espacio que kills/damages: total_rounds_played, 0-indexado)
    # -> tick en el que la ronda se volvió "viva" (terminó el freezetime).
    round_freeze_ticks: dict[int, int] = field(default_factory=dict)
    # Rank de matchmaking crudo del demo, por steamid. GOTV graba el rating al
    # ENTRAR a la partida (verificado: constante intra-demo). 0 = sin rating
    # (calibrando). rank_type 11 = Premier (CS Rating); otros valores son
    # rank por mapa de Competitive. comp_wins = victorias de matchmaking.
    ranks: dict[str, int] = field(default_factory=dict)
    rank_types: dict[str, int] = field(default_factory=dict)
    comp_wins: dict[str, int] = field(default_factory=dict)


_SIDE = {"CT": 3, "T": 2}  # winner string -> team_num

# evento de detonación -> weapon. Nombres verificados contra demoparser2 0.41.4
# con una demo real (ver docs/notas de la Fase 3 del plan). 'inferno' es el
# nombre real tanto del evento como del weapon en player_hurt para molotov/
# incendiary -- no existe un evento "molotov_detonate" separado.
_GRENADE_EVENTS = {
    "flashbang_detonate": "flashbang",
    "hegrenade_detonate": "hegrenade",
    "inferno_startburn": "inferno",
    "smokegrenade_detonate": "smokegrenade",
    "decoy_detonate": "decoy",
}


def parse_demo(dem_path: Path) -> ParsedDemo:
    from demoparser2 import DemoParser

    parser = DemoParser(str(dem_path))
    deaths = parser.parse_event(
        "player_death", player=["X", "Y", "Z"], other=["total_rounds_played"]
    )
    hurt = parser.parse_event("player_hurt", other=["total_rounds_played"])

    n_rounds = (
        int(deaths["total_rounds_played"].max()) + 1
        if "total_rounds_played" in deaths.columns and len(deaths)
        else 1
    )

    map_name = None
    try:
        map_name = parser.parse_header().get("map_name")
    except Exception:
        pass

    parsed = ParsedDemo(
        match_id=match_id_from_name(dem_path.name),
        demo_file=dem_path.name,
        map=map_name,
        n_rounds=n_rounds,
    )

    def note(sid, name):
        if sid:
            sid = str(sid)
            if name and sid not in parsed.players:
                parsed.players[sid] = name

    for _, r in deaths.iterrows():
        atk, vic, ast = (
            _val(r, "attacker_steamid"),
            _val(r, "user_steamid"),
            _val(r, "assister_steamid"),
        )
        note(atk, _val(r, "attacker_name"))
        note(vic, _val(r, "user_name"))
        note(ast, _val(r, "assister_name"))
        rnd = _val(r, "total_rounds_played")
        parsed.kills.append(
            {
                "round_num": int(rnd) if rnd is not None else None,
                "tick": int(_val(r, "tick") or 0),
                "attacker": str(atk) if atk else None,
                "victim": str(vic) if vic else None,
                "assister": str(ast) if ast else None,
                "weapon": _val(r, "weapon"),
                "headshot": bool(_val(r, "headshot")),
                "penetrated": bool(_val(r, "penetrated")),
                "noscope": bool(_val(r, "noscope")),
                "thru_smoke": bool(_val(r, "thrusmoke")),
                "attacker_blind": bool(_val(r, "attackerblind")),
                "distance": _val(r, "distance"),
                "attacker_x": _val(r, "attacker_X"),
                "attacker_y": _val(r, "attacker_Y"),
                "attacker_z": _val(r, "attacker_Z"),
                "victim_x": _val(r, "user_X"),
                "victim_y": _val(r, "user_Y"),
                "victim_z": _val(r, "user_Z"),
            }
        )

    for _, r in hurt.iterrows():
        atk, vic = _val(r, "attacker_steamid"), _val(r, "user_steamid")
        rnd = _val(r, "total_rounds_played")
        parsed.damages.append(
            {
                "round_num": int(rnd) if rnd is not None else None,
                "tick": int(_val(r, "tick") or 0),
                "attacker": str(atk) if atk else None,
                "victim": str(vic) if vic else None,
                "weapon": _val(r, "weapon"),
                "dmg_health": int(_val(r, "dmg_health") or 0),
                "dmg_armor": int(_val(r, "dmg_armor") or 0),
                "hitgroup": _val(r, "hitgroup"),
            }
        )

    _resolve_teams_and_score(parser, parsed)
    _extract_grenades(parser, parsed)
    _extract_blinds(parser, parsed)
    _extract_round_freeze_ticks(parser, parsed)
    return parsed


def _extract_round_freeze_ticks(parser, parsed: ParsedDemo) -> None:
    """Tick de fin de freezetime (ronda "viva") por round_num, en el mismo
    espacio de índices que kills/damages (total_rounds_played, 0-indexado).
    Usado para "muertes tempranas de ronda" (Coach's Corner) -- si el evento
    no está disponible en esta demo, queda vacío y esa feature simplemente
    no tiene datos para esa partida (no se fabrica un fallback aproximado)."""
    try:
        df = parser.parse_event("round_freeze_end", other=["total_rounds_played"])
    except Exception:
        return
    for _, r in _iter_rows(df):
        rnd = _val(r, "total_rounds_played")
        tick = _val(r, "tick")
        if rnd is not None and tick is not None:
            parsed.round_freeze_ticks[int(rnd)] = int(tick)


def _extract_grenades(parser, parsed: ParsedDemo) -> None:
    """Detonaciones de granadas (lugar de EFECTO, no de origen del tiro).
    entity_id se usa solo para ligar blinds a su flash (domain.utility);
    no se persiste en la tabla `grenades`."""
    for event_name, weapon in _GRENADE_EVENTS.items():
        try:
            df = parser.parse_event(event_name, other=["total_rounds_played"])
        except Exception:
            continue
        for _, r in _iter_rows(df):
            sid, name = _val(r, "user_steamid"), _val(r, "user_name")
            if sid:
                sid = str(sid)
            rnd = _val(r, "total_rounds_played")
            if sid and name and sid not in parsed.players:
                parsed.players[sid] = name
            parsed.grenades.append(
                {
                    "round_num": int(rnd) if rnd is not None else None,
                    "tick": int(_val(r, "tick") or 0),
                    "thrower": sid,
                    "weapon": weapon,
                    "x": _val(r, "x"),
                    "y": _val(r, "y"),
                    "z": _val(r, "z"),
                    "entity_id": _val(r, "entityid"),
                }
            )


def _extract_blinds(parser, parsed: ParsedDemo) -> None:
    """Quién cegó a quién y cuánto. entity_id liga cada blind a la flash que
    lo causó (mismo id que flashbang_detonate, ver domain/utility.py)."""
    try:
        df = parser.parse_event("player_blind", other=["total_rounds_played"])
    except Exception:
        return
    for _, r in _iter_rows(df):
        atk, vic = _val(r, "attacker_steamid"), _val(r, "user_steamid")
        atk_name, vic_name = _val(r, "attacker_name"), _val(r, "user_name")
        if atk:
            atk = str(atk)
        if vic:
            vic = str(vic)
        for sid, name in ((atk, atk_name), (vic, vic_name)):
            if sid and name and sid not in parsed.players:
                parsed.players[sid] = name
        rnd = _val(r, "total_rounds_played")
        parsed.blinds.append(
            {
                "round_num": int(rnd) if rnd is not None else None,
                "tick": int(_val(r, "tick") or 0),
                "attacker": atk,
                "victim": vic,
                "duration": _val(r, "blind_duration"),
                "entity_id": _val(r, "entityid"),
            }
        )


# Friendly names de demoparser2: "rank" = m_iCompetitiveRanking, "comp_wins" =
# m_iCompetitiveWins. El rank type NO tiene friendly name (se ignora en
# silencio): hay que pedirlo por su path crudo.
_RANK_TYPE_PROP = "CCSPlayerController.m_iCompetitiveRankType"


def _resolve_teams_and_score(parser, parsed: ParsedDemo) -> None:
    """Extrae round_end + team_num por tick y delega el calculo a domain.
    Aprovecha el mismo parse_ticks para capturar rank/comp_wins por jugador:
    como las filas llegan en orden de tick ascendente, queda el valor del
    último round_end (el tick 1 puede traer rank_type sin inicializar)."""
    from cs2tracker.domain import resolve_teams

    try:
        re_df = parser.parse_event("round_end")
    except Exception:
        return
    if re_df is None or len(re_df) == 0:
        return

    round_events, ticks = [], []
    for i, row in re_df.iterrows():
        side = _SIDE.get(str(_val(row, "winner")))
        tick = _val(row, "tick")
        if side is None or tick is None:
            continue
        tick = int(tick)
        ticks.append(tick)
        round_events.append(
            {
                "round_num": int(_val(row, "round") or i),
                "tick": tick,
                "winner_side": side,
            }
        )
    if not round_events:
        return

    teams_at_tick: dict[int, dict[str, int]] = {}
    tk = parser.parse_ticks(["team_num", "rank", "comp_wins", _RANK_TYPE_PROP], ticks=ticks)
    for _, tr in tk.iterrows():
        sid, team, tick = (_val(tr, "steamid"), _val(tr, "team_num"), _val(tr, "tick"))
        if sid is None or team is None or tick is None:
            continue
        teams_at_tick.setdefault(int(tick), {})[str(sid)] = int(team)
        rank, wins, rtype = (
            _val(tr, "rank"),
            _val(tr, "comp_wins"),
            _val(tr, _RANK_TYPE_PROP),
        )
        if rank is not None:
            parsed.ranks[str(sid)] = int(rank)
        if wins is not None:
            parsed.comp_wins[str(sid)] = int(wins)
        if rtype is not None:
            parsed.rank_types[str(sid)] = int(rtype)

    res = resolve_teams(round_events, teams_at_tick)
    parsed.teams = res.player_roster
    parsed.rounds = res.rounds
    parsed.score = res.score
