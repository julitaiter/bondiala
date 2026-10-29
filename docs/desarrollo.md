# Desarrollo de Bondiala

Requisitos: Docker Engine y Docker Compose 2.24.4 o posterior. No hace falta instalar Python, GDAL ni PostgreSQL en el host.

```sh
cp .env.example .env
docker compose up --build
```

Abrir **http://localhost:8080**. El primer arranque aplica migraciones, crea la tabla de rate limiting, carga niveles/logros y el catálogo desde `data/recorrido-colectivos.csv`. No crea usuarios: registrate desde la web. Los datos permanecen en el volumen `postgres_data`.

El CSV aporta 134 líneas, 557 ramales y 1.104 recorridos por sentido; 102 líneas tienen colores en el JSON existente. Como complemento de desarrollo se cargan 24 trazados oficiales de cuatro líneas y 202 paradas **ilustrativas**, muestreadas sobre esos trazados para probar el flujo. El CSV no contiene geometrías ni paradas: los recorridos restantes se pueden explorar, pero su mapa o registro esperan esos datos. La interfaz avisa de las paradas de muestra y de los trazados no disponibles.

El puerto 8080 se publica únicamente en loopback. Django, Next y PostgreSQL permanecen internos. Podés cambiar `PORT` en `.env`.

## Administración y comandos

```sh
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py bootstrap
docker compose exec backend python manage.py seed_game
docker compose exec backend python manage.py import_badata_recorridos
docker compose exec backend python manage.py import_badata_paradas --file /data/mis-paradas.geojson
docker compose exec backend python manage.py import_line_colors /colores_lineas_bondiala.json
```

El admin está en `/admin/`; los eventos, viajes y avances son de solo lectura. `bootstrap` solo funciona con `DJANGO_DEBUG=True` y usa el CSV como catálogo, añadiendo después los complementos visuales/de paradas. `seed_game` no sobrescribe ajustes del admin. Para producción usar `BOOTSTRAP_DEMO=false` e importar el CSV con `import_badata_recorridos`; los trazados y las paradas reales se cargan por separado según [Importaciones](importaciones.md). Las instancias anteriores actualizan los recorridos de muestra conservando IDs y datos de usuario.

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
cd frontend
npx playwright install --with-deps chromium
npm run test:e2e
```

Las pruebas usan cuentas únicas `@example.test` sobre la instancia de desarrollo y cubren registro, viaje, progreso, perfil, ranking, temas, logout y login en desktop y móvil. `E2E_BASE_URL` permite cambiar la URL. No ejecutarlas contra producción. Reportes y trazas se guardan en `frontend/test-results/` (ignorado por Git).

## Detener

`docker compose down` detiene los servicios conservando la base. `docker compose logs --tail=100` muestra los logs. No es necesario eliminar volúmenes para reconstruir los contenedores.
