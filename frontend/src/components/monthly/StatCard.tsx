export function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="monthly-stat-card">
      <span className="monthly-stat-value">{value}</span>
      <span className="cs-section-label">{label}</span>
    </div>
  );
}
