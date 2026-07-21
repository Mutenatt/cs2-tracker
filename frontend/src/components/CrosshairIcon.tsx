export function CrosshairIcon({
  size = 96,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <circle cx="48" cy="48" r="30" stroke="var(--text-muted)" strokeWidth="2" />
      <line
        x1="48"
        y1="4"
        x2="48"
        y2="20"
        stroke="var(--accent-cyan)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="48"
        y1="76"
        x2="48"
        y2="92"
        stroke="var(--accent-cyan)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="4"
        y1="48"
        x2="20"
        y2="48"
        stroke="var(--accent-cyan)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="76"
        y1="48"
        x2="92"
        y2="48"
        stroke="var(--accent-cyan)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <rect x="38" y="38" width="6" height="20" rx="2" fill="var(--accent-cyan)" />
      <rect x="48" y="30" width="6" height="28" rx="2" fill="#ffffff" />
      <rect x="58" y="42" width="6" height="16" rx="2" fill="var(--accent-cyan)" />
    </svg>
  );
}
