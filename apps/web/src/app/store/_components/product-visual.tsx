// Placeholder packaging drawn in SVG until the real product renders exist.
// One silhouette per product type, tinted by routine step.

const TINTS: Record<number, [string, string]> = {
  1: ["#e9dfd1", "#c9b79f"],
  2: ["#e4e7dc", "#a9b59b"],
  3: ["#efe1d6", "#d1a98f"],
  4: ["#ece6db", "#b8a88f"],
  5: ["#f1e8d8", "#d8bf8f"],
  6: ["#e7e2ea", "#ad9fb8"],
};

function Shape({ type, body, accent }: { type: string; body: string; accent: string }) {
  switch (type) {
    case "Cleanser":
    case "Sunscreen":
      return (
        <g>
          <rect x="70" y="40" width="60" height="120" rx="14" fill={body} stroke={accent} strokeWidth="2" />
          <rect x="82" y="160" width="36" height="22" rx="4" fill={accent} />
        </g>
      );
    case "Serum":
      return (
        <g>
          <rect x="88" y="22" width="24" height="26" rx="8" fill={accent} />
          <rect x="94" y="46" width="12" height="12" fill={accent} opacity="0.7" />
          <rect x="70" y="58" width="60" height="118" rx="16" fill={body} stroke={accent} strokeWidth="2" />
        </g>
      );
    case "Moisturizer":
      return (
        <g>
          <rect x="52" y="78" width="96" height="22" rx="6" fill={accent} />
          <rect x="56" y="98" width="88" height="70" rx="14" fill={body} stroke={accent} strokeWidth="2" />
        </g>
      );
    case "Mask":
      return (
        <g>
          <path d="M55 40 h90 l-6 140 h-78 z" fill={body} stroke={accent} strokeWidth="2" />
          <path d="M55 40 h90 v14 h-90 z" fill={accent} opacity="0.8" />
        </g>
      );
    default: // Toner, Exfoliant
      return (
        <g>
          <rect x="88" y="24" width="24" height="22" rx="4" fill={accent} />
          <rect x="72" y="46" width="56" height="132" rx="10" fill={body} stroke={accent} strokeWidth="2" />
        </g>
      );
  }
}

export function ProductVisual({ type, step, title }: { type: string; step: number; title: string }) {
  const [bg, accent] = TINTS[step] ?? TINTS[1];
  return (
    <svg viewBox="0 0 200 200" role="img" aria-label={`${title} packaging`} className="h-full w-full">
      <rect width="200" height="200" fill={bg} />
      <circle cx="150" cy="44" r="54" fill="#fff" opacity="0.35" />
      <Shape type={type} body="#fbf8f3" accent={accent} />
      <text x="100" y="118" textAnchor="middle" fontSize="9" letterSpacing="2.5" fill="#5d5248" fontFamily="serif">
        ARDEA
      </text>
    </svg>
  );
}
