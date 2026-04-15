import { test, expect } from "@playwright/test";

test.describe("Tenant Switcher", () => {
  // The tenant switcher (Clerk OrganizationSwitcher or custom dropdown)
  // is only visible after authentication. These tests require Clerk auth setup.
  // See: https://playwright.dev/docs/auth

  test("should display the tenant switcher in header after login", async ({
    page,
  }) => {
    test.skip(true, "Requires Clerk auth setup");
  });

  test("should persist selected tenant across page reloads", async ({
    page,
  }) => {
    test.skip(true, "Requires Clerk auth setup");
  });

  test("should include X-Tenant-ID header in API requests", async ({
    page,
  }) => {
    test.skip(true, "Requires Clerk auth setup");
  });
});
