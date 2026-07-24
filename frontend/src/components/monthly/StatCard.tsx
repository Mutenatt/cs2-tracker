export function StatCard({
  value,
  label,
  highlight = false,
}: {
  value: string;
  label: string;
  highlight?: boolean;
}) {
  return (
    <div className="monthly-stat-card">
      <span className={`monthly-stat-value${highlight ? " monthly-stat-value-highlight" : ""}`}>
        {value}
      </span>
      <span className="cs-section-label">{label}</span>
    </div>
  );
}
