import { useState } from "react";
import Logo from "./Logo.tsx";
import ThemeToggle from "./ThemeToggle.tsx";

const LINKS = [
  { href: "#how", label: "Product" },
  { href: "#who", label: "Use Cases" },
  { href: "#pricing", label: "Pricing" },
  { href: "#resources", label: "Resources" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);

  function closeAndGo() {
    setOpen(false);
  }

  return (
    <nav className="nav">
      <div className="nav-row">
        <a href="#top" className="brand">
          <Logo />
          <span className="brand-name">Educa</span>
        </a>
        <div className="nav-links">
          {LINKS.map((l) => (
            <a className="nav-link" href={l.href} key={l.href}>{l.label}</a>
          ))}
          <a className="btn btn-primary" href="#get-access">Get early access</a>
          <ThemeToggle />
        </div>
        <button
          className="nav-toggle"
          type="button"
          aria-expanded={open}
          aria-controls="nav-mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 6h18M3 12h18M3 18h18" /></svg>
          )}
        </button>
        <div className={`nav-mobile${open ? " is-open" : ""}`} id="nav-mobile-menu">
          {LINKS.map((l) => (
            <a className="nav-link" href={l.href} key={l.href} onClick={closeAndGo}>{l.label}</a>
          ))}
          <a className="btn btn-primary" href="#get-access" onClick={closeAndGo}>Get early access</a>
        </div>
      </div>
    </nav>
  );
}
