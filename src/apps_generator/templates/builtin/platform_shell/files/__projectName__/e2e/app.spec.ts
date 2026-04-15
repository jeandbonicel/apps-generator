import { test, expect } from "@playwright/test";

test.describe("{{ projectTitle or projectName }} - Platform Shell", () => {
  test("should load the application", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/{{ projectTitle or projectName }}/i);
  });

  test("should show sign-in screen when unauthenticated", async ({ page }) => {
    await page.goto("/");
    // ProtectedRoute shows sign-in prompt when not authenticated
    const signInButton = page.getByRole("button", { name: /sign in/i });
    await expect(signInButton).toBeVisible();
  });

  test("should display the project name on login screen", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("{{ projectTitle or projectName }}")).toBeVisible();
  });
});

test.describe("Authenticated Shell", () => {
  // These tests require Clerk authentication.
  // To run them, set up a Clerk test user and configure storageState:
  // See: https://playwright.dev/docs/auth

  test("should display header after login", async ({ page }) => {
    test.skip(true, "Requires Clerk auth setup — see https://playwright.dev/docs/auth");
  });

  test("should display sidebar navigation after login", async ({ page }) => {
    test.skip(true, "Requires Clerk auth setup");
  });

  test("should navigate between remote apps", async ({ page }) => {
    test.skip(true, "Requires Clerk auth setup");
  });
});
