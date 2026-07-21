"""
Modelos SQLAlchemy 2.0 (declarative). Reflejan el esquema del ROADMAP.
Portable a Postgres/Supabase: tipos genéricos, sin dialecto específico.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    map: Mapped[str | None] = mapped_column(String)
    demo_file: Mapped[str] = mapped_column(String, nullable=False)
    tickrate: Mapped[int | None] = mapped_column(Integer)
    n_rounds: Mapped[int | None] = mapped_column(Integer)
    ingested_at: Mapped[str] = mapped_column(String, nullable=False)
    # Cuándo se JUGÓ la partida (matchtime del GC, ISO). NULL = desconocido
    # (demo manual sin backfill). El ORDEN cronológico no depende de esto:
    # match_id es monótono creciente y zero-padded -> ordenar por match_id.
    played_at: Mapped[str | None] = mapped_column(String)
    # Auditoría de quién disparó la ingesta; NO gatea acceso (ver users/visibilidad).
    ingested_by_steamid: Mapped[str | None] = mapped_column(ForeignKey("players.steamid"))

    players: Mapped[list[MatchPlayer]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    stats: Mapped[list[PlayerMatchStats]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"

    steamid: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)


class User(Base):
    """Cuenta con la que un steamid inició sesión (Steam OpenID). Distinta de
    Player (cualquier steamid visto en una demo, se haya registrado o no).
    El login debe upsertear Player además de User para no violar la FK."""

    __tablename__ = "users"

    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    last_login_at: Mapped[str | None] = mapped_column(String)

    # Auto-fetch estilo Leetify. El auth code SOLO da acceso al historial de
    # partidas del propio usuario (Web API), nunca a su cuenta; se guarda en
    # claro a propósito (cifrado = mejora futura). last_sharecode es la
    # posición en la cadena (knowncode) y se conserva al desvincular para
    # re-vincular sin huecos.
    steam_auth_code: Mapped[str | None] = mapped_column(String)
    last_sharecode: Mapped[str | None] = mapped_column(String)
    # None = no vinculado | 'active' | 'revoked' (403 de Steam) | 'error'
    autofetch_status: Mapped[str | None] = mapped_column(String)
    autofetch_error: Mapped[str | None] = mapped_column(String)
    last_polled_at: Mapped[str | None] = mapped_column(String)
    last_fetched_at: Mapped[str | None] = mapped_column(String)


class MatchPlayer(Base):
    __tablename__ = "match_players"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), primary_key=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    team_num: Mapped[int | None] = mapped_column(Integer)
    # Rating de matchmaking al ENTRAR a la partida, crudo del demo.
    # NULL = demo ingerido antes de esta feature (re-ingerir con --force para
    # backfillear); 0 = parseado pero sin rating (calibrando); >0 = CS Rating.
    rank: Mapped[int | None] = mapped_column(Integer)
    rank_type: Mapped[int | None] = mapped_column(Integer)  # 11 = Premier
    comp_wins: Mapped[int | None] = mapped_column(Integer)

    match: Mapped[Match] = relationship(back_populates="players")


class Round(Base):
    __tablename__ = "rounds"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), primary_key=True)
    round_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    end_tick: Mapped[int | None] = mapped_column(Integer)
    winner_num: Mapped[int | None] = mapped_column(Integer)
    win_reason: Mapped[int | None] = mapped_column(Integer)


class Kill(Base):
    __tablename__ = "kills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    round_num: Mapped[int | None] = mapped_column(Integer)
    tick: Mapped[int | None] = mapped_column(Integer)
    attacker: Mapped[str | None] = mapped_column(String)
    victim: Mapped[str] = mapped_column(String, nullable=False)
    assister: Mapped[str | None] = mapped_column(String)
    weapon: Mapped[str | None] = mapped_column(String)
    headshot: Mapped[bool | None] = mapped_column(Boolean)
    penetrated: Mapped[bool | None] = mapped_column(Boolean)
    noscope: Mapped[bool | None] = mapped_column(Boolean)
    thru_smoke: Mapped[bool | None] = mapped_column(Boolean)
    attacker_blind: Mapped[bool | None] = mapped_column(Boolean)
    distance: Mapped[float | None] = mapped_column(Float)
    attacker_x: Mapped[float | None] = mapped_column(Float)
    attacker_y: Mapped[float | None] = mapped_column(Float)
    attacker_z: Mapped[float | None] = mapped_column(Float)
    victim_x: Mapped[float | None] = mapped_column(Float)
    victim_y: Mapped[float | None] = mapped_column(Float)
    victim_z: Mapped[float | None] = mapped_column(Float)


class Damage(Base):
    __tablename__ = "damages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    round_num: Mapped[int | None] = mapped_column(Integer)
    tick: Mapped[int | None] = mapped_column(Integer)
    attacker: Mapped[str | None] = mapped_column(String)
    victim: Mapped[str] = mapped_column(String, nullable=False)
    weapon: Mapped[str | None] = mapped_column(String)
    dmg_health: Mapped[int | None] = mapped_column(Integer)
    dmg_armor: Mapped[int | None] = mapped_column(Integer)
    hitgroup: Mapped[str | None] = mapped_column(Text)


class Grenade(Base):
    """Detonaciones de granadas. Coords = lugar de efecto, no de origen del tiro."""

    __tablename__ = "grenades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    round_num: Mapped[int | None] = mapped_column(Integer)
    tick: Mapped[int | None] = mapped_column(Integer)
    thrower: Mapped[str | None] = mapped_column(String)
    # flashbang|hegrenade|molotov|smokegrenade|decoy
    weapon: Mapped[str | None] = mapped_column(String)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    z: Mapped[float | None] = mapped_column(Float)


class Blind(Base):
    """Flashes: quién cegó a quién y cuánto."""

    __tablename__ = "blinds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    round_num: Mapped[int | None] = mapped_column(Integer)
    tick: Mapped[int | None] = mapped_column(Integer)
    attacker: Mapped[str | None] = mapped_column(String)
    victim: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float)


class PlayerMapEvent(Base):
    """Detalle por jugador involucrado (fan-out), fuente de los heatmaps.
    Podable por TTL una vez agregado en PlayerMapZone."""

    __tablename__ = "player_map_events"
    __table_args__ = (Index("idx_pme_lookup", "steamid", "map", "event_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    round_num: Mapped[int | None] = mapped_column(Integer)
    tick: Mapped[int | None] = mapped_column(Integer)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"))
    # 'kill'|'death'|'flash_thrown'|'he_thrown'|'molotov_thrown'|'smoke_thrown'
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    is_entry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_traded: Mapped[bool | None] = mapped_column(Boolean)  # solo event_type='death'
    is_trade_kill: Mapped[bool | None] = mapped_column(Boolean)  # solo event_type='kill'
    avenged_steamid: Mapped[str | None] = mapped_column(String)  # a quién vengó (si is_trade_kill)
    # Segundos desde que la ronda se volvió "viva" (fin de freezetime) hasta
    # esta muerte. Solo event_type='death'; None si el demo no expuso
    # round_freeze_end (ver infra/parser.py). Insumo de Coach's Corner.
    seconds_into_round: Mapped[float | None] = mapped_column(Float)
    map: Mapped[str] = mapped_column(String, nullable=False)  # denormalizado de matches.map
    team_num: Mapped[int | None] = mapped_column(Integer)  # denormalizado de match_players
    round_won: Mapped[bool | None] = mapped_column(Boolean)  # denormalizado de rounds
    weapon: Mapped[str | None] = mapped_column(String)
    headshot: Mapped[bool | None] = mapped_column(Boolean)
    distance: Mapped[float | None] = mapped_column(Float)
    enemies_blinded: Mapped[int | None] = mapped_column(Integer)  # solo flash_thrown
    blind_duration_total: Mapped[float | None] = mapped_column(Float)  # solo flash_thrown
    teammates_blinded: Mapped[int | None] = mapped_column(Integer)  # solo flash_thrown
    damage_dealt: Mapped[int | None] = mapped_column(Integer)  # solo he_thrown/molotov_thrown
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    u: Mapped[float | None] = mapped_column(Float)  # radar-normalizada (maps.to_radar_norm)
    v: Mapped[float | None] = mapped_column(Float)
    grid_x: Mapped[int | None] = mapped_column(Integer)  # derivada de (u,v), no de bounds propios
    grid_y: Mapped[int | None] = mapped_column(Integer)


class PlayerMapZone(Base):
    """Agregado por celda de grid. Read-path principal para renderizar heatmaps
    (payload acotado sin importar cuántas partidas tenga el jugador)."""

    __tablename__ = "player_map_zones"

    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    map: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, primary_key=True)
    grid_x: Mapped[int] = mapped_column(Integer, primary_key=True)
    grid_y: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    traded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top_weapon: Mapped[str | None] = mapped_column(String)
    avg_enemies_blinded: Mapped[float | None] = mapped_column(Float)
    total_blind_duration: Mapped[float | None] = mapped_column(Float)
    avg_damage: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[str | None] = mapped_column(String)


class PlayerClutch(Base):
    """Una fila por CADA situación 1vX detectada -- ganada o perdida (ver
    domain/rounds.py::find_clutch_situations). Cache table reconstruible
    desde kills+rounds, igual que player_match_stats; se persiste porque el
    Clutch Timeline y la milestone "clutch más grande" la leen seguido."""

    __tablename__ = "player_clutches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), index=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), index=True)
    round_num: Mapped[int] = mapped_column(Integer, nullable=False)
    enemies_at_start: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)  # 'won'|'lost'


class PlayerMatchStats(Base):
    __tablename__ = "player_match_stats"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), primary_key=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    damage: Mapped[int] = mapped_column(Integer, default=0)
    adr: Mapped[float] = mapped_column(Float, default=0.0)
    kd: Mapped[float] = mapped_column(Float, default=0.0)
    hs_pct: Mapped[float] = mapped_column(Float, default=0.0)
    kast: Mapped[float] = mapped_column(Float, default=0.0)
    entry_kills: Mapped[int] = mapped_column(Integer, default=0)
    entry_deaths: Mapped[int] = mapped_column(Integer, default=0)
    k2: Mapped[int] = mapped_column(Integer, default=0)
    k3: Mapped[int] = mapped_column(Integer, default=0)
    k4: Mapped[int] = mapped_column(Integer, default=0)
    k5: Mapped[int] = mapped_column(Integer, default=0)
    clutches: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    match: Mapped[Match] = relationship(back_populates="stats")
