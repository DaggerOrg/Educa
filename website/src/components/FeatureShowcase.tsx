export default function FeatureShowcase() {
  return (
    <section className="section" id="how">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow-label">How it works</span>
          <h2>From a one-line brief to a taught lesson.</h2>
        </div>

        <div className="showcase-row">
          <div className="showcase-copy">
            <h3>Describe it once, get a real syllabus</h3>
            <p>
              Subject, audience, length, style — in your own words, in one prompt.
              Educa scaffolds a live, editable syllabus immediately. Reorder it by hand,
              or ask for a change and it redraws only what you asked for.
            </p>
          </div>
          <div className="showcase-visual">
            <div className="doc-row">
              <span className="doc-icon" />
              <div className="doc-meta">
                <div className="name">Week 3 — Functions &amp; game logic</div>
                <div className="cite">edited by you · preserved on refinement</div>
              </div>
            </div>
            <div className="doc-row">
              <span className="doc-icon" />
              <div className="doc-meta">
                <div className="name">Week 4 — Debugging your first bugs</div>
                <div className="cite">drafted by the agent</div>
              </div>
            </div>
          </div>
        </div>

        <div className="showcase-row is-reverse">
          <div className="showcase-copy">
            <h3>Grounded in the material you already trust</h3>
            <p>
              Upload the books, PDFs, and notes you already teach from. Every generated
              lesson cites the passage it was drawn from — the agent teaches from your
              sources, not its own unverified recall.
            </p>
          </div>
          <div className="showcase-visual">
            <div className="doc-row">
              <span className="doc-icon" />
              <div className="doc-meta">
                <div className="name">Python Crash Course, Ch. 12</div>
                <div className="cite">cited in Week 1, Week 3</div>
              </div>
            </div>
            <div className="doc-row">
              <span className="doc-icon" />
              <div className="doc-meta">
                <div className="name">Automate the Boring Stuff, Ch. 4</div>
                <div className="cite">cited in Week 4</div>
              </div>
            </div>
          </div>
        </div>

        <div className="showcase-row">
          <div className="showcase-copy">
            <h3>Nothing reaches a student unreviewed</h3>
            <p>
              A lesson can't be published until you check it off. The agent can draft,
              refine, and redraft — but the publish action is yours alone, enforced on
              the server, not just hidden in the UI.
            </p>
          </div>
          <div className="showcase-visual">
            <div className="gate-card">
              <div className="name">Week 2 — Loops &amp; simple animation</div>
              <div className="gate-check"><span className="box" />Reviewed — ready to publish</div>
              <span className="gate-publish">Publish to students</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
