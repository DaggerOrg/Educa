// Educa is pre-launch: there's no real pricing tier or resource library
// yet. Both cards say that plainly rather than inventing tiers or a blog
// that doesn't exist.
export default function PricingResources() {
  return (
    <section className="section soft">
      <div className="wrap">
        <div className="grid-2">
          <div className="card" id="pricing">
            <span className="tag">Pricing</span>
            <h3>Free during early access</h3>
            <p>
              We're focused on making Educa work well for real classrooms first.
              Pricing will be announced closer to general launch — everyone in
              early access uses it free until then.
            </p>
          </div>
          <div className="card" id="resources">
            <span className="tag">Resources</span>
            <h3>No blog yet — just us</h3>
            <p>
              Documentation and guides will live here once Educa is further along.
              For now, the fastest way to learn more is to{" "}
              <a className="link-inline" href="mailto:hello@educa.app">ask us directly</a>.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
