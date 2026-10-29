import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Bondiala · El AMBA, línea por línea",
    short_name: "Bondiala",
    description: "Recorré. Completá. Coleccioná.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    lang: "es-AR",
    background_color: "#FAFAF7",
    theme_color: "#17213A",
    icons: [192, 512].map((size) => ({
      src: `/icons/icon-${size}.png`,
      sizes: `${size}x${size}`,
      type: "image/png",
      purpose: "any" as const,
    })),
  };
}
