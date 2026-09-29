import { test as setup, expect } from '@playwright/test';
import { STORAGE_STATE } from '../playwright.config';

setup('authenticate', async ({ page }) => {
  const email = process.env.RHOMBUS_EMAIL;
  const password = process.env.RHOMBUS_PASSWORD;
  if (!email || !password) {
    throw new Error('RHOMBUS_EMAIL and RHOMBUS_PASSWORD must be set in ../.env');
  }

  // TODO: confirm the login path from the real app.
  await page.goto('/');

  // TODO: replace placeholder selectors with the real login form selectors.
  await page.locator('TODO_EMAIL_INPUT_SELECTOR').fill(email);
  await page.locator('TODO_PASSWORD_INPUT_SELECTOR').fill(password);
  await page.locator('TODO_SUBMIT_BUTTON_SELECTOR').click();

  // TODO: assert on something only visible when logged in (e.g. the projects list or user menu).
  await expect(page.locator('TODO_LOGGED_IN_INDICATOR_SELECTOR')).toBeVisible();

  await page.context().storageState({ path: STORAGE_STATE });
});
