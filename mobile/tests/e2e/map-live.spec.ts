import { expect, test } from "@playwright/test";

test("MapLibre renders live style and tiles with selectable building markers", async ({
  page,
}) => {
  const mapResponses: number[] = [];
  const mapErrors: number[] = [];
  page.on("response", (response) => {
    if (response.url().startsWith("https://tiles.openfreemap.org/")) {
      mapResponses.push(response.status());
      if (response.status() >= 400) mapErrors.push(response.status());
    }
  });
  await page.goto("/");
  const skip = page.getByRole("button", { name: "Skip", exact: true });
  if (await skip.isVisible()) await skip.click();
  await page.getByRole("button", { name: "Continue with Email" }).click();
  await page
    .getByRole("textbox", { name: "Email", exact: true })
    .fill("alex@example.edu");
  await page.getByLabel("Password", { exact: true }).fill("StudySpot123!");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  const next = page.getByRole("button", { name: "Next", exact: true });
  const home = page.getByText("Your next great idea needs a good spot.");
  await expect(next.or(home)).toBeVisible();
  if (await next.isVisible()) {
    for (let step = 0; step < 3; step++) await next.click();
    await page.getByRole("button", { name: "Finish", exact: true }).click();
  }
  await expect(home).toBeVisible();
  await page.getByRole("tab", { name: "Map" }).click();
  await expect(page.getByLabel("Interactive campus map")).toBeVisible();
  await expect(page.getByText("Loading campus map…")).toHaveCount(0, {
    timeout: 30000,
  });
  await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
  await expect(
    page.getByText(/Map unavailable|Map setup required/),
  ).toHaveCount(0);
  await expect
    .poll(
      () =>
        mapResponses.filter((status) => status === 200 || status === 304)
          .length,
    )
    .toBeGreaterThan(1);
  expect(
    mapErrors,
    `Tile provider returned HTTP errors: ${mapErrors.join(", ")}`,
  ).toEqual([]);
  await page
    .getByRole("button", { name: /Fenwick Library.*study zones/ })
    .click();
  await expect(
    page.getByRole("button", { name: "Floor 4", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/live-map.png", fullPage: true });
});
