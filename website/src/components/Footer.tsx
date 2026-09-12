import Logo from "./Logo.tsx";

export default function Footer() {
  return (
    <footer>
      <div className="wrap">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="brand">
              <Logo />
              <span className="brand-name">Educa</span>
            </div>
            <p>Agentic AI for teaching — describe a course, get a syllabus you can trust.</p>
          </div>
          <div className="footer-col">
            <h4>Product</h4>
            <a href="#how">How it works</a>
            <a href="#who">Use cases</a>
            <a href="#pricing">Pricing</a>
            <a href="#trust">Trust</a>
          </div>
          <div className="footer-col">
            <h4>Company</h4>
            <a href="#resources">Resources</a>
            <a href="mailto:hello@educa.app">hello@educa.app</a>
            <a href="#get-access">Get early access</a>
          </div>
        </div>
        <p className="footer-fine">Educa is a prototype. Nothing above is a shipped product yet.</p>
      </div>
    </footer>
  );
}
