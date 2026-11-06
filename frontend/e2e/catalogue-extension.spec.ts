import { mkdir } from "node:fs/promises";
import { test, expect } from "@playwright/test";
import type { Line, Page, Route } from "../src/lib/types";

test("variantes documentadas y catálogo eBUS en ambos temas", async ({ page }, info) => {
  const variants = [
    ["50", "C"], ["12", "C"], ["151", "B"], ["151", "C"],
    ["151", "D"], ["102", "B"], ["EBUS", "A"], ["42", "C"],
  ];
  const routes = new Map<string, Route[]>();
  let ebus: Line | undefined;
  for (const [code, branch] of variants) {
    if (!routes.has(code)) {
      const result: Page<Line> = await page.request.get(`/api/v1/lineas/?search=${code}`).then((r) => r.json());
      const line = result.results.find((item) => item.numero === code);
      expect(line).toBeDefined();
      if (code === "EBUS") ebus = line;
      routes.set(code, await page.request.get(`/api/v1/lineas/${line!.id}/recorridos/`).then((r) => r.json()));
    }
    const prefix = /^\d+$/.test(code) ? code.padStart(3, "0") : code;
    for (const direction of ["IDA", "VUELTA"]) {
      const route = routes.get(code)!.find((item) => item.external_id === `${prefix}${branch}${direction}`);
      expect(route).toBeDefined();
      expect(route!.geometria?.type).toBe("MultiLineString");
      expect(route!.requiere_rematch).toBe(false);
      expect(route!.paradas.every((stop) => stop.parada.is_official)).toBe(true);
      expect(route!.paradas.map((stop) => stop.orden)).toEqual(route!.paradas.map((_, index) => index + 1));
    }
  }
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const directory = "test-results/catalogue-extension";
  await mkdir(directory, { recursive: true });
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    await page.goto("/lineas");
    await page.getByLabel("Buscar línea", { exact: true }).fill("ebus");
    const card = page.locator(`.line-card[href="/lineas/${ebus!.id}"]`);
    await expect(card).toBeVisible();
    const badge = card.getByLabel("Línea EBUS");
    await expect(badge).toHaveText("EBUS");
    await page.evaluate(() => document.fonts.ready);
    expect(await badge.locator("b").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    await card.click();
    await expect(page.getByRole("heading", { name: "Línea EBUS", exact: true })).toBeVisible();
    await expect(page.locator(".map-canvas")).toHaveAttribute("aria-busy", "false");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `${directory}/${info.project.name}-ebus-${theme}.png`, fullPage: true, animations: "disabled" });
  }
  expect(errors).toEqual([]);
});

test("viaje real en eBUS conserva código y actualiza progreso", async ({ page }, info) => {
  const catalogue: Page<Line> = await page.request.get("/api/v1/lineas/?search=ebus").then((r) => r.json());
  const line = catalogue.results.find((item) => item.numero === "EBUS");
  expect(line).toBeDefined();
  const routes: Route[] = await page.request.get(`/api/v1/lineas/${line!.id}/recorridos/`).then((r) => r.json());
  const route = routes.find((item) => item.sentido === "IDA");
  expect(route?.puede_registrar_viaje).toBe(true);
  expect(route!.paradas.length).toBeGreaterThanOrEqual(3);
  const suffix = `${Date.now()}${info.project.name}`;
  const csrf = await page.request.get("/api/v1/auth/csrf/").then((r) => r.json());
  const signup = await page.request.post("/api/v1/auth/registro/", {
    headers: { "X-CSRFToken": csrf.csrfToken },
    data: {
      username: `ebus${suffix}`.slice(0, 30), nickname: "Viajero eBUS",
      email: `ebus${suffix}@example.test`, password: "Una-coleccion-segura-2026!",
    },
  });
  expect(signup.status()).toBe(201);
  await page.goto(`/viajes/nuevo?linea=${line!.id}&recorrido=${route!.id}`);
  await page.getByRole("combobox", { name: "¿Dónde subiste?", exact: true }).selectOption(String(route!.paradas[0].id));
  await page.getByRole("combobox", { name: "¿Dónde bajaste?", exact: true }).selectOption(String(route!.paradas[2].id));
  await page.getByRole("button", { name: "Revisar viaje" }).click();
  await page.getByRole("button", { name: "Confirmar y guardar" }).click();
  await expect(page.getByRole("heading", { name: /Ya es parte de tu colección.|¡Línea completada!/ })).toBeVisible();
  await expect(page.locator(".reward-grid")).toContainText("3");
  const updated: Line = await page.request.get(`/api/v1/lineas/${line!.id}/`).then((r) => r.json());
  expect(updated.numero).toBe("EBUS");
  expect(updated.progreso.transitadas).toBe(3);
  await page.goto(`/recorridos/${route!.id}`);
  await expect(page.locator(".map-canvas")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".stop-list li").filter({ hasText: "Transitada" })).toHaveCount(3);
  await page.screenshot({ path: `test-results/catalogue-extension/${info.project.name}-ebus-progress.png`, fullPage: true, animations: "disabled" });
});
