import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import {
  LineBadge,
  ProgressBar,
  ThemeToggle,
  ErrorState,
  Empty,
  Gate,
} from "@/components/ui";
import { Providers } from "@/components/providers";

const palette = {
  color_principal: "#BE1F1C",
  color_secundario_1: "#CCC7B1",
  color_secundario_2: "#1D3B78",
  color_texto: "#FFFFFF",
};
function session() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ user: null }) }),
  );
}
describe("componentes de la colección", () => {
  it("identifica la línea y conserva sus colores en ambos temas", () => {
    const { rerender } = render(<LineBadge numero="60" colores={palette} />);
    const badge = screen.getByLabelText("Línea 60");
    expect(badge).toHaveTextContent("60");
    expect(badge).toHaveStyle({
      "--line-main": "#BE1F1C",
      "--line-text": "#FFFFFF",
    });
    document.documentElement.dataset.theme = "dark";
    rerender(<LineBadge numero="60" colores={palette} />);
    expect(screen.getByLabelText("Línea 60")).toHaveStyle({
      "--line-main": "#BE1F1C",
    });
  });
  it("expone progreso accesible sin depender del color", () => {
    render(<ProgressBar value={62.5} label="Paradas transitadas" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "62.5",
    );
    expect(screen.getByText("63%")).toBeVisible();
  });
  it("permite cambiar light, dark y system sin credenciales locales", async () => {
    session();
    render(
      <Providers>
        <ThemeToggle />
      </Providers>,
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Sistema" })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Oscuro" }));
    await waitFor(() =>
      expect(document.documentElement).toHaveAttribute("data-theme", "dark"),
    );
    expect(localStorage.getItem("bondiala-theme")).toBe("dark");
    fireEvent.click(screen.getByRole("button", { name: "Claro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    fireEvent.click(screen.getByRole("button", { name: "Sistema" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });
  it("muestra un error accionable y permite reintentar", () => {
    const retry = vi.fn();
    render(<ErrorState message="Sin conexión" retry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Sin conexión");
    fireEvent.click(screen.getByRole("button", { name: "Intentar de nuevo" }));
    expect(retry).toHaveBeenCalledOnce();
  });
  it("ofrece una acción en un estado vacío", () => {
    render(
      <Empty
        title="Sin viajes"
        text="Registrá tu primer tramo"
        href="/viajes/nuevo"
        cta="Registrar viaje"
      />,
    );
    expect(
      screen.getByRole("link", { name: "Registrar viaje" }),
    ).toHaveAttribute("href", "/viajes/nuevo");
  });
  it("protege contenido privado cuando no hay sesión", async () => {
    session();
    render(
      <Providers>
        <Gate>
          <p>Historial privado</p>
        </Gate>
      </Providers>,
    );
    await screen.findByText("Tu colección te espera");
    expect(screen.queryByText("Historial privado")).not.toBeInTheDocument();
  });
});
