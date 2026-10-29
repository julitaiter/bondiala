# Despliegue

El destino es un VPS con Docker Compose, PostgreSQL/PostGIS persistente y Nginx como única entrada pública. Esta configuración no publica ni registra el dominio automáticamente.

## Preparación

1. Apuntar `bondiala.com.ar` al servidor, instalar certificados TLS válidos y configurar su renovación. `TLS_CERTS_DIR` debe contener `fullchain.pem` y `privkey.pem`.
2. Crear `.env` fuera de Git con `DJANGO_SECRET_KEY` aleatoria de al menos 64 caracteres, `DB_PASSWORD` y `POSTGRES_ADMIN_PASSWORD` distintas y fuertes. No usar los valores de desarrollo.
3. Establecer `DJANGO_DEBUG=False`, `BOOTSTRAP_DEMO=false`, `DB_ALLOW_CREATEDB=false`, `FRONTEND_URL=https://bondiala.com.ar`, hosts/orígenes de producción y SMTP real. El override refuerza HTTPS/cookies/HSTS, desactiva la muestra y usa SMTP.
4. Configurar los estilos cartográficos `MAP_STYLE_LIGHT_URL` y `MAP_STYLE_DARK_URL` para un proveedor compatible con la carga y la política de privacidad del sitio. El raster público OSM es un fallback de desarrollo, sujeto a su [política oficial](https://operations.osmfoundation.org/policies/tiles/); no es una garantía de servicio productivo.
5. Usar una base nueva para producción. La inicialización de roles ocurre solo con un volumen vacío. Cambiar una variable de contraseña no modifica contraseñas de roles existentes: para rotarlas usar SQL administrativo por canal seguro y actualizar el secreto de la app.

```sh
docker compose -f compose.yaml -f compose.prod.yaml config --quiet
docker compose -f compose.yaml -f compose.prod.yaml up --build -d --wait
docker compose -f compose.yaml -f compose.prod.yaml exec backend python manage.py check --deploy --fail-level WARNING
docker compose -f compose.yaml -f compose.prod.yaml exec backend python manage.py createsuperuser
```

Luego importar el catálogo validado según [Importaciones](importaciones.md), comprobar HTTPS, email, login y registro de un viaje. Verificar logs, backups y restauración antes de abrir el servicio. El compose productivo exige secretos y certificados; no se despliega automáticamente desde este repositorio.

## Seguridad operativa

Solo se publican 80/443; la base y las aplicaciones no publican 5432/8000/3000. La app usa un rol PostgreSQL `NOSUPERUSER NOCREATEROLE`, sin `CREATEDB` en una base productiva nueva. PostGIS lo instala el rol de inicialización y las migraciones verifican la extensión sin otorgar privilegios extra a Django. Los procesos de Next y Django usan UID 10001. No se monta el socket Docker ni se usa modo privilegiado.

Nginx sobrescribe `X-Forwarded-Proto`, `Host` y los headers de IP: no confiar en proxies públicos adicionales sin adaptar explícitamente esta frontera. El firewall debe admitir solo los puertos públicos necesarios y SSH restringido. Usar SSH por clave, actualizaciones y protección adicional del admin según el proveedor.

La CSP de Next admite scripts inline para el bootstrap de React y el tema inicial; bloquea objetos, frames y formularios externos. Los estilos inline son necesarios para MapLibre. `connect-src https:` e `img-src https:` admiten estilos y avatares configurables: al fijar proveedores conviene limitar esas directivas a sus dominios. La API tiene CSP `default-src 'none'`, respuestas privadas sin caché y no expone UI Swagger CDN.

Los límites de Nginx protegen por IP; DRF limita además por sesión/acción usando caché compartida en PostgreSQL. Los contadores de DRF son aproximados bajo concurrencia, y el control perimetral complementa ese límite. Configurar monitoreo de 429/5xx y alertas de importaciones fallidas. No registrar cuerpos de autenticación ni cookies.

## Backups y restauración

Ejecutar desde la raíz:

```sh
sh scripts/backup.sh
```

El dump usa formato custom, permisos locales restrictivos y no incluye propietarios/ACL. Para producción agregar `-f compose.yaml -f compose.prod.yaml` a los comandos del script o usar la misma identidad `COMPOSE_PROJECT_NAME`. Cifrar y copiar fuera del servidor; el dump local por sí solo no es un backup externo.

Ejemplo de cron de backup diario (adaptar ruta):

```cron
15 3 * * * cd /srv/bondiala && /bin/sh scripts/backup.sh >> /var/log/bondiala-backup.log 2>&1
```

Retención inicial: 7 diarios, 4 semanales y 3 mensuales. Implementarla en el almacenamiento elegido sin borrar la única copia válida.

Para probar restauración, crear una base **separada**, habilitar PostGIS y asignar permisos al rol de aplicación; pasar el dump a `pg_restore --no-owner --no-acl --exit-on-error --dbname=<base_de_prueba>`. Verificar conteos, login, progreso y `SELECT PostGIS_Version()`. Nunca sobrescribir la base activa como parte de una prueba. Una restauración completa y el proveedor de backups deben validarse en la infraestructura elegida.

Si se restaura como administrador con `--no-owner`, transferir después la propiedad de las tablas y secuencias de Django al rol de aplicación (sin reasignar objetos compartidos ni extensiones). Verificar además un endpoint privado usando ese rol. La comprobación local de implementación restauró 4 líneas, 24 recorridos y 202 paradas en una base temporal y obtuvo respuesta 200 de `me/` con el rol `bondiala`; luego se eliminó esa base temporal.

## Mantenimiento

Revisar Dependabot, `npm audit`, `pip-audit`, actualizaciones de imágenes y `check --deploy`. Realizar backup antes de migraciones productivas. El arranque aplica migraciones compatibles; cambios destructivos requieren planificación y restauración validada. Los viajes y el ledger son inmutables desde la API/admin: una corrección de puntos exige un procedimiento administrativo específico, no editar un total almacenado.

Para eliminar una cuenta de forma completa, un administrador debe borrar en una transacción sus eventos de puntos, logros, avances `UsuarioLineaParada`, registros de viaje y finalmente el usuario. Ese orden respeta las referencias protegidas de auditoría. Las sesiones previas quedan sin usuario válido. No basta con ocultar el perfil; la política de retención en backups debe contemplar la solicitud.
