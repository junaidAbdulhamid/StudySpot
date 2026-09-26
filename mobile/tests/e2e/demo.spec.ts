import { test, expect, Page } from "@playwright/test";
const api = "http://127.0.0.1:8002/api/v1";
test.beforeEach(async ({ request }) => {
  const response = await request.get(`${api}/users/development`);
  expect(response.ok()).toBeTruthy();
  const { data: user } = await response.json();
  const favorites = await (
    await request.get(`${api}/users/${user.id}/favorites?page_size=100`)
  ).json();
  for (const favorite of favorites.items)
    await request.delete(
      `${api}/users/${user.id}/favorites/${favorite.location_id}`,
    );
  for (const id of ["zone-1", "zone-6"])
    await request.post(`${api}/users/${user.id}/favorites/${id}`);
  const saved = await request.patch(`${api}/users/${user.id}/preferences`, {
    data: {
      noise_preference: "quiet",
      study_style: "solo",
      max_walking_minutes: 10,
      study_duration_hours: 1,
      preferred_amenities: ["outlets"],
    },
  });
  expect(saved.ok()).toBeTruthy();
});

async function enter(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Skip", exact: true }).click();
  await page.getByRole("button", { name: "Continue with Mason" }).click();
  for (let i = 0; i < 3; i++)
    await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await expect(
    page.getByText("Your next great idea needs a good spot."),
  ).toBeVisible();
}
test("complete demo journey", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByText("Find your perfect place to study."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByText("Know before you go.")).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Get Started", exact: true }).click();
  await page.getByRole("button", { name: "Continue with Mason" }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await page.screenshot({ path: "test-results/home.png", fullPage: true });
  await page.getByRole("tab", { name: "Explore" }).click();
  await page.getByRole("textbox").fill("Fenwick");
  await expect(page.getByText("4 study spaces · Seed data")).toBeVisible();
  await page
    .getByRole("button", { name: "View Fenwick Library, Floor 4", exact: true })
    .click();
  await page
    .getByRole("button", { name: "View Predictions", exact: true })
    .click();
  await expect(page.getByText("Your next few hours")).toBeVisible();
  await page.getByRole("button", { name: "Live", exact: true }).click();
  await expect(page.getByText("Confidence", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Check In / Report Crowd" }).click();
  await page
    .getByRole("button", { name: "Check In", exact: true })
    .last()
    .click();
  await expect(page.getByText("Checked in", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Report Crowd", exact: true }).click();
  await page
    .getByRole("button", { name: "Lots of seats", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Submit Crowd Report", exact: true })
    .click();
  await expect(page.getByText("You made a difference.")).toBeVisible();
  await page.getByRole("button", { name: "Return Home" }).click();
  await page
    .getByRole("button", { name: "Find Me a Spot", exact: true })
    .click();
  await page.getByRole("button", { name: "2 hours", exact: true }).click();
  await page.getByRole("button", { name: "Find My Spot", exact: true }).click();
  await expect(page.getByText("#1 BEST MATCH")).toBeVisible();
  await page
    .getByRole("button", { name: /^View .* Floor/ })
    .first()
    .click();
  const heart = page.getByRole("button", {
    name: /Remove from favorites|Save to favorites/,
  });
  if ((await heart.getAttribute("aria-label")) === "Remove from favorites")
    await heart.click();
  await page.getByRole("button", { name: "Save to favorites" }).click();
  await page.getByRole("button", { name: "Directions", exact: true }).click();
  await page.getByRole("button", { name: "Explore campus map" }).click();
  await page
    .getByRole("button", { name: "Fenwick Library, Floor 4, 28% available" })
    .click();
  await expect(
    page.getByRole("button", { name: "View Fenwick Library, Floor 4" }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/map.png", fullPage: true });
  await page.getByRole("tab", { name: "Alerts" }).click();
  await expect(
    page.getByText("Your quiet corner is clearing up"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear all", exact: true }).click();
  await expect(page.getByText("All quiet for now.")).toBeVisible();
  await page.getByRole("tab", { name: "Profile" }).click();
  await page.getByRole("button", { name: "Favorites", exact: true }).click();
  await expect(page.getByText("Your familiar favorites.")).toBeVisible();
  await page.getByRole("button", { name: "Go back" }).click();
  await page.getByRole("button", { name: "Notification Settings" }).click();
  await page.getByRole("switch").click();
  await page.getByRole("button", { name: "Go back" }).click();
  await page.getByRole("button", { name: "Log Out" }).click();
  await expect(
    page.getByRole("button", { name: "Continue with Mason" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("filters, empty states, persisted favorites, and small-screen layout", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await enter(page);
  await page.getByRole("tab", { name: "Explore" }).click();
  await page.getByRole("button", { name: "Noise ⌄" }).click();
  await page.getByRole("button", { name: "Quiet", exact: true }).click();
  await page.getByRole("button", { name: "Show study spaces" }).click();
  await expect(page.getByText("6 study spaces · Seed data")).toBeVisible();
  await page.getByRole("textbox").fill("not-a-real-building");
  await expect(page.getByText("Let’s widen the search")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText("12 study spaces · Seed data")).toBeVisible();
  await page
    .getByRole("button", { name: "View Fenwick Library, Floor 4", exact: true })
    .click();
  await page.getByRole("button", { name: "Remove from favorites" }).click();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Skip", exact: true }),
  ).toBeVisible();
  await enter(page);
  await page.getByRole("tab", { name: "Explore" }).click();
  await page
    .getByRole("button", { name: "View Fenwick Library, Floor 4", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Save to favorites" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("preference editing, check-out, recents, home search, and settings", async ({
  page,
}) => {
  await enter(page);
  await page.getByRole("textbox").fill("Peterson");
  await page.getByRole("textbox").press("Enter");
  await expect(page.getByText("2 study spaces · Seed data")).toBeVisible();
  await page
    .getByRole("button", { name: "View Peterson Hall, Floor 1", exact: true })
    .click();
  await page.getByRole("button", { name: "Check In", exact: true }).click();
  await page
    .getByRole("button", { name: "Check In", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "Check Out", exact: true }).click();
  await expect(page.getByText("You’re here!", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Return Home" }).click();
  await page.getByRole("button", { name: "Recent", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "View Peterson Hall, Floor 1",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Go back" }).click();
  await page.getByRole("tab", { name: "Profile" }).click();
  await page
    .getByRole("button", { name: "Study Preferences", exact: true })
    .click();
  await page.getByRole("button", { name: "Moderate", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Group", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Whiteboards", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "15 minutes", exact: true }).click();
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await expect(page.getByText("15-minute walking radius")).toBeVisible();
  for (const [name, text] of [
    ["Appearance", "Campus night"],
    ["Privacy", "Your development data."],
    ["About StudySpot", "A better place to focus."],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(page.getByText(text!, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Go back" }).click();
  }
  await page.getByRole("tab", { name: "Home" }).click();
  await page
    .getByRole("button", { name: "Find Me a Spot", exact: true })
    .click();
  for (const name of [
    "Printers",
    "Food nearby",
    "Group rooms",
    "Natural light",
  ])
    await page.getByRole("button", { name, exact: true }).click();
  await page.getByRole("button", { name: "Find My Spot", exact: true }).click();
  await expect(page.getByText("Let’s give you more options")).toBeVisible();
});
