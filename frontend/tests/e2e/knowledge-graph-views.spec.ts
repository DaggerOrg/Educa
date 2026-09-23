import { expect, test, type Page } from "@playwright/test";
import { englishKnowledgeGraph } from "../../src/knowledge-graph/data/englishKnowledgeGraph.ts";
import type { KnowledgeNode, KnowledgeRelationship } from "../../src/knowledge-graph/types/knowledgeGraph.ts";
import { buildLearningPath } from "../../src/knowledge-graph/utils/learningPath.ts";

const node = (id: string, patch: Partial<KnowledgeNode> = {}): KnowledgeNode => ({
  id, type: "concept", name: id, status: "teacher_approved", ...patch,
});
const prereq = (source: string, target: string): KnowledgeRelationship => ({
  id: `${source}>${target}`, sourceId: source, targetId: target, type: "prerequisite_of", evidenceType: "teacher_created", teacherApproved: true,
});
const link = (source: string, target: string, type: KnowledgeRelationship["type"]): KnowledgeRelationship => ({
  ...prereq(source, target), id: `${source}~${target}`, type,
});
const names = (items: { node: KnowledgeNode }[]) => items.map((i) => i.node.name);

test.describe("learning path ordering", () => {
  const path = buildLearningPath(englishKnowledgeGraph.nodes, englishKnowledgeGraph.relationships);
  const section = (key: string) => path.sections.find((s) => s.key === key)!;

  test("the sample graph reads A1 to B2, then what has no topic", () => {
    expect(path.grouping).toBe("level");
    expect(path.sections.map((s) => s.key)).toEqual(["A1", "A2", "B1", "B2", "other"]);
    expect(names(section("A1").items)).toEqual(["Have / Has", "Present Simple"]);
    expect(names(section("B2").items)).toEqual(["Conditionals", "Present Perfect Continuous"]);
    expect(names(section("other").items)).toEqual(["Listening"]);
  });

  test("level nodes are never shown, and topics without a level take the one they build on", () => {
    const shown = path.sections.flatMap((s) => names(s.items));
    for (const level of ["A1", "A2", "B1", "B2", "C1", "C2"]) expect(shown).not.toContain(level);
    // The learning objective has no level of its own; it builds on Present Perfect (B1).
    expect(names(section("B1").items)).toContain("Students can describe past life experiences.");
  });

  test("a topic lists what comes before it, and the practice attached to it", () => {
    const perfect = section("B1").items.find((i) => i.node.name === "Present Perfect")!;
    expect(perfect.after.map((n) => n.name)).toEqual(["Have / Has", "Past Participle", "Past-time concepts"]);
    expect(perfect.support.map((n) => n.name)).toEqual(expect.arrayContaining(["Speaking", "Writing", "Present Perfect Quiz"]));
    // Skills come before exercises, then resources.
    expect(perfect.support.map((n) => n.type)).toEqual([...perfect.support.map((n) => n.type)].sort(
      (a, b) => ["skill", "exercise", "resource"].indexOf(a) - ["skill", "exercise", "resource"].indexOf(b),
    ));
    expect(perfect.role).toBeUndefined();
    expect(section("A1").items[0].role).toBe("start");
  });

  test("with no levels anywhere, steps follow the learn-this-first arrows", () => {
    const result = buildLearningPath(
      [node("a"), node("b"), node("c"), node("d")],
      [prereq("a", "b"), prereq("b", "c")],
    );
    expect(result.grouping).toBe("step");
    expect(result.sections.map((s) => [s.label, names(s.items)])).toEqual([
      ["Step 1", ["a", "d"]],
      ["Step 2", ["b"]],
      ["Step 3", ["c"]],
    ]);
  });

  test("a topic with no level and no links goes to 'No level yet' when the others have levels", () => {
    const result = buildLearningPath([node("a", { cefrLevel: "A1" }), node("lonely")], []);
    expect(result.sections.map((s) => [s.kind, names(s.items)])).toEqual([
      ["stage", ["a"]],
      ["unleveled", ["lonely"]],
    ]);
  });

  test("a level is inherited from what builds on the topic when nothing comes before it", () => {
    const result = buildLearningPath([node("early"), node("late", { cefrLevel: "B2" })], [prereq("early", "late")]);
    expect(result.sections.map((s) => [s.key, names(s.items)])).toEqual([["B2", ["early", "late"]]]);
  });

  test("a cycle can't hang or drop topics", () => {
    const result = buildLearningPath([node("a"), node("b")], [prereq("a", "b"), prereq("b", "a")]);
    expect(result.sections.flatMap((s) => names(s.items)).sort()).toEqual(["a", "b"]);
  });

  test("a graph of only skills still gets a path, and nothing is 'not tied to a topic'", () => {
    const result = buildLearningPath([node("reading", { type: "skill" }), node("writing", { type: "skill" })], []);
    expect(result.sections.map((s) => s.kind)).toEqual(["stage"]);
    expect(names(result.sections[0].items)).toEqual(["reading", "writing"]);
  });

  test("an empty graph has no sections; links to missing nodes are ignored", () => {
    expect(buildLearningPath([], []).sections).toEqual([]);
    const result = buildLearningPath([node("a")], [prereq("a", "ghost"), link("ghost", "a", "practices")]);
    expect(names(result.sections[0].items)).toEqual(["a"]);
  });
});

const BOARDS = [
  { id: "b1", title: "English Language — B1 Curriculum", createdBy: "u1", createdByName: "Soe Moe", createdAt: "2026-09-01T00:00:00Z" },
  { id: "b2", title: "Grammar Unit 3", createdBy: "u1", createdByName: "Soe Moe", createdAt: "2026-09-02T00:00:00Z" },
  { id: "b3", title: "Untitled", createdBy: "u2", createdByName: "Ava", createdAt: "2026-09-03T00:00:00Z" },
];

async function openKnowledgeGraph(page: Page) {
  await page.addInitScript(() =>
    localStorage.setItem("educa_auth", JSON.stringify({ token: "t", user: { id: "t1", email: "t@example.com", name: "Test Teacher", role: "teacher" } })),
  );
  const json = (body: unknown) => ({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  await page.route("**/api/**", (route) => route.fulfill(json([])));
  await page.route("**/api/kg-boards", (route) => route.fulfill(json(BOARDS)));
  await page.goto("/");
  await page.getByRole("button", { name: "Knowledge Graph" }).click();
  await expect(page.getByRole("button", { name: "Collapse live graphs" })).toBeVisible();
}

test.describe("knowledge graph: live graphs panel", () => {
  test("collapsed, it is a rail with new graph, the example graph and one chip per board", async ({ page }) => {
    await openKnowledgeGraph(page);
    await page.getByRole("button", { name: "Collapse live graphs" }).click();

    await expect(page.getByRole("button", { name: "New graph" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Example graph" })).toHaveAttribute("aria-pressed", "true");
    for (const [title, initials] of [["English Language — B1 Curriculum", "EL"], ["Grammar Unit 3", "GU"], ["Untitled", "UN"]]) {
      const chip = page.getByRole("button", { name: title, exact: true });
      await expect(chip).toHaveText(initials);
      await expect(chip).toHaveAttribute("title", new RegExp(`^${title}`));
      await expect(chip).toHaveAttribute("aria-pressed", "false");
    }

    // New graph works without expanding the panel.
    await page.getByRole("button", { name: "New graph" }).click();
    await expect(page.getByText("New knowledge graph")).toBeVisible();
  });

  test("expanded, the example graph is the first entry and is the current one", async ({ page }) => {
    await openKnowledgeGraph(page);
    const items = page.locator(".kg-history-item");
    await expect(items.first()).toContainText("Example graph");
    await expect(items.first()).toHaveClass(/is-active/);
    await expect(items).toHaveCount(4);
    await expect(page.getByRole("button", { name: "Back to example graph" })).toHaveCount(0);
  });
});

test.describe("knowledge graph: Graph / Path view", () => {
  test("Path lists the levels from basics to advanced, and the direction can be flipped", async ({ page }) => {
    await openKnowledgeGraph(page);
    await expect(page.locator(".react-flow")).toBeVisible();

    await page.getByRole("button", { name: "Path", exact: true }).click();
    await expect(page.locator(".react-flow")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Learning path" })).toBeVisible();
    await expect(page.getByText("Basics · start here")).toBeVisible();
    await expect(page.getByText("Most advanced")).toBeVisible();

    const y = async (level: string) => (await page.getByRole("region", { name: `Level ${level}` }).boundingBox())!.y;
    expect(await y("A1")).toBeLessThan(await y("A2"));
    expect(await y("A2")).toBeLessThan(await y("B1"));
    expect(await y("B1")).toBeLessThan(await y("B2"));

    await page.getByRole("button", { name: "Basics at bottom" }).click();
    await expect(page.getByRole("button", { name: "Basics at bottom" })).toHaveAttribute("aria-pressed", "true");
    expect(await y("B2")).toBeLessThan(await y("B1"));
    expect(await y("A2")).toBeLessThan(await y("A1"));
  });

  test("a topic card shows what comes before it and opens in the inspector", async ({ page }) => {
    await openKnowledgeGraph(page);
    await page.getByRole("button", { name: "Path", exact: true }).click();

    const card = page.locator('[data-node-id="concept-present-perfect"]');
    await expect(card).toContainText("Have / Has");
    await expect(card).toContainText("Past Participle");
    await card.locator(".kg-path-card-main").click();
    await expect(card).toHaveClass(/is-selected/);
    await expect(page.locator(".kg-right")).toContainText("Present Perfect");

    // A card with a lot of practice attached folds the rest away.
    await card.getByRole("button", { name: /more$/ }).click();
    await expect(card.getByRole("button", { name: "Show less" })).toBeVisible();
  });

  test("the filters still apply, and the choice is remembered", async ({ page }) => {
    await openKnowledgeGraph(page);
    await page.getByRole("button", { name: "Path", exact: true }).click();
    await expect(page.getByRole("region", { name: "Level B2" })).toBeVisible();

    await page.getByRole("button", { name: "B2", exact: true }).click(); // CEFR filter: hide B2
    await expect(page.getByRole("region", { name: "Level B2" })).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Level B1" })).toBeVisible();

    await page.reload();
    await page.getByRole("button", { name: "Knowledge Graph" }).click();
    await expect(page.getByRole("heading", { name: "Learning path" })).toBeVisible();
    await page.getByRole("button", { name: "Graph", exact: true }).click();
    await expect(page.locator(".react-flow")).toBeVisible();
  });
});
