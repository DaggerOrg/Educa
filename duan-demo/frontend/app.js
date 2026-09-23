"use strict";
function requireElement(id) {
    const el = document.getElementById(id);
    if (!el) {
        throw new Error(`Missing #${id} element`);
    }
    return el;
}
const form = requireElement("match-form");
const stepper = requireElement("stepper");
const results = requireElement("results");
const submitBtn = requireElement("submit-btn");
const STEP_DELAY_MS = 500;
function steps() {
    return document.querySelectorAll(".step");
}
function resetSteps() {
    steps().forEach((el) => el.classList.remove("active", "done"));
}
function markStep(index, className) {
    steps()[index]?.classList.add(className);
}
function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
async function animateSteps(count) {
    resetSteps();
    stepper.hidden = false;
    for (let i = 0; i < count; i++) {
        markStep(i, "active");
        await wait(STEP_DELAY_MS);
        steps()[i]?.classList.remove("active");
        markStep(i, "done");
    }
}
form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = "Running pipeline…";
    results.hidden = true;
    const payload = {
        name: requireElement("name").value,
        birth_date: requireElement("birth_date").value,
        birth_time: requireElement("birth_time").value || null,
        birth_city: requireElement("birth_city").value || null,
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
        const data = (await response.json());
        markStep(4, "active");
        await wait(STEP_DELAY_MS);
        steps()[4]?.classList.remove("active");
        markStep(4, "done");
        renderResults(data);
    }
    catch (err) {
        console.error(err);
        alert("Something went wrong running the pipeline. Check the console for details.");
    }
    finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Run Matching Pipeline";
    }
});
function renderResults(data) {
    const markersList = requireElement("markers-list");
    markersList.innerHTML = "";
    data.profile.synthetic_markers.forEach((marker) => {
        const li = document.createElement("li");
        li.textContent = `${marker.marker}: ${marker.genotype}`;
        markersList.appendChild(li);
    });
    const astro = data.astrology;
    requireElement("astrology-detail").innerHTML = `
    <p class="astro-sign">${astro.sign}</p>
    <p>Element: ${astro.element}</p>
    <p>Ruling planet: ${astro.ruling_planet}</p>
  `;
    const traitsBars = requireElement("traits-bars");
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
    const matchesGrid = requireElement("matches-grid");
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
    requireElement("disclaimer").textContent = data.disclaimer;
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth" });
}
