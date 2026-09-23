interface MatchRequestPayload {
  name: string;
  birth_date: string;
  birth_time: string | null;
  birth_city: string | null;
}

interface SyntheticMarker {
  marker: string;
  genotype: string;
}

interface AstrologyProfile {
  sign: string;
  element: string;
  ruling_planet: string;
}

interface GemMatch {
  id: string;
  name: string;
  color: string;
  element: string;
  description: string;
  score: number;
  reasoning: string;
  rank: number;
}

interface MatchResponse {
  profile: {
    seed: string;
    synthetic_markers: SyntheticMarker[];
  };
  trait_scores: Record<string, number>;
  astrology: AstrologyProfile;
  matches: GemMatch[];
  disclaimer: string;
}

function requireElement<T extends HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) {
    throw new Error(`Missing #${id} element`);
  }
  return el as T;
}

const form = requireElement<HTMLFormElement>("match-form");
const stepper = requireElement<HTMLElement>("stepper");
const results = requireElement<HTMLElement>("results");
const submitBtn = requireElement<HTMLButtonElement>("submit-btn");

const STEP_DELAY_MS = 500;

function steps(): NodeListOf<HTMLElement> {
  return document.querySelectorAll<HTMLElement>(".step");
}

function resetSteps(): void {
  steps().forEach((el) => el.classList.remove("active", "done"));
}

function markStep(index: number, className: string): void {
  steps()[index]?.classList.add(className);
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function animateSteps(count: number): Promise<void> {
  resetSteps();
  stepper.hidden = false;
  for (let i = 0; i < count; i++) {
    markStep(i, "active");
    await wait(STEP_DELAY_MS);
    steps()[i]?.classList.remove("active");
    markStep(i, "done");
  }
}

form.addEventListener("submit", async (event: SubmitEvent) => {
  event.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Running pipeline…";
  results.hidden = true;

  const payload: MatchRequestPayload = {
    name: requireElement<HTMLInputElement>("name").value,
    birth_date: requireElement<HTMLInputElement>("birth_date").value,
    birth_time: requireElement<HTMLInputElement>("birth_time").value || null,
    birth_city: requireElement<HTMLInputElement>("birth_city").value || null,
  };

  try {
    const [response] = await Promise.all([
      fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
      animateSteps(4),
    ]);

    if (!response.ok) {
      throw new Error(`Pipeline request failed: ${response.status}`);
    }

    const data = (await response.json()) as MatchResponse;
    markStep(4, "active");
    await wait(STEP_DELAY_MS);
    steps()[4]?.classList.remove("active");
    markStep(4, "done");

    renderResults(data);
  } catch (err) {
    console.error(err);
    alert("Something went wrong running the pipeline. Check the console for details.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Run Matching Pipeline";
  }
});

function renderResults(data: MatchResponse): void {
  const markersList = requireElement<HTMLUListElement>("markers-list");
  markersList.innerHTML = "";
  data.profile.synthetic_markers.forEach((marker) => {
    const li = document.createElement("li");
    li.textContent = `${marker.marker}: ${marker.genotype}`;
    markersList.appendChild(li);
  });

  const astro = data.astrology;
  requireElement<HTMLDivElement>("astrology-detail").innerHTML = `
    <p class="astro-sign">${astro.sign}</p>
    <p>Element: ${astro.element}</p>
    <p>Ruling planet: ${astro.ruling_planet}</p>
  `;

  const traitsBars = requireElement<HTMLDivElement>("traits-bars");
  traitsBars.innerHTML = "";
  Object.entries(data.trait_scores).forEach(([label, score]) => {
    const row = document.createElement("div");
    row.className = "trait-row";
    row.innerHTML = `
      <div class="trait-label">${label}</div>
      <div class="trait-bar-track"><div class="trait-bar-fill" style="width:${score}%"></div></div>
      <div class="trait-score">${score}</div>
    `;
    traitsBars.appendChild(row);
  });

  const matchesGrid = requireElement<HTMLDivElement>("matches-grid");
  matchesGrid.innerHTML = "";
  data.matches.forEach((match) => {
    const card = document.createElement("div");
    card.className = "gem-card";
    card.innerHTML = `
      <div class="gem-swatch" style="background:${match.color}"></div>
      <div class="gem-rank">#${match.rank}</div>
      <h3>${match.name}</h3>
      <div class="gem-score">${match.score}% match</div>
      <p class="gem-reasoning">${match.reasoning}</p>
      <p class="gem-description">${match.description}</p>
    `;
    matchesGrid.appendChild(card);
  });

  requireElement<HTMLParagraphElement>("disclaimer").textContent = data.disclaimer;

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth" });
}
