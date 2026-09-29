/**
 * End-to-end journey: S3 source -> AI-built cleaning pipeline -> GCS destination, scheduled.
 *
 * WAITING RULE: never use page.waitForTimeout() (or any fixed sleep) in this suite.
 * Every wait must be a web-first assertion that retries until it passes, e.g.
 *   await expect(locator).toBeVisible();
 *   await expect(locator).toHaveText(/success/i);
 * or, for state that isn't a single locator, expect.poll():
 *   await expect.poll(async () => readRunStatus(page), { timeout: RUN_TIMEOUT }).toBe('Success');
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const AI_BUILDER_PROMPT = fs
  .readFileSync(path.join(__dirname, '..', 'fixtures', 'ai-builder-prompt.txt'), 'utf-8')
  .trim();

// Pipeline runs are slow; give run-related assertions more room than the default expect timeout.
const RUN_TIMEOUT = 8 * 60 * 1000;

test.describe('Rhombus AI pipeline journey (S3 -> clean -> GCS, scheduled)', () => {
  test('build, schedule and run the pipeline', async ({ page }) => {
    await test.step('1. Open the project', async () => {
      // TODO: navigate to the project (path / project name selector).
      await page.goto('/');
      // Assert: the project canvas/editor is loaded, e.g. the project title is visible.
      await expect(page.locator('TODO_PROJECT_TITLE_SELECTOR')).toBeVisible();
    });

    await test.step('2. Configure the S3 data input', async () => {
      // TODO: selectors for adding an S3 input node and filling bucket / key / region.
      //   bucket: process.env.S3_BUCKET, key: process.env.S3_INPUT_KEY, region: process.env.AWS_REGION
      // Assert (real outcome): the input node shows a connected/success state and a data preview
      // with the expected columns (order_id, customer_name, email, ...).
      await expect(page.locator('TODO_S3_NODE_STATUS_SELECTOR')).toBeVisible();
    });

    await test.step('3. Build the cleaning pipeline through the AI builder prompt', async () => {
      expect(AI_BUILDER_PROMPT, 'fixtures/ai-builder-prompt.txt must contain the real prompt').not.toMatch(/^TODO/);
      // TODO: selectors for the AI builder input and submit button.
      await page.locator('TODO_AI_BUILDER_INPUT_SELECTOR').fill(AI_BUILDER_PROMPT);
      await page.locator('TODO_AI_BUILDER_SUBMIT_SELECTOR').click();
      // Assert (real outcome): the builder produced transformation nodes on the canvas and
      // they are connected to the input node (e.g. node count > 0, no error badge).
      await expect(page.locator('TODO_TRANSFORM_NODE_SELECTOR').first()).toBeVisible({ timeout: RUN_TIMEOUT });
    });

    await test.step('4. Set the GCS destination', async () => {
      // TODO: selectors for adding a GCS output node; bucket: process.env.GCS_BUCKET,
      //   path/prefix: process.env.GCS_OUTPUT_PREFIX.
      // Assert (real outcome): the destination node is saved and shows as configured/valid.
      await expect(page.locator('TODO_GCS_NODE_STATUS_SELECTOR')).toBeVisible();
    });

    await test.step('5. Configure the schedule', async () => {
      // TODO: selectors for the schedule dialog (frequency, time, timezone) and save.
      // Assert (real outcome): the schedule shows as active with the expected next-run time.
      await expect(page.locator('TODO_SCHEDULE_STATUS_SELECTOR')).toHaveText(/TODO_ACTIVE_TEXT/i);
    });

    await test.step('6. Trigger a run and assert the logs show success', async () => {
      // TODO: selector for the "run now" button and for the run log / status.
      await page.locator('TODO_RUN_NOW_SELECTOR').click();
      // Assert (real outcome): the latest run reaches a success status in the logs.
      // Use expect.poll or a web-first assertion with RUN_TIMEOUT — no fixed sleeps.
      await expect(page.locator('TODO_RUN_STATUS_SELECTOR')).toHaveText(/TODO_SUCCESS_TEXT/i, {
        timeout: RUN_TIMEOUT,
      });
      // Follow-up (outside the UI): verify the file landed in GCS with data-validation/validate.py.
    });
  });
});
