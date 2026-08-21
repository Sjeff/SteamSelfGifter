import { test, expect } from "@playwright/test";
import { mockApi, type ApiCall } from "./mocks";

test.describe("Accounts", () => {
  let calls: ApiCall[];

  test.beforeEach(async ({ page }) => {
    calls = await mockApi(page);
    await page.goto("/accounts");
  });

  test("renders the account list", async ({ page }) => {
    // "Main" also appears in the sidebar's account switcher, so scope to
    // the page content.
    await expect(page.getByRole("main").getByText("Main")).toBeVisible();
  });

  test("saving credentials posts to the account credentials endpoint", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Show account details" }).click();
    await page.getByRole("button", { name: "Set credentials" }).click();
    await page
      .getByPlaceholder("Paste your PHPSESSID here")
      .fill("brand-new-cookie");
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect
      .poll(() =>
        calls.some(
          (c) =>
            c.method === "POST" && /\/accounts\/\d+\/credentials$/.test(c.url),
        ),
      )
      .toBe(true);
  });
});
