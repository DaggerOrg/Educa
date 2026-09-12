// Icon path data from Lucide's graduation-cap.svg (ISC License) --
// see docs/NOTICE.md. Inlined (rather than <img src>) so the
// stroke can follow the surrounding color via currentColor.

interface LogoProps {
  className?: string;
}

export default function Logo({ className = "" }: LogoProps) {
  return (
    <span className={`brand-mark ${className}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z" />
        <path d="M22 10v6" />
        <path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5" />
      </svg>
    </span>
  );
}
