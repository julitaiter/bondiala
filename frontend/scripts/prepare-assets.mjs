import { cp, mkdir, lstat, rm } from "node:fs/promises";
import sharp from "sharp";
const target = new URL("../public/assets", import.meta.url);
const source = new URL("../../assets/", import.meta.url);
const stat = await lstat(target).catch(() => null);
if (stat?.isSymbolicLink()) await rm(target);
await cp(source, target, { recursive: true });
await mkdir(new URL("../public/icons/", import.meta.url), { recursive: true });
for (const size of [192, 512]) {
  await sharp(new URL("light/icono_bondiala.png", source).pathname).resize(size, size).png().toFile(new URL(`../public/icons/icon-${size}.png`, import.meta.url).pathname);
}
await mkdir(new URL("../public/maplibre/", import.meta.url), { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  await cp(new URL(`../node_modules/maplibre-gl/dist/${file}`, import.meta.url), new URL(`../public/maplibre/${file}`, import.meta.url));
}
await mkdir(new URL("../public/licenses/", import.meta.url), { recursive: true });
await cp(new URL("../node_modules/maplibre-gl/LICENSE.txt", import.meta.url), new URL("../public/licenses/MapLibre-BSD.txt", import.meta.url));
await cp(new URL("../node_modules/@fontsource-variable/archivo/LICENSE", import.meta.url), new URL("../public/licenses/Archivo-OFL.txt", import.meta.url));
