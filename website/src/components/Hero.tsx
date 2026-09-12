export default function Hero() {
  return (
    <section className="hero" id="top">
      <div className="hero-glow" aria-hidden="true" />
      <div className="wrap">
        <div className="hero-inner">
          <span className="eyebrow-pill"><span className="dot" />Agentic AI for teaching</span>
          <h1>The curriculum infrastructure behind a course you'd actually teach.</h1>
          <p className="lede">
            Describe a course in one prompt. Educa drafts the syllabus, grounds every
            lesson in the books you already trust, and never shows a student a slide
            you haven't approved.
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#get-access">Get early access</a>
            <a className="btn btn-outline" href="#how">See how it works</a>
          </div>
        </div>

        <div className="hero-canvas">
          <div
            className="hero-visual"
            role="img"
            aria-label="Educa's Teacher Studio: a chat panel where a teacher describes a course, next to the generated syllabus with weekly lessons"
          >
            <div className="ghost-card" aria-hidden="true">
              <div className="name">Week 2 — Loops &amp; animation</div>
              <div className="row"><span className="box" />Reviewed — ready to publish</div>
            </div>

            <div className="screenshot">
              <div className="screenshot-bar">
                <span className="chrome-dot r" /><span className="chrome-dot y" /><span className="chrome-dot g" />
                <span className="screenshot-url">app.educa.ai/studio</span>
              </div>
              <div className="screenshot-body">
                <div className="screenshot-chat">
                  <span className="screenshot-label">Curriculum agent</span>
                  <div className="chat-bubble">
                    An 8-week intro to Python for 14-year-olds, project-based, ending with
                    a small game they build themselves.
                  </div>
                  <div className="chat-reply">
                    <span className="avatar" />
                    <p>Drafted an 8-week syllabus grounded in your uploaded textbook — take a look on the right.</p>
                  </div>
                </div>
                <div className="screenshot-syllabus">
                  <span className="screenshot-label">Syllabus</span>
                  <div className="syllabus-title">Intro to Python — Build Your First Game</div>
                  <div className="syllabus-row"><span className="syllabus-tag">WK 1</span> Variables &amp; the turtle canvas</div>
                  <div className="syllabus-row"><span className="syllabus-tag">WK 2</span> Loops &amp; simple animation</div>
                  <div className="syllabus-row"><span className="syllabus-tag">WK 3</span> Functions &amp; game logic</div>
                  <div className="syllabus-row is-more">+ 5 more weeks, fully editable</div>
                </div>
              </div>
            </div>

            <span className="floating-badge"><span className="dot" />Publish gate enforced</span>
          </div>
        </div>
      </div>
    </section>
  );
}
