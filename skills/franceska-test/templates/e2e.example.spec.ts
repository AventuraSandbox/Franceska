import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// One spec file per flow. Select by role and label, never by CSS class.
test.describe('F01 user creates a habit and checks in', () => {
  test('F01-H1 happy path', async ({ page }) => {
    const problems: string[] = [];
    page.on('console', (m) => m.type() === 'error' && problems.push(m.text()));
    page.on('response', (r) => r.status() >= 500 && problems.push(`${r.status()} ${r.url()}`));

    await page.goto('/habits/new');
    await page.getByLabel('Habit name').fill('Evening walk');
    await page.getByRole('button', { name: 'Save habit' }).click();
    await page.getByRole('button', { name: 'Check in' }).click();
    await expect(page.getByText('Streak: 1')).toBeVisible();

    const scan = await new AxeBuilder({ page }).analyze();
    expect(scan.violations).toEqual([]);
    expect(problems).toEqual([]);
  });

  test('F01-E1 double click on check-in counts once', async ({ page }) => {
    await page.goto('/habits/demo');
    await page.getByRole('button', { name: 'Check in' }).dblclick();
    await expect(page.getByText('Streak: 1')).toBeVisible();
  });
});
