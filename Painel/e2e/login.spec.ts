import { expect, test } from "@playwright/test";

test("login via credenciais de ambiente", async ({ page }) => {
  const email = process.env.E2E_LOGIN_EMAIL;
  const password = process.env.E2E_LOGIN_PASSWORD;

  test.skip(!email || !password, "Defina E2E_LOGIN_EMAIL e E2E_LOGIN_PASSWORD para validar login real.");

  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/senha/i).fill(password);
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page).toHaveURL(/\/analise-vendas/);
  await expect(page.getByRole("heading", { name: "Vendas", exact: true })).toBeVisible();
});
