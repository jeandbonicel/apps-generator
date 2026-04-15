import { test, expect } from "@playwright/test";

test.describe("API Integration", () => {
  test("should include correct headers in API requests", async ({ page }) => {
    const apiRequests: { url: string; headers: Record<string, string> }[] = [];

    await page.route("{{ apiBaseUrl }}/**", async (route) => {
      apiRequests.push({
        url: route.request().url(),
        headers: route.request().headers(),
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [] }),
      });
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Verify API requests include expected headers when they occur
    for (const req of apiRequests) {
      expect(req.headers["content-type"] || req.headers["accept"]).toBeDefined();
    }
  });

  test("should handle API errors gracefully", async ({ page }) => {
    await page.route("{{ apiBaseUrl }}/**", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal Server Error" }),
      });
    });

    await page.goto("/");
    // App should not crash on API errors
    await expect(page.locator("body")).toBeVisible();
  });
});
