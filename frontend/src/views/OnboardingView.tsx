import { useEffect, useState } from "react";
import { completeOnboarding, getOnboardingStatus, postDemographics, steamLinkUrl } from "../api";
import { AutofetchLinkForm } from "../components/AutofetchLinkForm";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";
import type {
  AcquisitionChannel,
  AgeBucket,
  DemographicsIn,
  OnboardingStatus,
  PrimaryGoal,
} from "../types";

const AGE_BUCKETS: AgeBucket[] = ["13-17", "18-24", "25-34", "35-44", "45+"];
const ACQUISITION_CHANNELS: { value: AcquisitionChannel; label: string }[] = [
  { value: "youtube", label: "YouTube" },
  { value: "twitch", label: "Twitch" },
  { value: "reddit", label: "Reddit" },
  { value: "amigo", label: "Un amigo" },
  { value: "buscador", label: "Buscador (Google, etc.)" },
  { value: "otro", label: "Otro" },
];
const PRIMARY_GOALS: { value: PrimaryGoal; label: string }[] = [
  { value: "competitivo", label: "Mejorar en competitivo" },
  { value: "casual", label: "Repasar partidas casuales" },
  { value: "coaching", label: "Coaching" },
  { value: "equipo", label: "Organización / equipo esports" },
  { value: "otro", label: "Otro" },
];

// Sondeo del paso del bot: no hay evento del sidecar hacia el frontend, solo
// polling contra /onboarding/status hasta que bot_friend_added_at se setee.
const BOT_POLL_MS = 4000;

type Step = "link-steam" | "bot" | "matchmaking" | "demographics" | "done";

interface Props {
  // "pending": cuenta recién verificada, todavía sin steamid -- arranca en
  // "link-steam" sin llamar a /onboarding/status (esa ruta exige cookie
  // real, que una cuenta pending no tiene). "user": ya tiene steamid.
  mode: "pending" | "user";
  onComplete: () => void;
}

// Wizard de registro post-login: vincular Steam (solo en mode="pending"),
// agregar al bot de Steam, conectar matchmaking (auth code) y encuesta
// demográfica (estudio de mercado) -- los 4 obligatorios; el backend
// (POST /onboarding/complete) los vuelve a exigir server-side antes de
// dejar pasar.
export function OnboardingView({ mode, onComplete }: Props) {
  const [step, setStep] = useState<Step>("link-steam");
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [demographics, setDemographics] = useState<Partial<DemographicsIn>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "user") {
      setStep("link-steam");
      return;
    }
    (async () => {
      try {
        const s = await getOnboardingStatus();
        setStatus(s);
        if (!s.bot_friend_added_at) setStep("bot");
        else if (!s.autofetch_linked) setStep("matchmaking");
        else if (!s.demographics_completed) setStep("demographics");
        else setStep("done");
      } catch {
        // sigue en el paso inicial con status en null
      }
    })();
  }, [mode]);

  useEffect(() => {
    if (step !== "bot") return;
    const id = setInterval(async () => {
      try {
        const s = await getOnboardingStatus();
        setStatus(s);
        if (s.bot_friend_added_at) setStep("matchmaking");
      } catch {
        // reintenta en el próximo tick
      }
    }, BOT_POLL_MS);
    return () => clearInterval(id);
  }, [step]);

  const demographicsValid = Boolean(
    demographics.age_bucket &&
    demographics.country?.trim() &&
    demographics.acquisition_channel &&
    demographics.primary_goal
  );

  const submitDemographics = async () => {
    if (!demographicsValid) return;
    setBusy(true);
    setError(null);
    try {
      const s = await postDemographics(demographics as DemographicsIn);
      setStatus(s);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar la encuesta.");
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    setBusy(true);
    setError(null);
    try {
      await completeOnboarding();
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar el registro.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="onb-shell">
      <div className="onb-topbar">
        <Logo size={20} />
      </div>
      <div className="onb-card">
        <ol className="onb-steps-nav">
          <li className={step === "link-steam" ? "active" : ""}>1. Vincular Steam</li>
          <li className={step === "bot" ? "active" : ""}>2. Agregar al bot</li>
          <li className={step === "matchmaking" ? "active" : ""}>3. Conectar matchmaking</li>
          <li className={step === "demographics" || step === "done" ? "active" : ""}>
            4. Contanos de vos
          </li>
        </ol>

        {step === "link-steam" && (
          <>
            <h2>Vinculá tu cuenta de Steam</h2>
            <p className="onb-sub">
              Es el último dato que nos falta para identificarte en tus partidas.
            </p>
            <div className="onb-actions">
              <Button as="a" href={steamLinkUrl()}>
                Vincular con Steam
              </Button>
            </div>
          </>
        )}

        {step === "bot" && (
          <>
            <h2>Agregá a nuestro bot de Steam</h2>
            <p className="onb-sub onb-bot-benefit">
              Te avisamos por chat de Steam apenas tu partida esté lista para ver, y mejora la
              precisión de tu rating Premier vigente. Es obligatorio para terminar el registro.
            </p>
            {status?.bot_steamid ? (
              <div className="onb-actions">
                <Button
                  as="a"
                  href={`https://steamcommunity.com/profiles/${status.bot_steamid}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Agregar de amigo en Steam
                </Button>
              </div>
            ) : (
              <p className="muted">
                El bot no está disponible en este momento, reintentá en un rato.
              </p>
            )}
            <p className="onb-sub muted">Esperando que aceptes la solicitud…</p>
          </>
        )}

        {step === "matchmaking" && (
          <>
            <h2>Conectá tu matchmaking</h2>
            <p className="onb-sub">Obligatorio: sin esto no tenemos partidas para mostrarte.</p>
            <AutofetchLinkForm
              onLinked={() => {
                setStatus((prev) => (prev ? { ...prev, autofetch_linked: true } : prev));
                setStep("demographics");
              }}
            />
          </>
        )}

        {step === "demographics" && (
          <>
            <h2>Contanos un poco de vos</h2>
            <p className="onb-sub">
              Nos ayuda a entender quién juega cStats. Es obligatorio y solo se usa para estudio de
              mercado interno.
            </p>
            <div className="onb-field">
              <label>Rango etario</label>
              <select
                className="onb-select"
                value={demographics.age_bucket ?? ""}
                onChange={(e) =>
                  setDemographics((d) => ({ ...d, age_bucket: e.target.value as AgeBucket }))
                }
              >
                <option value="" disabled>
                  Elegí una opción
                </option>
                {AGE_BUCKETS.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>
            <div className="onb-field">
              <label>País</label>
              <input
                className="onb-select"
                placeholder="Argentina"
                value={demographics.country ?? ""}
                onChange={(e) => setDemographics((d) => ({ ...d, country: e.target.value }))}
              />
            </div>
            <div className="onb-field">
              <label>¿Cómo nos conociste?</label>
              <select
                className="onb-select"
                value={demographics.acquisition_channel ?? ""}
                onChange={(e) =>
                  setDemographics((d) => ({
                    ...d,
                    acquisition_channel: e.target.value as AcquisitionChannel,
                  }))
                }
              >
                <option value="" disabled>
                  Elegí una opción
                </option>
                {ACQUISITION_CHANNELS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="onb-field">
              <label>¿Cuál es tu objetivo principal en cStats?</label>
              <select
                className="onb-select"
                value={demographics.primary_goal ?? ""}
                onChange={(e) =>
                  setDemographics((d) => ({ ...d, primary_goal: e.target.value as PrimaryGoal }))
                }
              >
                <option value="" disabled>
                  Elegí una opción
                </option>
                {PRIMARY_GOALS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="onb-actions">
              <Button onClick={submitDemographics} disabled={!demographicsValid || busy}>
                {busy ? "Guardando…" : "Continuar"}
              </Button>
            </div>
          </>
        )}

        {step === "done" && (
          <>
            <h2>¡Listo!</h2>
            <p className="onb-sub">Ya tenés todo conectado. Vamos a tus stats.</p>
            <div className="onb-actions">
              <Button onClick={finish} disabled={busy}>
                {busy ? "Terminando…" : "Entrar a cStats"}
              </Button>
            </div>
          </>
        )}

        {error && <p className="af-error">{error}</p>}
      </div>
    </div>
  );
}
