export const dynamic = "force-dynamic";
export function GET() {
  return Response.json({
    light: process.env.MAP_STYLE_LIGHT_URL || "",
    dark: process.env.MAP_STYLE_DARK_URL || "",
  });
}
