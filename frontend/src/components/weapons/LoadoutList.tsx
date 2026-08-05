import { motion } from "motion/react";
import { staggerList } from "../motion/presets";
import { LoadoutCard, LOADOUT_ORDER } from "./LoadoutCard";
import type { LoadoutTierStats } from "../../types";

export function LoadoutList({ loadouts }: { loadouts: LoadoutTierStats[] }) {
  return (
    <motion.div className="loadout-list" variants={staggerList} initial="hidden" animate="show">
      {LOADOUT_ORDER.map((tier) => (
        <LoadoutCard key={tier} tier={tier} stats={loadouts.find((l) => l.tier === tier)} />
      ))}
    </motion.div>
  );
}
