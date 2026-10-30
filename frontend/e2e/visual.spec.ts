import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { officialTestRoute } from "./catalog";

test.use({deviceScaleFactor:1});

test("pantallas completas en claro y oscuro, sin overflow", async ({
  page,
}, info) => {
  test.setTimeout(240000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const token = await page.request
    .get("/api/v1/auth/csrf/")
    .then((r) => r.json());
  const signup = await page.request.post("/api/v1/auth/registro/", {
    headers: { "X-CSRFToken": token.csrfToken },
    data: {
      username: `visual${Date.now()}`,
      nickname: "Coleccionista",
      email: `visual${Date.now()}@example.test`,
      password: "Una-coleccion-segura-2026!",
    },
  });
  expect(signup.status()).toBe(201);
  const route = await officialTestRoute(page.request);
  const line = { id: route.linea };
  const csrf = await page.request
    .get("/api/v1/auth/csrf/")
    .then((r) => r.json());
  const trip = await page.request.post("/api/v1/viajes/", {
    headers: { "X-CSRFToken": csrf.csrfToken },
    data: {
      recorrido: route.id,
      inicio: route.paradas[0].id,
      fin: route.paradas[2].id,
    },
  });
  expect(trip.status()).toBe(201);
  const screens = [
    ["home", "/"],
    ["dashboard", "/dashboard"],
    ["lineas", "/lineas"],
    ["linea", `/lineas/${line.id}`],
    ["recorrido", `/recorridos/${route.id}`],
    ["viaje", `/viajes/nuevo?linea=${line.id}&recorrido=${route.id}`],
    ["mapa", "/mapa"],
    ["perfil", "/perfil"],
    ["rankings", "/ranking"],
    ["logros", "/logros"],
    ["amigos", "/amigos"],
    ["configuracion", "/configuracion"],
  ];
  const directory = `test-results/visual/${info.project.name}`;
  await mkdir(directory, { recursive: true });
  for (const mode of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: mode, reducedMotion: "reduce" });
    for (const [name, path] of screens) {
      await page.goto(path);
      await expect(page.locator("h1").first()).toBeVisible({timeout:15000});
      await expect(page.locator(".route-loader")).toHaveCount(0);
      await expect(page.locator("html")).toHaveAttribute("data-theme", mode);
      if (name === "mapa")
        await page
          .getByRole("combobox", { name: "Línea en el mapa" })
          .selectOption(String(line.id));
      if (["mapa", "linea", "recorrido"].includes(name)) {
        await expect(page.locator(".map-canvas canvas")).toHaveCount(1);
        await expect(page.locator(".map-canvas")).toHaveAttribute(
          "aria-busy",
          "false",
          { timeout: 15000 },
        );
      }
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
        `${name} ${mode}: overflow horizontal`,
      ).toBe(true);
      await page.screenshot({
        path: `${directory}/${name}-${mode}.png`,
        fullPage: true,
        animations: "disabled",
      });
    }
  }
  expect(errors).toEqual([]);
});
