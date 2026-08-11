import { expect, test, type Page } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

test.use({ timezoneId: "Asia/Kolkata" });

function captureClientErrors(page: Page) {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test("completed workout history powers the responsive strength intelligence report", async ({ page }) => {
  test.setTimeout(90_000);
  const clientErrors = captureClientErrors(page);
  const email = `strength-e2e-${Date.now()}@example.com`;
  const registration = await page.request.post(`${API_URL}/auth/register`, {
    data: {
      full_name: "Strength Test Athlete",
      email,
      password: "StrongPass123",
      confirm_password: "StrongPass123",
      accept_terms: true,
    },
  });
  expect(registration.status()).toBe(201);
  const steps = [
    { step: 1, data: { full_name: "Strength Test Athlete", date_of_birth: "1998-04-12", height_cm: 178, weight_kg: 75, gender: "male", unit_system: "metric", country: "India", timezone: "Asia/Kolkata" } },
    { step: 2, data: { water_target_ml: 3000, sleep_hours: 7.5, activity_level: "moderately_active" } },
    { step: 3, data: { experience_level: "intermediate" } },
    { step: 4, data: { training_type: "bodybuilding" } },
    { step: 5, data: { primary_goal: "strength" } },
    { step: 6, data: { equipment: ["full_gym"] } },
    { step: 7, data: { days_per_week: 3, preferred_weekdays: [0, 2, 4], session_minutes: 60, preferred_time: "evening" } },
    { step: 8, data: { waist_cm: 80, chest_cm: 100 } },
    { step: 9, data: { skip_scan: true, cv_consent: false } },
  ];
  for (const body of steps) {
    expect((await page.request.put(`${API_URL}/onboarding`, { data: body })).ok()).toBeTruthy();
  }
  const program = await (await page.request.get(`${API_URL}/programs/active`)).json();
  const day = program.program.days[0];
  const prescription = day.exercises[0];
  for (let workout = 0; workout < 3; workout += 1) {
    const started = await page.request.post(`${API_URL}/workouts`, { data: { program_day_id: day.id } });
    expect(started.status()).toBe(201);
    const { session_id: sessionId } = await started.json();
    for (let setIndex = 1; setIndex <= 3; setIndex += 1) {
      const logged = await page.request.post(`${API_URL}/workouts/${sessionId}/sets`, {
        data: {
          prescribed_exercise_id: prescription.id,
          set_index: setIndex,
          client_operation_id: `${Date.now()}-${workout}-${setIndex}`,
          load_kg: 60 + workout * 2.5,
          reps: 8 + workout,
          rir: 2,
          completed: true,
        },
      });
      expect(logged.status()).toBe(201);
    }
    expect((await page.request.post(`${API_URL}/workouts/${sessionId}/complete`, { data: { session_rpe: 8, rating: "good" } })).ok()).toBeTruthy();
  }

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Progress & Strength Intelligence", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recorded Strength Profile", exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Body strength map", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("Not Enough Data", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: /Chest:/ }).first().click();
  await expect(page.getByRole("dialog", { name: "Chest" })).toBeVisible();
  await page.getByRole("button", { name: "Close muscle detail" }).click();
  await page.getByRole("button", { name: "Generate Strength Report" }).click();
  await expect(page.getByRole("dialog", { name: "Strength Report" })).toBeVisible();
  await page.getByRole("button", { name: "Close strength report" }).click();
  await page.screenshot({ path: "test-results/strength-progress-desktop.png", fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Progress & Strength Intelligence", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recorded Strength Profile", exact: true })).toBeVisible({ timeout: 30_000 });
  const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(hasHorizontalOverflow).toBe(false);
  await page.screenshot({ path: "test-results/strength-progress-mobile.png", fullPage: true });
  expect(clientErrors).toEqual([]);
});
