const statusMessage = document.querySelector("#status");
const productForm = document.querySelector("#product-form");
const recipeForm = document.querySelector("#recipe-form");
const matchForm = document.querySelector("#match-form");
let products = [];
let recipes = [];
let editingId = null;
let matchVersion = 0;

async function api(path, method = "GET", body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Не удалось связаться с сервером. Проверьте, что приложение запущено.");
  }
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Не удалось выполнить запрос (HTTP ${response.status}).`,
    );
  }
  return response.status === 204 ? null : response.json();
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function checkedIds(container) {
  return [...document.querySelectorAll(`${container} input:checked`)].map((input) =>
    Number(input.value),
  );
}

function renderChoices(containerId, selectedIds = []) {
  const container = document.querySelector(containerId);
  container.replaceChildren();
  if (!products.length) {
    container.append(
      element("p", "Пока нет продуктов. Добавьте первый продукт в справочник.", "hint"),
    );
  }
  for (const product of products) {
    const label = element("label");
    const checkbox = element("input");
    checkbox.type = "checkbox";
    checkbox.value = product.id;
    checkbox.checked = selectedIds.includes(product.id);
    label.append(checkbox, element("span", product.name));
    container.append(label);
  }
}

function clearMatches() {
  matchVersion += 1;
  document
    .querySelector("#match-results")
    .replaceChildren(element("p", "Выберите продукты и нажмите «Подобрать рецепты».", "hint"));
}

function recipeCard(recipe) {
  const article = element("article", undefined, "recipe-card");
  article.append(element("h3", recipe.name));
  const details = element("details");
  details.append(element("summary", "Инструкция и состав"));
  details.append(element("p", recipe.instructions, "instructions"));
  const ingredients = element("ul");
  for (const product of recipe.ingredients) ingredients.append(element("li", product.name));
  details.append(ingredients);
  article.append(details);
  return article;
}

function resetEditor() {
  editingId = null;
  recipeForm.reset();
  renderChoices("#recipe-products");
  document.querySelector("#editor-title").textContent = "Новый рецепт";
  document.querySelector("#save-recipe").textContent = "Создать рецепт";
  document.querySelector("#cancel-edit").hidden = true;
}

function renderRecipes() {
  const container = document.querySelector("#recipe-list");
  container.replaceChildren();
  if (!recipes.length)
    container.append(element("p", "Рецептов пока нет. Создайте первый рецепт.", "hint"));
  for (const recipe of recipes) {
    const card = recipeCard(recipe);
    const actions = element("div", undefined, "actions");
    const edit = element("button", "Редактировать");
    edit.type = "button";
    edit.addEventListener("click", () => {
      editingId = recipe.id;
      document.querySelector("#recipe-name").value = recipe.name;
      document.querySelector("#recipe-instructions").value = recipe.instructions;
      renderChoices(
        "#recipe-products",
        recipe.ingredients.map((item) => item.id),
      );
      document.querySelector("#editor-title").textContent = "Редактирование рецепта";
      document.querySelector("#save-recipe").textContent = "Сохранить изменения";
      document.querySelector("#cancel-edit").hidden = false;
      document.querySelector("#recipe-name").focus();
    });
    const remove = element("button", "Удалить", "danger");
    remove.type = "button";
    remove.addEventListener("click", () =>
      runAction(remove, async () => {
        if (!window.confirm(`Удалить рецепт «${recipe.name}»?`)) return;
        await api(`/api/recipes/${recipe.id}`, "DELETE");
        if (editingId === recipe.id) resetEditor();
        await loadRecipes();
        clearMatches();
      }),
    );
    actions.append(edit, remove);
    card.append(actions);
    container.append(card);
  }
}

async function loadRecipes() {
  recipes = await api("/api/recipes");
  renderRecipes();
}

async function runAction(button, action) {
  statusMessage.textContent = "";
  button.disabled = true;
  try {
    await action();
  } catch (error) {
    statusMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function refreshAddedProduct() {
  try {
    products = await api("/api/products");
    renderChoices("#available-products", checkedIds("#available-products"));
    renderChoices("#recipe-products", checkedIds("#recipe-products"));
  } catch {
    const retry = element("button", "Обновить список");
    retry.type = "button";
    retry.addEventListener("click", () => runAction(retry, refreshAddedProduct));
    statusMessage.replaceChildren("Продукт добавлен. ", retry);
  }
}

productForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(productForm.querySelector("button"), async () => {
    await api("/api/products", "POST", { name: document.querySelector("#product-name").value });
    productForm.reset();
    await refreshAddedProduct();
  });
});

recipeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(document.querySelector("#save-recipe"), async () => {
    const body = {
      name: document.querySelector("#recipe-name").value,
      instructions: document.querySelector("#recipe-instructions").value,
      ingredient_ids: checkedIds("#recipe-products"),
    };
    const list = document.querySelector("#recipe-list");
    recipeForm.inert = true;
    list.inert = true;
    try {
      await api(
        editingId === null ? "/api/recipes" : `/api/recipes/${editingId}`,
        editingId === null ? "POST" : "PUT",
        body,
      );
      resetEditor();
      await loadRecipes();
      clearMatches();
    } finally {
      recipeForm.inert = false;
      list.inert = false;
    }
  });
});

matchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(matchForm.querySelector("button"), async () => {
    const version = ++matchVersion;
    const results = await api("/api/matches", "POST", {
      product_ids: checkedIds("#available-products"),
    });
    if (version !== matchVersion) return;
    const container = document.querySelector("#match-results");
    container.replaceChildren();
    if (!results.length)
      container.append(
        element("p", "Подходящих рецептов нет. Попробуйте выбрать другие продукты.", "hint"),
      );
    for (const result of results) {
      const card = recipeCard(result);
      const percentage = result.percentage.toLocaleString("ru-RU", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });
      card.prepend(element("p", `Совпадение: ${percentage}%`, "percentage"));
      card.append(
        element("p", "Есть: " + result.available_ingredients.map((item) => item.name).join(", ")),
      );
      card.append(
        element(
          "p",
          result.missing_ingredients.length
            ? `Не хватает: ${result.missing_ingredients.map((item) => item.name).join(", ")}`
            : "Все ингредиенты есть",
        ),
      );
      container.append(card);
    }
  });
});

document.querySelector("#available-products").addEventListener("change", clearMatches);
document.querySelector("#cancel-edit").addEventListener("click", resetEditor);

async function initialize() {
  try {
    [products, recipes] = await Promise.all([api("/api/products"), api("/api/recipes")]);
    renderChoices("#available-products");
    renderChoices("#recipe-products");
    renderRecipes();
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

initialize();
