"""
Modelos SQLAlchemy 2.0 (declarative). Reflejan el esquema del ROADMAP.
Portable a Postgres/Supabase: tipos genéricos, sin dialecto específico.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
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


class AccountSignup(Base):
    """Cuenta creada por email+contraseña, ANTES de vincular Steam. Fila
    efímera: se borra al completar el link a Steam (ver api/account.py::
    auth_callback), momento en el que sus 3 campos se copian a una fila
    NUEVA de User (PK steamid). Separada de User a propósito: no tocar la
    PK de users (steamid, con FK activa desde afuera) es lo que hace esta
    migración de bajo riesgo -- ver el comentario en User.email más abajo."""

    __tablename__ = "account_signups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    # None hasta que se hace click en el link de /auth/verify-email.
    email_verified_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class User(Base):
    """Cuenta con la que un steamid inició sesión. Distinta de Player
    (cualquier steamid visto en una demo, se haya registrado o no). El login
    debe upsertear Player además de User para no violar la FK."""

    __tablename__ = "users"

    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    steam_background_url: Mapped[str | None] = mapped_column(String)
    # Fondo elegido a mano por el usuario (URL de imagen propia). Tiene
    # prioridad sobre steam_background_url -- existe porque el scraping del
    # perfil de Steam puede fallar (rate-limit 429) o simplemente porque el
    # usuario prefiere elegir su propia imagen.
    custom_background_url: Mapped[str | None] = mapped_column(String)
    last_login_at: Mapped[str | None] = mapped_column(String)

    # Login por email+contraseña (obligatorio, alta previa a vincular
    # Steam -- ver AccountSignup). NOT NULL: una fila de User solo se crea
    # en el paso de vincular Steam, que exige email_verified_at no-nulo en
    # el pending -- el invariante "todo User tiene email verificado" queda
    # garantizado a nivel DB, no solo por convención.
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_verified_at: Mapped[str] = mapped_column(String, nullable=False)

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

    # CS Rating Premier VIGENTE, consultado en vivo al GC tras cada ingesta
    # (ver ingest.py + infra/gc_client.fetch_premier_profile). Cierra el gap
    # que el demo no puede: el rating resultante de la última partida. None
    # si nunca se pudo consultar (bot no amiga / offline).
    current_premier_rating: Mapped[int | None] = mapped_column(Integer)
    current_premier_updated_at: Mapped[str | None] = mapped_column(String)

    # Onboarding post-login (wizard tipo Leetify). None = todavía no lo
    # completó (usuarios pre-existentes a esta feature también quedan en
    # None y lo ven la próxima vez que entran). api/onboarding.py exige,
    # antes de setear esto, los 4 campos demográficos + autofetch activo +
    # bot_friend_added_at -- server-side, nunca confía en el cliente.
    onboarding_completed_at: Mapped[str | None] = mapped_column(String)
    # Seteado por gc-sidecar (vía api/internal.py) cuando confirma la
    # amistad con la cuenta bot -- necesaria para mandar la notificación de
    # "partida lista" por chat de Steam y mejora fetch_premier_profile.
    bot_friend_added_at: Mapped[str | None] = mapped_column(String)

    # Encuesta demográfica corta (estudio de mercado). Buckets, no datos
    # exactos (ni fecha de nacimiento ni ciudad) -- suficiente para segmentar
    # sin pedir de más.
    age_bucket: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    acquisition_channel: Mapped[str | None] = mapped_column(String)
    primary_goal: Mapped[str | None] = mapped_column(String)


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
    # Roster (2=T/3=CT, ver domain/teams.py) que atacaba esta ronda. NULL en
    # partidas ingeridas antes de este campo -- se completa re-ingiriendo con
    # --force, mismo criterio que MatchPlayer.rank. Insumo de domain/lurker.py.
    attacker_roster: Mapped[int | None] = mapped_column(Integer)


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
    # este evento. event_type='death' (insumo de Coach's Corner) y
    # event_type='kill' (insumo de domain/lurker.py: timing tardío); None si
    # el demo no expuso round_freeze_end (ver infra/parser.py).
    seconds_into_round: Mapped[float | None] = mapped_column(Float)
    map: Mapped[str] = mapped_column(String, nullable=False)  # denormalizado de matches.map
    # Zona nombrada del engine (BombsiteA, Mid, TSpawn...) donde ocurrió el
    # evento -- prop last_place_name del tick (ver infra/parser.py::
    # _annotate_places). Solo kill/death; NULL en partidas ingeridas antes
    # de este campo (re-ingerir con --force) o demos sin la prop.
    place: Mapped[str | None] = mapped_column(String)
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


class PlayerProfileTag(Base):
    """Cache de tags de perfil estilo Porofessor (rendimiento sobre una
    ventana de N partidas, no una sola partida -- ver domain/badges con
    UmbralTipo.RELATIVO_PARTIDA para el caso de una sola partida). Se
    borra y reinserta por usuario en cada recálculo (trigger: fin de
    ingest_demo), mismo patrón idempotente que ingest_demo con match_id.
    Siempre reconstruible desde player_match_stats/player_map_events -- es
    cache, no fuente de verdad."""

    __tablename__ = "player_profile_tags"
    __table_args__ = (Index("idx_ppt_steamid", "steamid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON)
    calculado_en: Mapped[str] = mapped_column(String, nullable=False)
    ventana_partidas: Mapped[int] = mapped_column(Integer, nullable=False)


class GlobalMetricStats(Base):
    """Percentiles globales por métrica, sobre TODOS los jugadores de la
    base (una fila-fuente por jugador: su promedio en player_match_stats).
    Cache chico (una fila por métrica), recomputado al final de cada
    ingesta -- insumo de los tags de perfil relativos-a-global (ver
    domain/percentiles.py). Delete+reinsert completo, patrón idempotente."""

    __tablename__ = "global_metric_stats"

    metric: Mapped[str] = mapped_column(String, primary_key=True)
    p25: Mapped[float] = mapped_column(Float, nullable=False)
    p50: Mapped[float] = mapped_column(Float, nullable=False)
    p75: Mapped[float] = mapped_column(Float, nullable=False)
    p90: Mapped[float] = mapped_column(Float, nullable=False)
    n_players: Mapped[int] = mapped_column(Integer, nullable=False)
    calculado_en: Mapped[str] = mapped_column(String, nullable=False)


class ClipJob(Base):
    """Job de render de clip 2D (ver infra/clips.py). El render corre como
    BackgroundTask de FastAPI tras el POST (segundos de CPU, no amerita
    cola externa); la fila persiste el estado para listar/descargar.
    file_path relativo a settings.clips_dir; el MP4 es regenerable
    mientras el .dem siga en disco."""

    __tablename__ = "clip_jobs"
    __table_args__ = (Index("idx_clip_jobs_steamid", "steamid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), nullable=False)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), nullable=False)
    round_num: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # pending|rendering|done|error
    error: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class RoundEconomy(Base):
    """Snapshot de economía por jugador por ronda: equipment value YA con
    lo comprado (muestreado al mismo tick de fin de freezetime que ya usa
    seconds_into_round -- ver infra/parser.py::_extract_economy), plata
    gastada/disponible, y las armas reales compradas esa ronda (jsonb,
    NO una tabla de items -- mismo criterio que ya aplicaron con
    positions: no crear una tabla hasta que un feature concreto la
    necesite). Cache reconstruible desde el demo -- requiere re-ingerir
    con --force partidas ingeridas antes de este campo."""

    __tablename__ = "round_economy"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"), primary_key=True)
    round_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    steamid: Mapped[str] = mapped_column(ForeignKey("players.steamid"), primary_key=True)
    equip_value: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    start_account: Mapped[int] = mapped_column(Integer, nullable=False)
    armas_compradas: Mapped[list | None] = mapped_column(JSON)
