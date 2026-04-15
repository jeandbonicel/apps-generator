import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("should show sign-in button when not authenticated", async ({
    page,
  }) => {
    await page.goto("/");
    const signInButton = page.getByRole("button", { name: /sign in/i });
    await expect(signInButton).toBeVisible();
  });

  test("should open Clerk modal on sign-in click", async ({ page }) => {
    await page.goto("/");
    const signInButton = page.getByRole("button", { name: /sign in/i });
    await signInButton.click();
    // Clerk modal should appear
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });
  });

  test("should display user menu when authenticated", async ({ page }) => {
    // TODO: Set up authenticated state via storageState
    // See: https://playwright.dev/docs/auth
    test.skip(true, "Requires Clerk auth setup");
  });

  test("should handle logout flow", async ({ page }) => {
    test.skip(true, "Requires Clerk auth setup");
  });
});
