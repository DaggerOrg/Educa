const CAPABILITIES = [
  {
    tag: "Delivery",
    title: "Adaptive pacing",
    body: "The agent tracks where a class is getting stuck and adjusts the next lesson accordingly.",
  },
  {
    tag: "Design",
    title: "Vibe visual studio",
    body: "Describe the vibe of an image or diagram and iterate until it fits the lesson.",
  },
  {
    tag: "Oversight",
    title: "Teacher dashboard",
    body: "What's published, who's enrolled, and where students are struggling — in one view.",
  },
];

export default function Capabilities() {
  return (
    <section className="section soft">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow-label">And more</span>
          <h2>The rest of the studio.</h2>
        </div>
        <div className="grid-3">
          {CAPABILITIES.map((c) => (
            <div className="card" key={c.title}>
              <span className="tag">{c.tag}</span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
