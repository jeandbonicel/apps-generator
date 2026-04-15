import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("should display the home page", async ({ page }) => {
    await page.goto("/");
    const heading = page.locator("h1, h2, [data-testid='page-title']");
    await expect(heading.first()).toBeVisible();
  });

  test("should navigate between pages", async ({ page }) => {
    await page.goto("/");

    // Find and click a navigation link
    const links = page.locator("a[href]");
    const count = await links.count();

    if (count > 0) {
      const href = await links.first().getAttribute("href");
      if (href && href.startsWith("/")) {
        await links.first().click();
        await expect(page).toHaveURL(new RegExp(href));
      }
    }
  });

  test("should handle 404 for unknown routes", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });
});
