import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("подбор показывает состав при частичном и полном совпадении", async ({ page }) => {
  const choices = page.locator("#available-products");
  const submit = page.getByRole("button", { name: "Подобрать рецепты" });
  await choices.getByLabel("Молоко").check();
  await submit.click();
  const omelet = page.locator("#match-results article").filter({ hasText: "Омлет" });
  await expect(omelet).toContainText("25,0%");
  await expect(omelet).toContainText("Не хватает:");
  await expect(omelet).toContainText("Яйцо");
  for (const name of ["Яйцо", "Соль", "Масло растительное"])
    await choices.getByLabel(name, { exact: true }).check();
  await submit.click();
  await expect(omelet).toContainText("100,0%");
  await expect(omelet).toContainText("Все ингредиенты есть");
  await expect(omelet).not.toContainText("Не хватает:");
});

test("запоздавший ответ не возвращает старый подбор", async ({ page }) => {
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/matches", async (route) => {
    await pending;
    await route.continue();
  });
  const milk = page.locator("#available-products").getByLabel("Молоко");
  await milk.check();
  const started = page.waitForRequest("**/api/matches");
  await page.getByText("Подобрать рецепты", { exact: true }).click();
  await started;
  await milk.uncheck();
  release();
  await expect(page.locator("#match-form button")).toBeEnabled();
  await expect(page.locator("#match-results article")).toHaveCount(0);
});

test("на время сохранения редактор закрыт для изменений", async ({ page }) => {
  await page.getByRole("button", { name: "Редактировать" }).first().click();
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/recipes/*", async (route) => {
    await pending;
    await route.continue();
  });
  const started = page.waitForRequest((r) => r.method() === "PUT");
  await page.getByText("Сохранить изменения", { exact: true }).click();
  await started;
  await expect(page.locator("#recipe-form")).toHaveJSProperty("inert", true);
  await expect(page.locator("#recipe-list")).toHaveJSProperty("inert", true);
  release();
  await expect(page.locator("#recipe-form")).toHaveJSProperty("inert", false);
});

test("повтор загрузки списка не добавляет продукт дважды", async ({ page }) => {
  await expect(page.locator("#available-products input").first()).toBeVisible();
  let saves = 0,
    reads = 0;
  await page.route("**/api/products", async (route) => {
    if (route.request().method() === "POST") saves++;
    else if (++reads === 1) return route.abort();
    await route.continue();
  });
  await page.getByLabel("Новый продукт").fill("Кефир");
  await page.getByRole("button", { name: "Добавить", exact: true }).click();
  await page.getByRole("button", { name: "Обновить список" }).click();
  await expect(page.locator("#available-products").getByLabel("Кефир")).toBeVisible();
  expect(saves).toBe(1);
});

test("ошибка 503 показана понятным текстом", async ({ page }) => {
  await page.route("**/api/matches", (route) =>
    route.fulfill({ status: 503, contentType: "text/plain", body: "Unavailable" }),
  );
  await page.getByRole("button", { name: "Подобрать рецепты" }).click();
  await expect(page.getByRole("status")).toHaveText("Не удалось выполнить запрос (HTTP 503).");
});
