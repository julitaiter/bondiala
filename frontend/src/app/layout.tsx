import type { Metadata, Viewport } from "next";
import "@fontsource-variable/archivo";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: {
    default: "Bondiala · El AMBA, línea por línea",
    template: "%s · Bondiala",
  },
  description:
    "Convertí cada viaje en colectivo en una nueva parte de tu colección. Explorá líneas, registrá recorridos y descubrí cuánto del AMBA ya bondiaste.",
  applicationName: "Bondiala",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      {
        url: "/assets/light/icono_bondiala.ico",
        media: "(prefers-color-scheme: light)",
      },
      {
        url: "/assets/dark/favicon_bondiala_dark.ico",
        media: "(prefers-color-scheme: dark)",
      },
    ],
    apple: "/icons/icon-192.png",
  },
  appleWebApp: { capable: true, statusBarStyle: "default", title: "Bondiala" },
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAFAF7" },
    { media: "(prefers-color-scheme: dark)", color: "#0E1320" },
  ],
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-AR" suppressHydrationWarning>
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('bondiala-theme')||'system';document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t}catch(e){}`,
          }}
        />
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
