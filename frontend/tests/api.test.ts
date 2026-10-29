import { describe, it, expect, vi } from "vitest";
import { api, mutate } from "@/lib/api";
describe("cliente de sesión y CSRF", () => {
  it("obtiene CSRF por cada operación y nunca envía premios calculados", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ csrfToken: "csrf-masked-token" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 1 }),
      });
    vi.stubGlobal("fetch", fetch);
    await mutate("viajes/", { recorrido: 1, inicio: 2, fin: 3 });
    expect(fetch.mock.calls[0][0]).toBe("/api/v1/auth/csrf/");
    const options = fetch.mock.calls[1][1];
    expect(options.headers.get("X-CSRFToken")).toBe("csrf-masked-token");
    expect(options.credentials).toBe("same-origin");
    expect(JSON.parse(options.body)).toEqual({
      recorrido: 1,
      inicio: 2,
      fin: 3,
    });
  });
  it("presenta validaciones de campos del backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          json: async () => ({ error: { inicio: ["Parada inválida"] } }),
        }),
    );
    await expect(api("viajes/")).rejects.toThrow("inicio: Parada inválida");
  });
  it("no intenta decodificar respuestas sin contenido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 204 }),
    );
    await expect(api("test/")).resolves.toBeUndefined();
  });
});
