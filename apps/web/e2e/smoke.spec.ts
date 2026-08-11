import { expect, test, type Page } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

function captureClientErrors(page: Page) {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test("landing page renders cleanly at desktop and mobile sizes", async ({ page }) => {
  const clientErrors = captureClientErrors(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Train smarter/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Start your journey" }).first()).toBeVisible();
  await page.screenshot({ path: "test-results/landing-desktop.png", fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: /Train smarter/i })).toBeVisible();
  await expect(page.getByText("Built for mobile")).toBeVisible();
  await page.screenshot({ path: "test-results/landing-mobile.png", fullPage: true });

  expect(clientErrors).toEqual([]);
});

test("an onboarded athlete can open the responsive command center", async ({ page }) => {
  const clientErrors = captureClientErrors(page);
  const email = `visual-${Date.now()}@example.com`;
  const registration = await page.request.post(`${API_URL}/auth/register`, {
    data: {
      full_name: "Aarav Mehta",
      email,
      password: "StrongPass123",
      confirm_password: "StrongPass123",
      accept_terms: true,
    },
  });
  expect(registration.status()).toBe(201);

  const steps = [
    { step: 1, data: { full_name: "Aarav Mehta", date_of_birth: "1998-04-12", height_cm: 178, weight_kg: 72.5, gender: "male", unit_system: "metric", country: "India", timezone: "Asia/Kolkata" } },
    { step: 2, data: { water_target_ml: 3000, sleep_hours: 7.5, activity_level: "moderately_active" } },
    { step: 3, data: { experience_level: "intermediate" } },
    { step: 4, data: { training_type: "bodybuilding" } },
    { step: 5, data: { primary_goal: "aesthetic_physique" } },
    { step: 6, data: { equipment: ["full_gym"] } },
    { step: 7, data: { days_per_week: 5, preferred_weekdays: [0, 1, 2, 4, 5], session_minutes: 60, preferred_time: "evening" } },
    { step: 8, data: { waist_cm: 80, chest_cm: 98 } },
    { step: 9, data: { skip_scan: true, cv_consent: false } },
  ];

  for (const body of steps) {
    const response = await page.request.put(`${API_URL}/onboarding`, { data: body });
    expect(response.ok()).toBeTruthy();
  }

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: /Aarav/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Next workout" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Start workout/i })).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard-desktop.png", fullPage: true });

  const programResponse = await page.request.get(`${API_URL}/programs/active`);
  expect(programResponse.ok()).toBeTruthy();
  const program = await programResponse.json();
  const sessionResponse = await page.request.post(`${API_URL}/workouts`, {
    data: { program_day_id: program.program.days[0].id },
  });
  expect(sessionResponse.status()).toBe(201);
  const { session_id: sessionId } = await sessionResponse.json();
  await page.goto(`/workouts/session/${sessionId}`);
  await expect(page.getByRole("heading", { name: "Push Day" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save set 1" }).first()).toBeVisible();

  await page.goto("/workouts");
  await page.getByRole("button", { name: "Add workout" }).first().click();
  await page.getByLabel("Workout name").fill("Browser Test Day");
  await page.getByLabel("Focus areas").fill("Grip, Mobility");
  await page.locator("form").getByRole("button", { name: "Add workout" }).click();
  const customDay = page.locator(".day-card").filter({ hasText: "Browser Test Day" });
  await expect(customDay).toBeVisible();
  await customDay.getByRole("button", { name: "Manage day" }).click();
  await expect(page.getByRole("heading", { name: "Browser Test Day" })).toBeVisible();
  await page.getByRole("button", { name: "Add exercise" }).click();
  await page.getByRole("textbox", { name: "Search exercises to add" }).fill("Farmer Carry");
  await page.getByRole("button", { name: /Farmer Carry/ }).click();
  await expect(page.getByRole("heading", { name: "Farmer Carry" })).toBeVisible();
  await page.screenshot({ path: "test-results/workout-day-editor-desktop.png", fullPage: true });

  await page.goto("/workouts");
  const removableDay = page.locator(".day-card").filter({ hasText: "Browser Test Day" });
  page.once("dialog", (dialog) => dialog.accept());
  await removableDay.getByRole("button", { name: "Delete Browser Test Day" }).click();
  await expect(removableDay).toHaveCount(0);

  await page.getByRole("button", { name: "Change plan" }).click();
  await expect(page.getByRole("heading", { name: "Change workout plan" })).toBeVisible();
  await page.screenshot({ path: "test-results/plan-chooser-desktop.png", fullPage: true });
  await page.getByLabel("Workout plan").selectOption({ label: "Full Body 2-Day" });
  await page.getByRole("button", { name: "Use this plan" }).click();
  await expect(page.getByRole("heading", { name: "Full Body 2-Day" })).toBeVisible();

  await page.goto("/exercises");
  await expect(page.getByRole("heading", { name: "Exercise library" })).toBeVisible();
  await expect(page.getByText("151").first()).toBeVisible();
  await page.getByRole("textbox", { name: "Search exercise catalogue" }).fill("Barbell Bench Press");
  await expect(page.getByRole("heading", { name: "Barbell Bench Press", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Full exercise profile" }).first().click();
  await expect(page.getByRole("heading", { name: "Barbell Bench Press", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Program prescriptions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Smart substitutions" })).toBeVisible();
  await page.screenshot({ path: "test-results/exercise-detail-desktop.png", fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Next workout" })).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard-mobile.png", fullPage: true });

  expect(clientErrors).toEqual([]);
});
