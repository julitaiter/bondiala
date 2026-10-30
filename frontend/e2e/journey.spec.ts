import { test, expect, type Page } from "@playwright/test";
import { officialTestRoute } from "./catalog";
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}
test("registro, viaje, progreso, perfil, ranking y temas", async ({
  page,
}, testInfo) => {
  const suffix = `${Date.now()}${testInfo.project.name}`;
  const password = "Mi-viaje-seguro-2026!";
  await page.goto("/registro");
  await page
    .getByLabel("Nombre de usuario", { exact: true })
    .fill(`viajero${suffix}`.slice(0, 30));
  await page.getByLabel("¿Cómo te llamamos?").fill("Viajero de prueba");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`viajero${suffix}@example.test`);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Crear mi colección" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(
    page.getByRole("heading", { name: /Qué vas a bondiar/ }),
  ).toBeVisible();
  const officialRoute = await officialTestRoute(page.request);
  await page.goto("/lineas");
  await expect(
    page.getByRole("heading", { name: "Explorá tu próxima línea" }),
  ).toBeVisible();
  await page.getByLabel("Buscar línea", { exact: true }).fill(officialRoute.linea_numero);
  await page.locator(`.line-card[href="/lineas/${officialRoute.linea}"]`).click();
  await expect(page).toHaveURL(/\/lineas\/\d+$/);
  await expect(
    page.getByRole("heading", { level: 1, name: /^Línea \d+$/ }),
  ).toBeVisible();
  await page
    .locator("main")
    .getByRole("link", { name: "Registrar viaje", exact: true })
    .last()
    .click();
  await page.getByRole("combobox", { name: "Ramal", exact: true }).selectOption(String(officialRoute.ramal));
  await page.getByRole("combobox", { name: "Sentido", exact: true }).selectOption(String(officialRoute.id));
  await page
    .getByRole("combobox", { name: "¿Dónde subiste?", exact: true })
    .selectOption({ index: 1 });
  await page
    .getByRole("combobox", { name: "¿Dónde bajaste?", exact: true })
    .selectOption({ index: 2 });
  await page.getByRole("button", { name: "Revisar viaje" }).click();
  await page.getByRole("button", { name: "Confirmar y guardar" }).click();
  await expect(
    page.getByRole("heading", { name: /Ya es parte de tu colección.|¡Línea completada!/ }),
  ).toBeVisible();
  await expect(page.locator(".reward-grid")).toContainText("3");
  await noOverflow(page);
  await page.goto("/perfil");
  await expect(
    page.getByRole("heading", { name: "Viajero de prueba", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".metric").first()).toContainText("3");
  await page.goto("/ranking");
  await page.getByRole("tab", { name: "Esta semana" }).click();
  await expect(page.getByRole("tabpanel")).toContainText("DEL LUNES A HOY");
  await page.getByRole("tab", { name: "Amigos", exact: true }).click();
  await expect(page.getByRole("tabpanel")).toContainText("Viajero de prueba");
  await page.goto("/configuracion");
  for (const [label, theme] of [
    ["Oscuro", "dark"],
    ["Claro", "light"],
    ["Sistema", "light"],
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    await noOverflow(page);
  }
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByRole("status")).toContainText("Cambios guardados");
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/login");
  await page
    .getByLabel("Email o usuario", { exact: true })
    .fill(`viajero${suffix}@example.test`);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Iniciar sesión", exact: true })
    .click();
  await expect(page).toHaveURL(/dashboard/);
});

test("el catálogo CSV permite explorar líneas sin trazado ni paradas", async ({
  page,
}) => {
  const catalog = await page.request
    .get("/api/v1/lineas/?search=2")
    .then((r) => r.json());
  const line = catalog.results.find(
    (entry: { numero: string }) => entry.numero === "2",
  );
  expect(line).toBeDefined();
  expect(line.colores.color_principal).toBe("#BE1F1C");
  const routes = await page.request
    .get(`/api/v1/lineas/${line.id}/recorridos/`)
    .then((r) => r.json());
  expect(routes.length).toBeGreaterThan(0);
  expect(routes[0].geometria).toBeNull();
  await page.goto(`/lineas/${line.id}`);
  await expect(
    page.getByRole("heading", { name: "Trazado todavía no disponible" }),
  ).toBeVisible();
  await noOverflow(page);
  await page.goto(`/recorridos/${routes[0].id}`);
  await expect(
    page.getByRole("heading", { name: "Paradas aún no disponibles" }),
  ).toBeVisible();
  await expect(page.locator(".map-canvas")).toHaveCount(0);
  await expect(page.locator("main").getByRole("link", { name: "Registrar viaje", exact: true })).toHaveCount(0);
  await noOverflow(page);
});

test("el alta bloquea paradas ilustrativas incluso con disponibilidad obsoleta", async ({ page }) => {
  const route = await officialTestRoute(page.request);
  const illustrative = {
    ...route,
    // Respuesta simulada: no se cambia el origen ni el contenido de la base real.
    puede_registrar_viaje: true,
    paradas: route.paradas.map((item) => ({
      ...item,
      parada: { ...item.parada, is_official: false },
    })),
  };
  await page.route("**/api/v1/me/", (request) => request.fulfill({
    json: { user: {
      id: 1, nickname: "Prueba de restricción", username: "restriccion",
      avatar: "", theme: "system", nivel: { numero: 1, nombre: "Pasajero" },
    } },
  }));
  await page.route(`**/api/v1/lineas/${route.linea}/recorridos/`,
    (request) => request.fulfill({ json: [illustrative] }));
  let posted = false;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/viajes/")) posted = true;
  });
  await page.goto(`/viajes/nuevo?linea=${route.linea}&recorrido=${route.id}`);
  await expect(page.getByText(/Paradas aún no disponibles/)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "¿Dónde subiste?", exact: true })).toBeDisabled();
  await expect(page.getByRole("combobox", { name: "¿Dónde bajaste?", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Revisar viaje" })).toBeDisabled();
  expect(posted).toBe(false);
  await noOverflow(page);
});
