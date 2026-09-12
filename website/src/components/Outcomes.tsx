// Framed as principles Educa is built around, not measured statistics --
// there's no user base yet to measure. Honest > a fabricated percentage.
const OUTCOMES = [
  { big: "Minutes", body: "From a one-line brief to a first draft, not a weekend of prep." },
  { big: "Grounded", body: "Every lesson traces back to a passage in your own material." },
  { big: "Reviewed", body: "Nothing reaches a student without your sign-off." },
];

export default function Outcomes() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="outcomes">
          {OUTCOMES.map((o) => (
            <div className="outcome" key={o.big}>
              <div className="big">{o.big}</div>
              <p>{o.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
