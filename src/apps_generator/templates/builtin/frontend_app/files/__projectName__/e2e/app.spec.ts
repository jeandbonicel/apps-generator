import { test, expect } from "@playwright/test";

test.describe("{{ projectTitle or projectName }} - App", () => {
  test("should load the application in standalone mode", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/{{ projectTitle or projectName }}/i);
  });

  test("should render the main content", async ({ page }) => {
    await page.goto("/");
    const main = page.locator("main, #root, [data-testid='app']");
    await expect(main.first()).toBeVisible();
  });

  test("should have no console errors on load", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    expect(errors).toEqual([]);
  });
});
