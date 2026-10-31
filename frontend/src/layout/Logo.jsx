/** Simple inline-SVG brain-in-scan-frame logo mark. */
export function Logo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="#2563EB" />
      <path d="M7 11V9a2 2 0 0 1 2-2h2M21 7h2a2 2 0 0 1 2 2v2M25 21v2a2 2 0 0 1-2 2h-2M11 25H9a2 2 0 0 1-2-2v-2" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M16 11.5c-1-1.3-3.6-1.1-4.2.8-1.6.2-2.3 2.2-1.2 3.3-.6 1.5.4 3.1 2 3.1.5 1.2 2.1 1.7 3.4.9V11.5Zm0 0c1-1.3 3.6-1.1 4.2.8 1.6.2 2.3 2.2 1.2 3.3.6 1.5-.4 3.1-2 3.1-.5 1.2-2.1 1.7-3.4.9" stroke="#fff" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
