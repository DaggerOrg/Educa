const PERSONAS = [
  {
    tag: "Teacher",
    title: "Independent teacher or tutor",
    body: "Runs their own cohort — coding, languages, test prep — outside a traditional school.",
  },
  {
    tag: "Teacher",
    title: "Corporate trainer",
    body: "Onboards or upskills employees, grounded in the company's own documents.",
  },
  {
    tag: "Teacher",
    title: "Domain expert or hobbyist",
    body: "A chef, musician, or engineer teaching a small paid cohort their craft.",
  },
  {
    tag: "Learner",
    title: "And their students",
    body: "Lessons that meet them where they are, with immediate feedback on how they're doing.",
  },
];

export default function WhoItsFor() {
  return (
    <section className="section soft" id="who">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow-label">Use Cases</span>
          <h2>Built for anyone who has something to teach.</h2>
        </div>
        <div className="grid-4">
          {PERSONAS.map((p) => (
            <div className="card" key={p.title}>
              <span className="tag">{p.tag}</span>
              <h3>{p.title}</h3>
              <p>{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
