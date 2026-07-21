import { useEffect, useState } from "react";
import { getMatchBadges } from "../api";
import type { Badge } from "../types";

export function BadgeStrip({ matchId, steamid }: { matchId: string; steamid: string }) {
  const [badges, setBadges] = useState<Badge[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await getMatchBadges(matchId, steamid);
        if (!cancelled) setBadges(r.badges);
      } catch {
        if (!cancelled) setBadges([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [matchId, steamid]);

  if (!badges || badges.length === 0) return null;

  return (
    <div className="badge-strip">
      {badges.map((b) => (
        <div className={`badge ${b.kind}`} key={b.key}>
          <span className="bi">{b.icon}</span>
          <div>
            <div className="bt">{b.title}</div>
            <div className="bd">{b.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
