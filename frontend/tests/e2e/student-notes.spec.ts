import { expect, test, type Page } from "@playwright/test";

const COURSE = "course-1";
const LESSON = "lesson-1";
const USER = { id: "student-1", email: "student@example.com", name: "Test Student", role: "student" };

const SUGGESTION = {
  title: "What is present tense",
  summary: "The present tense describes actions happening now or habits.",
  key_points: ["Use the base verb for I/you/we/they", "Add -s for he/she/it"],
  example: "She walks to school every day.",
  source: "lesson",
};

interface Calls {
  suggest: { heading: string; surrounding: string }[];
  saves: { doc?: unknown; sketch?: unknown }[];
}

/** Signs in as a student and mocks every API call the lesson page and notes panel make. */
async function openLesson(page: Page, opts: { suggestStatus?: number } = {}): Promise<Calls> {
  const calls: Calls = { suggest: [], saves: [] };
  await page.addInitScript((user) => {
    localStorage.setItem("educa_auth", JSON.stringify({ token: "playwright-token", user }));
  }, USER);

  const json = (body: unknown, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

  // Anything not mocked below is a 404, so a surprise call can't pass silently as data.
  await page.route("**/api/**", (route) => route.fulfill(json({ detail: "not mocked" }, 404)));
  await page.route(`**/api/courses/${COURSE}/persona`, (route) => route.fulfill(json({ detail: "none" }, 404)));
  await page.route(`**/api/courses/${COURSE}/lessons/${LESSON}`, (route) =>
    route.fulfill(
      json({
        id: LESSON,
        title: "Present tense basics",
        objective: "Form simple present sentences.",
        slides: [{ heading: "Simple present", bullets: ["Habits", "Facts"] }],
        speakerNotes: "",
        quiz: null,
      }),
    ),
  );
  await page.route(`**/api/courses/${COURSE}/lessons/${LESSON}/notes`, async (route) => {
    if (route.request().method() === "PUT") {
      calls.saves.push(route.request().postDataJSON());
      return route.fulfill(json({ doc: null, sketch: null, updatedAt: new Date().toISOString() }));
    }
    return route.fulfill(json({ doc: null, sketch: null, updatedAt: null }));
  });
  await page.route(`**/api/courses/${COURSE}/lessons/${LESSON}/notes/suggest`, async (route) => {
    const body = route.request().postDataJSON();
    calls.suggest.push({ heading: body.heading, surrounding: body.surrounding ?? "" });
    if (opts.suggestStatus && opts.suggestStatus !== 200) {
      return route.fulfill(json({ detail: "Daily limit reached" }, opts.suggestStatus));
    }
    return route.fulfill(json(SUGGESTION));
  });

  await page.goto(`/educa/courses/${COURSE}/lessons/${LESSON}`);
  await page.getByRole("button", { name: "My notes" }).click();
  await expect(page.getByRole("complementary", { name: "My notes" })).toBeVisible();
  await expect(page.getByLabel("Lesson notes")).toBeVisible();
  return calls;
}

const editor = (page: Page) => page.getByLabel("Lesson notes");

test.describe("student notes: ambient AI suggestions", () => {
  test("a pause after a title offers notes, and Accept writes them under it", async ({ page }) => {
    const calls = await openLesson(page);

    await editor(page).click();
    await page.keyboard.type("What is present tense");

    const card = page.getByRole("dialog", { name: /Suggested notes for What is present tense/ });
    await expect(card).toBeVisible({ timeout: 5000 });
    expect(calls.suggest).toHaveLength(1);
    expect(calls.suggest[0].heading).toBe("What is present tense");
    await expect(card).toContainText("Add -s for he/she/it");
    await expect(card).toContainText("From your lesson");

    await card.getByRole("button", { name: "Accept" }).click();
    await expect(card).toBeHidden();
    await expect(editor(page)).toContainText("The present tense describes actions happening now");
    await expect(editor(page).locator("li")).toHaveCount(2);
    await expect(editor(page)).toContainText("Example: She walks to school every day.");

    // The accepted notes are autosaved.
    await expect.poll(() => calls.saves.length, { timeout: 8000 }).toBeGreaterThan(0);
    expect(JSON.stringify(calls.saves.at(-1)?.doc)).toContain("Add -s for he/she/it");
  });

  test("Tab accepts and Escape rejects, and a rejected title isn't asked about again", async ({ page }) => {
    const calls = await openLesson(page);
    await editor(page).click();

    await page.keyboard.type("What is past tense");
    const rejected = page.getByRole("dialog", { name: /Suggested notes for What is past tense/ });
    await expect(rejected).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    await expect(rejected).toBeHidden();
    await expect(editor(page)).not.toContainText("Add -s for he/she/it");

    // Same title, still nothing beneath it: stays quiet.
    await page.keyboard.type(" ");
    await page.keyboard.press("Backspace");
    await page.waitForTimeout(2500);
    expect(calls.suggest).toHaveLength(1);

    // A different title is asked about, and Tab takes it.
    await page.keyboard.press("Enter");
    await page.keyboard.type("What is future tense");
    const next = page.getByRole("dialog", { name: /Suggested notes for What is future tense/ });
    await expect(next).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Tab");
    await expect(next).toBeHidden();
    await expect(editor(page)).toContainText("Add -s for he/she/it");
    expect(calls.suggest).toHaveLength(2);
  });

  test("no suggestion while the student is still typing, or once they've written under the title", async ({ page }) => {
    const calls = await openLesson(page);
    await editor(page).click();

    // Ends like a sentence -> the student's own note, not a title.
    await page.keyboard.type("Verbs change with the subject.");
    await page.waitForTimeout(2500);
    expect(calls.suggest).toHaveLength(0);
    await expect(page.getByRole("dialog", { name: /Suggested notes/ })).toHaveCount(0);
  });

  test("the toggle turns suggestions off, and the choice is remembered", async ({ page }) => {
    const calls = await openLesson(page);
    const toggle = page.getByRole("switch", { name: /AI suggestions/ });
    await expect(toggle).toHaveAttribute("aria-checked", "true");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", "false");

    await editor(page).click();
    await page.keyboard.type("What is present tense");
    await page.waitForTimeout(2500);
    expect(calls.suggest).toHaveLength(0);
    await expect(page.getByRole("dialog", { name: /Suggested notes/ })).toHaveCount(0);

    // Their own typing is still saved with the AI off.
    await expect.poll(() => calls.saves.length, { timeout: 8000 }).toBeGreaterThan(0);

    await page.reload();
    await page.getByRole("button", { name: "My notes" }).click();
    await expect(page.getByRole("switch", { name: /AI suggestions/ })).toHaveAttribute("aria-checked", "false");
  });

  test("turning it off while a suggestion is showing takes the card away", async ({ page }) => {
    await openLesson(page);
    await editor(page).click();
    await page.keyboard.type("What is present tense");
    const card = page.getByRole("dialog", { name: /Suggested notes/ });
    await expect(card).toBeVisible({ timeout: 5000 });

    await page.getByRole("switch", { name: /AI suggestions/ }).click();
    await expect(card).toBeHidden();
  });

  test("hitting the daily limit says so once and stops asking", async ({ page }) => {
    const calls = await openLesson(page, { suggestStatus: 429 });
    await editor(page).click();
    await page.keyboard.type("What is present tense");
    await expect(page.getByText("You've used today's AI note suggestions")).toBeVisible({ timeout: 5000 });

    await page.keyboard.press("Enter");
    await page.keyboard.type("What is past tense");
    await page.waitForTimeout(2500);
    expect(calls.suggest).toHaveLength(1);
  });
});
