import { expect, test } from "@playwright/test";

test("renders the auth screen and validates the teacher signup flow", async ({ page }) => {
  await page.route("**/api/auth/signup", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "playwright-test-token",
        user: { id: "user-playwright", email: "teacher@example.com", name: "Test Teacher", role: "teacher" },
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("EDUCA.")).toBeVisible();
  await page.getByRole("button", { name: "Sign up" }).click();
  await page.getByLabel("Name").fill("Test Teacher");
  await page.getByLabel("Email").fill("teacher@example.com");
  await page.getByLabel("Password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Teacher" }).click();
  await expect(page.getByRole("button", { name: "Create account" })).toBeEnabled();
  await page.getByRole("button", { name: "Create account" }).click();

  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("educa_auth")))
    .toContain("playwright-test-token");
});