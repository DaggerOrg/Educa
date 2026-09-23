import { expect, test, type Page, type Route } from "@playwright/test";

const COURSE = "course-1";
const MODULE = "module-1";

const SCRIPT = {
  title: "Present tense in a minute",
  hook: "Ever wonder why we say she walks but they walk?",
  scenes: [
    { narration: "Use the base verb for I, you, we and they.", on_screen_text: "I walk. They walk.", visual: "Four friends strolling", seconds: 6 },
    { narration: "For he, she and it, add an s.", on_screen_text: "She walks.", visual: "A single hiker", seconds: 6 },
  ],
  takeaway: "He, she, it: add the s.",
};

const json = (body: unknown, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

async function signIn(page: Page, role: "student" | "teacher") {
  await page.addInitScript(
    (user) => localStorage.setItem("educa_auth", JSON.stringify({ token: "playwright-token", user })),
    { id: `${role}-1`, email: `${role}@example.com`, name: `Test ${role}`, role },
  );
  // Anything not mocked is a 404, so a surprise call can't pass silently as data.
  await page.route("**/api/**", (route) => route.fulfill(json({ detail: "not mocked" }, 404)));
}

const lessons = [{ id: "lesson-1", title: "Present tense basics", objective: "Form simple present sentences." }];

test("a student can watch a module's story as a storyboard", async ({ page }) => {
  await signIn(page, "student");
  await page.route("**/api/students/me/courses", (route) =>
    route.fulfill(
      json([{ id: COURSE, teacherId: "t1", title: "English basics", audience: "Beginners", weeks: [{ moduleId: MODULE, week: 1, title: "Tenses", lessons }] }]),
    ),
  );
  await page.route(`**/api/courses/${COURSE}/story-videos`, (route) =>
    route.fulfill(json([{ moduleId: MODULE, week: 1, title: SCRIPT.title, kind: "storyboard" }])),
  );
  await page.route(`**/api/courses/${COURSE}/modules/${MODULE}/story-video`, (route) =>
    route.fulfill(json({ moduleId: MODULE, week: 1, title: SCRIPT.title, kind: "storyboard", script: SCRIPT, narrator: { name: "Ms. Rivera" } })),
  );

  await page.goto(`/educa/courses/${COURSE}`);
  await page.getByRole("button", { name: "Watch story" }).click();

  const player = page.getByRole("dialog", { name: `Story: ${SCRIPT.title}` });
  await expect(player).toBeVisible();
  await expect(player).toContainText("Ms. Rivera");
  // It says plainly that this is a storyboard rather than a filmed video.
  await expect(player).toContainText("scenes are described rather than filmed");
  await expect(player.getByText(SCRIPT.hook)).toBeVisible();

  await player.getByRole("button", { name: "Next scene" }).click();
  await expect(player.getByText("I walk. They walk.")).toBeVisible();
  await expect(player.getByText("Four friends strolling")).toBeVisible();

  await page.keyboard.press("ArrowRight");
  await expect(player.getByText("She walks.")).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(player.getByText(SCRIPT.takeaway)).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(player).toBeHidden();
});

test("a module with no ready story shows no Watch story button", async ({ page }) => {
  await signIn(page, "student");
  await page.route("**/api/students/me/courses", (route) =>
    route.fulfill(
      json([{ id: COURSE, teacherId: "t1", title: "English basics", audience: "Beginners", weeks: [{ moduleId: MODULE, week: 1, title: "Tenses", lessons }] }]),
    ),
  );
  await page.route(`**/api/courses/${COURSE}/story-videos`, (route) => route.fulfill(json([])));

  await page.goto(`/educa/courses/${COURSE}`);
  await expect(page.getByText("Week 1 — Tenses")).toBeVisible();
  await expect(page.getByRole("button", { name: "Watch story" })).toHaveCount(0);
});

test("a teacher drafts, edits, approves and renders a story", async ({ page }) => {
  await signIn(page, "teacher");

  // A tiny in-memory backend for the story.
  let story: Record<string, unknown> | null = null;
  const teacherStory = (status: string) => ({ moduleId: MODULE, status, style: "", kind: null, error: null, script: SCRIPT, ...{} });
  const course = {
    id: COURSE,
    teacherId: "teacher-1",
    title: "English basics",
    audience: "Beginners",
    weeks: [{ moduleId: MODULE, week: 1, title: "Tenses", lessons: lessons.map((l) => ({ ...l, content: null, approved: false, published: false })) }],
  };
  await page.route("**/api/courses/mine", (route) => route.fulfill(json([course])));
  await page.route(`**/api/courses/${COURSE}`, (route) => route.fulfill(json(course)));
  await page.route("**/api/marketplace/mine/listings", (route) => route.fulfill(json([])));

  const putStory = (route: Route, next: Record<string, unknown>) => {
    story = next;
    return route.fulfill(json(story));
  };
  await page.route(`**/api/modules/${MODULE}/story-video`, (route) => {
    if (route.request().method() === "DELETE") {
      story = null;
      return route.fulfill(json({ ok: true }));
    }
    return route.fulfill(json(story));
  });
  await page.route(`**/api/modules/${MODULE}/story-video/script`, (route) => {
    if (route.request().method() === "PUT") {
      const { script } = route.request().postDataJSON();
      return putStory(route, { ...teacherStory("draft"), script });
    }
    return putStory(route, teacherStory("draft"));
  });
  await page.route(`**/api/modules/${MODULE}/story-video/approve`, (route) => putStory(route, teacherStory("approved")));
  await page.route(`**/api/modules/${MODULE}/story-video/render`, (route) => putStory(route, { ...teacherStory("ready"), kind: "storyboard" }));

  await page.goto("/");
  await page.getByRole("button", { name: "Story video" }).click();
  const panel = page.getByRole("dialog", { name: "Story video" });
  await expect(panel).toBeVisible();

  await panel.getByRole("button", { name: "Write the story" }).click();
  await expect(panel.getByLabel("Title")).toHaveValue(SCRIPT.title);
  await expect(panel.getByText("Draft", { exact: true })).toBeVisible();

  // Editing makes the script "dirty": it must be saved before it can be approved.
  await panel.getByLabel("Opening line").fill("Here's a quick one about verbs.");
  await expect(panel.getByText("Unsaved edits")).toBeVisible();
  await expect(panel.getByRole("button", { name: "Approve script" })).toBeDisabled();
  await panel.getByRole("button", { name: "Save edits" }).click();
  await expect(panel.getByText("Unsaved edits")).toBeHidden();
  await expect(panel.getByLabel("Opening line")).toHaveValue("Here's a quick one about verbs.");

  await panel.getByRole("button", { name: "Approve script" }).click();
  await expect(panel.getByText("Script approved")).toBeVisible();

  await panel.getByRole("button", { name: "Render", exact: true }).click();
  await expect(panel.getByText("Ready for students")).toBeVisible();
  await expect(panel.getByText(/no video provider is connected/)).toBeVisible();

  await panel.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByRole("dialog", { name: `Story: ${SCRIPT.title}` })).toBeVisible();
});
