import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { getCs2News, getLatamStreams, getTeamRanking } from "../api";
import { HeroStreamCarousel } from "../components/HeroStreamCarousel";
import { SectionLabel } from "../components/SectionLabel";
import { cardRise, staggerList } from "../components/motion/presets";
import { MonthlySummaryHero } from "../components/monthly/MonthlySummaryHero";
import type { NewsItemDto, StreamsResponse, TeamRankingResponse } from "../types";

const CS2_KEY_ART =
  "https://cdn.cloudflare.steamstatic.com/apps/csgo/images/csgo_react/social/cs2.jpg";

// Pool activo de Premier vigente desde la Season 5 (julio 2026, Cache
// reemplazó a Overpass). Mantenido a mano -- no hay una fuente en vivo para
// esto, se actualiza si Valve vuelve a rotar el pool.
interface MapPoolEntry {
  key: string;
  name: string;
}

const ACTIVE_MAP_POOL: MapPoolEntry[] = [
  { key: "de_ancient", name: "Ancient" },
  { key: "de_anubis", name: "Anubis" },
  { key: "de_cache", name: "Cache" },
  { key: "de_dust2", name: "Dust II" },
  { key: "de_inferno", name: "Inferno" },
  { key: "de_mirage", name: "Mirage" },
  { key: "de_nuke", name: "Nuke" },
];

function mapIconUrl(key: string): string {
  return `https://raw.githubusercontent.com/MurkyYT/cs2-map-icons/main/images/${key}.png`;
}

function TeamLogo({ name, src }: { name: string; src: string | null }) {
  const [broken, setBroken] = useState(false);
  if (broken || src === null) {
    return <span className="team-logo-fallback">{name.slice(0, 2).toUpperCase()}</span>;
  }
  return <img className="team-logo" src={src} alt={name} onError={() => setBroken(true)} />;
}

// Badge de cambio de posición en el ranking: null = equipo nuevo ("NEW").
function RankChange({ change }: { change: number | null }) {
  if (change === null) return <span className="ranking-change new">NEW</span>;
  if (change > 0) return <span className="ranking-change up">▲ {change}</span>;
  if (change < 0) return <span className="ranking-change down">▼ {Math.abs(change)}</span>;
  return <span className="ranking-change flat">–</span>;
}

const viewersFmt = new Intl.NumberFormat("es-AR");

function shortDate(iso: string): string {
  return new Intl.DateTimeFormat("es-AR", { day: "numeric", month: "short" })
    .format(new Date(iso))
    .toUpperCase()
    .replace(".", "");
}

export function HomeView() {
  const [news, setNews] = useState<NewsItemDto[] | null>(null);
  const [newsError, setNewsError] = useState(false);
  const [ranking, setRanking] = useState<TeamRankingResponse | null>(null);
  const [rankingError, setRankingError] = useState(false);
  const [streams, setStreams] = useState<StreamsResponse | null>(null);
  const [streamsError, setStreamsError] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setNews((await getCs2News()).items);
      } catch {
        setNewsError(true);
      }
    })();
    (async () => {
      try {
        setRanking(await getTeamRanking());
      } catch {
        setRankingError(true);
      }
    })();
    (async () => {
      try {
        setStreams(await getLatamStreams());
      } catch {
        setStreamsError(true);
      }
    })();
  }, []);

  const bentoMain = news?.[0];
  const bentoSecondary = news?.slice(1, 3) ?? [];

  return (
    <>
      <MonthlySummaryHero />

      <div className="section-head">
        <SectionLabel>Mapas activos · Premier</SectionLabel>
        <span className="rule" />
      </div>
      <div className="section-note" style={{ marginTop: -4 }}>
        Pool vigente desde la Season 5 (julio 2026) — se actualiza a mano si Valve vuelve a rotarlo.
      </div>
      <motion.div className="map-pool-grid" variants={staggerList} initial="hidden" animate="show">
        {ACTIVE_MAP_POOL.map((m) => (
          <motion.div className="map-pool-card" key={m.key} variants={cardRise}>
            <img
              className="map-pool-icon"
              src={mapIconUrl(m.key)}
              alt={m.name}
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.visibility = "hidden";
              }}
            />
            <span className="map-pool-name">{m.name}</span>
          </motion.div>
        ))}
      </motion.div>

      <section>
        <div className="section-head">
          <SectionLabel>Streams · CS en LATAM</SectionLabel>
          <span className="rule" />
        </div>
        {streams?.configured === false && (
          <div className="section-note" style={{ marginTop: -4 }}>
            Streams no configurados — faltan credenciales de Twitch/Kick en el backend.
          </div>
        )}
        {streamsError && (
          <div className="section-note" style={{ marginTop: -4 }}>
            No se pudieron cargar los streams ahora mismo.
          </div>
        )}
        {streams === null && !streamsError && (
          <div className="section-note" style={{ marginTop: -4 }}>
            Cargando streams…
          </div>
        )}
        {streams?.configured && streams.streams.length === 0 && (
          <div className="section-note" style={{ marginTop: -4 }}>
            No hay streams de CS en español/portugués en vivo ahora.
          </div>
        )}
        {streams && streams.streams.length > 0 && <HeroStreamCarousel streams={streams.streams} />}
      </section>

      <section>
        <div className="section-head">
          <SectionLabel>Ranking mundial · Top 10</SectionLabel>
          <span className="rule" />
        </div>
        {ranking?.source === "valve" && (
          <div className="section-note" style={{ marginTop: -4 }}>
            HLTV no respondió — mostrando el ranking oficial de Valve.
          </div>
        )}
        {(rankingError || ranking?.source === "unavailable") && (
          <div className="section-note" style={{ marginTop: -4 }}>
            El ranking no está disponible ahora mismo — se reintenta en unos minutos.
          </div>
        )}
        {ranking === null && !rankingError && (
          <div className="section-note" style={{ marginTop: -4 }}>
            Cargando ranking…
          </div>
        )}
        {ranking && ranking.teams.length > 0 && (
          <motion.ol
            className="ranking-list"
            variants={staggerList}
            initial="hidden"
            animate="show"
          >
            {ranking.teams.map((t) => (
              <motion.li className="ranking-row" key={t.position} variants={cardRise}>
                <span className="ranking-pos">#{t.position}</span>
                <TeamLogo name={t.name} src={t.logo_url} />
                <span className="ranking-name">{t.name}</span>
                <span className="ranking-points">{viewersFmt.format(t.points)} pts</span>
                <RankChange change={t.change} />
              </motion.li>
            ))}
          </motion.ol>
        )}
      </section>

      <div className="section-head">
        <SectionLabel>Últimas novedades</SectionLabel>
        <span className="rule" />
      </div>
      {newsError && (
        <div className="section-note" style={{ marginTop: -4 }}>
          No se pudieron cargar las novedades de Steam ahora mismo.
        </div>
      )}
      {(bentoMain || bentoSecondary.length > 0) && (
        <motion.div className="news-bento" variants={staggerList} initial="hidden" animate="show">
          {bentoMain && (
            <motion.a
              className="news-bento-main"
              variants={cardRise}
              style={{ backgroundImage: `url(${CS2_KEY_ART})` }}
              href={bentoMain.url}
              target="_blank"
              rel="noreferrer"
            >
              <div className="news-bento-main-overlay" />
              <div className="news-bento-main-content">
                <span className="news-tag">{shortDate(bentoMain.date)}</span>
                <span className="news-bento-main-title">{bentoMain.title}</span>
                <span className="news-summary">{bentoMain.summary}</span>
              </div>
            </motion.a>
          )}
          {bentoSecondary.map((n) => (
            <motion.a
              className="news-bento-card"
              key={n.url}
              variants={cardRise}
              href={n.url}
              target="_blank"
              rel="noreferrer"
            >
              <span className="news-tag">{shortDate(n.date)}</span>
              <div className="news-bento-card-body">
                <span className="news-title">{n.title}</span>
                <span className="news-summary">{n.summary}</span>
              </div>
            </motion.a>
          ))}
        </motion.div>
      )}
    </>
  );
}
