# Desarrollo de Bondiala

Requisitos: Docker Engine y Docker Compose 2.24.4 o posterior. No hace falta instalar Python, GDAL ni PostgreSQL en el host.

```sh
cp .env.example .env
docker compose up --build
```

Abrir **http://localhost:8080**. El primer arranque aplica migraciones, crea la tabla de rate limiting, carga niveles/logros y el catálogo desde `data/recorrido-colectivos.csv`. No crea usuarios: registrate desde la web. Los datos permanecen en el volumen `postgres_data`.

El CSV aporta 135 líneas, 565 ramales y 1.120 recorridos por sentido; 102 líneas tienen colores en el JSON existente. Como complemento de desarrollo se cargan 24 trazados oficiales de cuatro líneas y se conservan 202 paradas **ilustrativas** para auditar la transición desde versiones anteriores. Esas paradas no se ofrecen para registrar viajes nuevos. El CSV no contiene geometrías ni paradas: los recorridos se pueden explorar y muestran qué datos faltan.

Para incorporar los trazados oficiales complementarios al CSV, importar las paradas y evaluar su asociación:

```sh
docker compose exec backend python manage.py import_badata_recorridos --geojson --dry-run
docker compose exec backend python manage.py import_badata_recorridos --geojson
docker compose exec backend python manage.py import_badata_paradas --match-routes --dry-run
docker compose exec backend python manage.py import_badata_paradas --match-routes
```

Si las paradas oficiales ya están almacenadas, reemplazá las dos últimas instrucciones por `import_badata_paradas --rematch --dry-run` y `import_badata_paradas --rematch`; ese modo no descarga otra vez los Points. `BA_DATA_RECORRIDOS_GEOJSON_URL` configura los trazados y `BA_DATA_PARADAS_GEOJSON_URL` configura las paradas. Cada fase admite archivo local; no es necesario acceder al CDN durante las pruebas.

Los recursos cubren colectivos y paradas de CABA y no garantizan cobertura completa del AMBA. El GeoJSON de recorridos inspeccionado el 6/11 contiene 112 features, con 112 coincidencias exactas tras incorporar al CSV las variantes documentadas; el importador geométrico no crea entidades. Solo las asociaciones confiables forman parte de la secuencia; se necesitan geometría, al menos dos paradas oficiales activas y ausencia de un rematch pendiente o inconsistencia crítica para registrar un viaje. [Importaciones](importaciones.md) explica los umbrales, corredores compartidos y ambigüedades.

El puerto 8080 se publica únicamente en loopback. Django, Next y PostgreSQL permanecen internos. Podés cambiar `PORT` en `.env`.

## Administración y comandos

```sh
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py bootstrap
docker compose exec backend python manage.py seed_game
docker compose exec backend python manage.py import_badata_recorridos
docker compose exec backend python manage.py import_badata_recorridos --geojson
docker compose exec backend python manage.py import_badata_paradas --match-routes
docker compose exec backend python manage.py import_badata_paradas --rematch
docker compose exec backend python manage.py import_line_colors /colores_lineas_bondiala.json
```

El admin está en `/admin/`; los eventos, viajes y avances son de solo lectura. `bootstrap` solo funciona con `DJANGO_DEBUG=True` y usa el CSV como catálogo. Su carga de trazados de muestra usa `--only-missing`, con checksum independiente, para no reemplazar geometrías ya actualizadas ni invalidar su secuencia al reiniciar. `seed_game` no sobrescribe ajustes del admin. Para producción usar `BOOTSTRAP_DEMO=false` e importar el CSV con `import_badata_recorridos`; los trazados y las paradas reales se cargan por separado según [Importaciones](importaciones.md). Las instancias anteriores actualizan los recorridos de muestra conservando IDs y datos de usuario.

## Verificación

```sh
docker compose run --rm backend python manage.py test --noinput
docker compose run --rm backend python manage.py makemigrations --check --dry-run
docker compose run --rm backend python manage.py check
```

La base de desarrollo permite `CREATEDB` al usuario de aplicación y proporciona `template_bondiala` con PostGIS para crear una base de tests aislada. En producción se deshabilita ese permiso: **no correr tests contra la base productiva**.

Para trabajar en el frontend con Node 22.22 o posterior:

```sh
cd frontend
npm ci
npm run dev
npm run typecheck
npm run lint
npm test
npm run build
```

El frontend local necesita una API en `API_INTERNAL_URL`, por defecto `http://127.0.0.1:8000`. Para desarrollar contra los contenedores sin publicar Django, lo más sencillo es reconstruir `docker compose up --build`. Otra opción es publicar temporalmente Django en loopback y ajustar `API_INTERNAL_URL`, `CSRF_TRUSTED_ORIGINS` y `DJANGO_ALLOWED_HOSTS` al origen local elegido.

Los scripts `predev` y `prebuild` copian los originales de `assets/` a una carpeta pública ignorada por Git y generan iconos PWA de 192/512 px. Se preservan los archivos originales, incluidos los nombres distintos de la variante oscura. Archivo se sirve localmente desde `@fontsource-variable/archivo`, que incluye su licencia OFL.

## Pruebas de navegador

Con el stack en ejecución:

```sh
docker compose exec -T backend python manage.py import_badata_recorridos --geojson --file /data/recorridos.variants.sample.geojson
docker compose exec -T backend python manage.py import_badata_paradas --file /data/paradas.catalogue.sample.geojson --match-routes
cd frontend
npx playwright install --with-deps chromium
npm run test:e2e
```

Las fixtures contienen 16 geometrías oficiales de las variantes incorporadas y 180 features oficiales de paradas de línea 4/eBUS, conservando propiedades y coordenadas. Junto a los 24 trazados del bootstrap preparan una base de pruebas sin depender del CDN; CI usa esta misma secuencia. Si ya se importaron los recursos completos, no hace falta cargar esos subconjuntos. Las pruebas seleccionan dinámicamente un recorrido con secuencia oficial utilizable y verifican las ocho variantes, búsqueda alfanumérica, badges y un viaje real en eBUS. Usan cuentas únicas `@example.test` sobre la instancia de desarrollo y cubren además registro, viaje numérico, progreso, perfil, ranking, temas, logout y login en desktop y móvil. `E2E_BASE_URL` permite cambiar la URL. No ejecutarlas contra producción. Reportes y trazas se guardan en `frontend/test-results/` (ignorado por Git).

## Detener

`docker compose down` detiene los servicios conservando la base. `docker compose logs --tail=100` muestra los logs. No es necesario eliminar volúmenes para reconstruir los contenedores.
