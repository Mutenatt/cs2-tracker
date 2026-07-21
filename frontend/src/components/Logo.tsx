export function Logo({ size = 22 }: { size?: number }) {
  return (
    <span className="cs-logo" style={{ fontSize: size }}>
      c<span>Stats</span>
    </span>
  );
}
