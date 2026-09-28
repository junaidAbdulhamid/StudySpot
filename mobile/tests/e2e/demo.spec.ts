import { expect, Page, test } from "@playwright/test";

const password = "StudySpot123!";

async function skipIntro(page: Page) {
  await page.goto("/");
  const skip = page.getByRole("button", { name: "Skip", exact: true });
  if (await skip.isVisible()) await skip.click();
}

async function finishPreferences(page: Page) {
  const next = page.getByRole("button", { name: "Next", exact: true });
  const home = page.getByText("Your next great idea needs a good spot.");
  await expect(next.or(home)).toBeVisible();
  if (await next.isVisible()) {
    for (let step = 0; step < 3; step++) {
      await next.click();
      await expect(page.getByText(`STEP ${step + 2} OF 4`)).toBeVisible();
    }
    await page.getByRole("button", { name: "Finish", exact: true }).click();
  }
  await expect(home).toBeVisible();
}

async function signIn(page: Page, email: string) {
  await skipIntro(page);
  await page.getByRole("button", { name: "Continue with Email" }).click();
  await page.getByRole("textbox", { name: "Email", exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await finishPreferences(page);
}

async function openFenwick(page: Page) {
  await page.getByRole("tab", { name: "Explore" }).click();
  await page.getByRole("textbox").fill("floor 4");
  await page
    .getByRole("button", { name: "View Fenwick Library, Floor 4", exact: true })
    .click();
}

test("foreground nearby discovery, shared filters, floor preview and directions", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({
    latitude: 38.8315,
    longitude: -77.3075,
    accuracy: 20,
  });
  await signIn(page, "alex@example.edu");
  const nearby = page.waitForResponse(
    (response) =>
      response.url().includes("/locations/nearby?") &&
      response.status() === 200,
  );
  await page
    .getByRole("button", { name: "Enable Location", exact: true })
    .click();
  const response = await nearby;
  const rows = (await response.json()).data;
  expect(rows.length).toBeGreaterThan(0);
  expect(rows[0].distance_meters).toBeLessThanOrEqual(
    rows.at(-1).distance_meters,
  );
  await expect(
    page.getByText("Study spots near you", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Explore" }).click();
  await page.getByRole("button", { name: "Nearest", exact: true }).click();
  await page.getByRole("button", { name: "Noise ⌄", exact: true }).click();
  await page.getByRole("button", { name: "Quiet", exact: true }).click();
  await page.getByRole("button", { name: "Show study spaces" }).click();
  await page.getByRole("button", { name: "Amenities ⌄", exact: true }).click();
  await page.getByRole("button", { name: "Outlets", exact: true }).click();
  await page.getByRole("button", { name: "Show study spaces" }).click();
  await page.getByRole("tab", { name: "Map" }).click();
  await expect(page.getByRole("button", { name: "Noise ⌄" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page
    .getByRole("button", { name: "Fenwick Library", exact: true })
    .click();
  await page.getByRole("button", { name: "Floor 4", exact: true }).click();
  await page
    .getByRole("button", { name: "View Fenwick Library, Floor 4", exact: true })
    .click();
  await expect(page).toHaveURL(/\/location\/zone-1/);
  await expect(
    page
      .getByText(/away · straight-line/)
      .filter({ visible: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: /Directions/ }).click();
  await expect(
    page.getByRole("button", { name: "Open walking directions" }),
  ).toBeVisible();
  await context.route("https://www.google.com/maps/dir/**", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: "External maps test destination",
    }),
  );
  const popup = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Open walking directions" }).click();
  const maps = await popup;
  await expect(maps).toHaveURL(/google\.com\/maps\/dir\/.*travelmode=walking/);
  await maps.close();
});

test("denied location keeps campus browsing usable without invented distances", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator.geolocation, "getCurrentPosition", {
      value: (
        _success: unknown,
        failure: (error: { code: number; message: string }) => void,
      ) => failure({ code: 1, message: "Permission denied" }),
    });
  });
  await signIn(page, "blair@example.edu");
  await page
    .getByRole("button", { name: "Enable Location", exact: true })
    .click();
  await expect(
    page.getByText(/Campus browsing is still available/),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Explore" }).click();
  await expect(
    page.getByRole("button", { name: "Nearest", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByText(/min walk/)).toHaveCount(0);
  await page.getByRole("textbox").fill("floor 4");
  await expect(
    page.getByRole("button", {
      name: "View Fenwick Library, Floor 4",
      exact: true,
    }),
  ).toBeVisible();
});

test("fresh account completes onboarding and persists personalization", async ({
  page,
}) => {
  await skipIntro(page);
  await page.getByRole("button", { name: "Continue with Email" }).click();
  await page.getByRole("button", { name: /Sign up/ }).click();
  const email = `new-${Date.now()}@example.edu`;
  await page.getByRole("textbox", { name: "Email", exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("textbox", { name: "Confirm password", exact: true })
    .fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
  await finishPreferences(page);
  await openFenwick(page);
  await page.getByRole("button", { name: "Save to favorites" }).click();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Remove from favorites" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Go back" }).click();
  await page.getByRole("tab", { name: "Profile" }).click();
  await expect(
    page.getByText("1 saved location", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Study Preferences" }).click();
  await page.getByRole("button", { name: "Moderate", exact: true }).click();
  for (let step = 0; step < 3; step++) {
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.getByText(`STEP ${step + 2} OF 4`)).toBeVisible();
  }
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await expect(page.getByText("moderate", { exact: true })).toBeVisible();
});

test("returning session restores without showing login", async ({ page }) => {
  await signIn(page, "alex@example.edu");
  await page.reload();
  await expect(
    page.getByText("Your next great idea needs a good spot."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continue with Email" }),
  ).toHaveCount(0);
});

test("logout clears state and a different account is isolated", async ({
  page,
}) => {
  await signIn(page, "alex@example.edu");
  await openFenwick(page);
  const save = page.getByRole("button", { name: "Save to favorites" });
  if (await save.isVisible()) await save.click();
  await page.getByRole("button", { name: "Go back" }).click();
  await page.getByRole("tab", { name: "Profile" }).click();
  await page.getByRole("button", { name: "Log Out", exact: true }).click();
  await page.getByRole("button", { name: "Confirm Log Out" }).click();
  await expect(
    page.getByRole("button", { name: "Continue with Email" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continue with Email" }).click();
  await page
    .getByRole("textbox", { name: "Email", exact: true })
    .fill("blair@example.edu");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await finishPreferences(page);
  await openFenwick(page);
  await expect(
    page.getByRole("button", { name: "Save to favorites" }),
  ).toBeVisible();
});

test("invalid credentials and backend outages are recoverable", async ({
  page,
}) => {
  await skipIntro(page);
  await page.getByRole("button", { name: "Continue with Email" }).click();
  await page
    .getByRole("textbox", { name: "Email", exact: true })
    .fill("alex@example.edu");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(
    page.getByText("We couldn’t sign you in. Check your email and password."),
  ).toBeVisible();
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await finishPreferences(page);
  const pattern = "**/api/v1/locations?**";
  await page.route(pattern, (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "DATABASE_UNAVAILABLE",
          message: "Data is temporarily unavailable. Please retry.",
        },
      },
    }),
  );
  await page.getByRole("tab", { name: "Explore" }).click();
  await expect(
    page.getByText("Data is temporarily unavailable. Please retry."),
  ).toBeVisible();
  await page.unroute(pattern);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(/study spaces · Seed data/)).toBeVisible();
});
