// Honest stand-in for a customer-logo strip: Educa is pre-launch, so there
// are no customer logos yet. This shows the real stack instead.
const STACK = ["React", "FastAPI", "Claude", "Agno"];

export default function BuiltWith() {
  return (
    <div className="built-with">
      <div className="wrap built-with-row">
        <span className="label">Built on</span>
        {STACK.map((s) => (
          <span className="item" key={s}>{s}</span>
        ))}
      </div>
    </div>
  );
}
