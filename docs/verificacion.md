# Verificación de la implementación

Validación local realizada el **29 de octubre de 2026**. No se publicaron servicios externos ni se hicieron commits.

## Resultado ejecutado

| Comprobación | Resultado |
|---|---|
| Construcción de imágenes backend/frontend | Correcta; Next completa compilación, TypeScript y generación de páginas |
| `docker compose up -d --wait` | Los cuatro servicios quedan saludables |
| Entrada HTTP | `http://localhost:8080`; solo Nginx publicado en loopback |
| Healthcheck | HTTP 200, conexión real y `PostGIS_Version()` |
| Migraciones desde base vacía | Aplicadas; incluidas en el repositorio |
| `makemigrations --check --dry-run` | Sin cambios pendientes |
| Backend | **57 tests aprobados** sobre PostgreSQL/PostGIS |
| Frontend | **9 tests aprobados**, TypeScript estricto y ESLint sin errores |
| E2E Chromium | **6 escenarios aprobados**: recorrido funcional, catálogo CSV sin trazado/paradas y revisión de pantallas en desktop/móvil |
| Revisión visual automatizada | **48 capturas**: 12 pantallas × claro/oscuro × desktop/móvil; sin overflow horizontal ni excepciones JavaScript |
| Mapas | Workers ESM propios; la suite espera geometrías efectivamente dibujadas antes de capturar |
| PWA en Chromium | Service worker activo, manifest sin errores y criterios de instalación sin errores según DevTools Protocol |
| OpenAPI | `spectacular --validate --fail-on-warn` sin errores/advertencias |
| Django producción | `check --deploy --fail-level WARNING` sin observaciones, con DEBUG desactivado y configuración segura |
| Auditoría Python | `pip-audit -r requirements.txt`: sin vulnerabilidades conocidas |
| Auditoría JavaScript | `npm audit --audit-level=high`: 0 vulnerabilidades |
| Compose producción | Configuración válida usando valores ficticios para las variables obligatorias |
| Nginx HTTPS | `nginx -t` correcto con certificados temporales de prueba, sin publicar puertos |
| Permisos de procesos | Django y Next ejecutan con UID 10001, sin root |
| Rol de aplicación | `NOSUPERUSER NOCREATEROLE`; CREATEDB solo en este entorno de desarrollo/tests |
| Backup/restauración anterior al CSV | Dump restaurado en base separada; 4 líneas, 24 recorridos, 202 paradas y `me/` HTTP 200 usando el rol normal. Base temporal eliminada |
| Higiene | `git diff --check` correcto; sin claves privadas, tokens ni secretos reales detectados en los archivos fuente revisados |

El build ejecutado directamente en el sandbox del host encontró una restricción de creación de procesos/puertos de Turbopack. El build del mismo proyecto se completó dentro del entorno Docker de referencia. No se atribuye ese error a la aplicación ni se afirma que se haya ejecutado un despliegue público.

## Cobertura funcional

Las pruebas backend comprueban normalización, restricciones de unicidad, segmento inclusivo, acumulación en distintos viajes, paradas compartidas entre ramales y separación entre líneas. Comprueban bonus, logros y claves idempotentes, incluso con dos viajes concurrentes; un fallo en la adjudicación revierte viaje, avances y eventos completos.

La cobertura de seguridad verifica que un usuario no consulte viajes privados ajenos, no los modifique ni elimine, no acceda a acciones admin y no pueda enviar puntos/ownership arbitrarios. Comprueba CSRF antes de iniciar sesión, cookies HttpOnly, registro, logout, recuperación de contraseña con respuesta no enumerativa y tokens de un uso. También revisa privacidad de perfiles y propiedad de relaciones.

Los importadores se prueban con fuentes locales, reimportaciones por checksum, actualizaciones, LineString/MultiLineString, geometrías inválidas, fuente vacía, relaciones explícitas y ambiguas, conservación de ocurrencias históricas, paletas compartidas y enriquecimiento persistente. El bootstrap importa features reales de BA Data, con paradas de muestra señaladas como tales.

El recorrido E2E crea cuentas de prueba `@example.test`, inicia sesión por registro, explora una línea, registra subida/bajada, comprueba 3 paradas nuevas, perfil y ranking, alterna claro/oscuro/sistema, guarda preferencias y verifica logout/login. Las capturas incluyen home, dashboard, líneas, detalle de línea, recorrido, alta de viaje, mapa, perfil, rankings, logros, amigos y configuración. Los resultados reproducibles quedan en `frontend/test-results/` (ignorados por Git).

## Implementación disponible

- **Modelo:** `User`, `LineaColor`, `Linea`, `Ramal`, `Recorrido`, `Parada`, `RecorridoParada`, `RegistroViaje`, `UsuarioLineaParada`, `EventoPuntos`, `Nivel`, `Logro`, `UsuarioLogro`, `Follow`, `DataSource`, `ImportRun`, `ImportError`.
- **Servicios:** cálculo de progreso derivado, registro transaccional, adjudicación única de eventos/logros, niveles editables y rankings desde el ledger.
- **API:** sesión/CSRF, cuentas, recuperación, preferencias, líneas/recorridos/paradas, viajes privados, progreso, perfiles, logros, amigos y rankings. Contratos en [API](api.md).
- **Importación:** `import_badata_recorridos`, `import_badata_paradas`, `import_line_colors`, `enrich_usig`, `seed_game`, `bootstrap`. Formatos en [Importaciones](importaciones.md).
- **Interfaz:** todas las pantallas mínimas, mapa MapLibre, PWA, componentes de línea/progreso, apariencia y variantes de assets. Los originales permanecen intactos.
- **Operación:** Docker/Compose, Nginx, SMTP configurable, caché de límites en PostgreSQL, CI y Dependabot, backups, configuración productiva y documentación.

## Límites reales

La muestra no contiene paradas oficiales ni toda la red del AMBA. No hay una fuente de paradas ni un contrato USIG definidos en la documentación original; los adaptadores normalizados están implementados y probados. El catálogo CSV incorpora 134 líneas, 557 ramales y 1.104 recorridos. Hay colores para 102 líneas y las restantes usan fallback; las geometrías y paradas reales siguen pendientes para los recorridos que no las incluyen.

No se verificó entrega SMTP de un proveedor real, DNS/TLS públicos ni backups externos: requieren el destino y credenciales del operador. La configuración Nginx HTTPS se comprobó con certificados de prueba, no certificados públicos del dominio. [Pendientes externos](pending.md) enumera esas dependencias; [Decisiones](decisions.md) explica los criterios adoptados.


## Actualización: catálogo desde CSV

Por indicación del usuario, `data/recorrido-colectivos.csv` pasó a ser la fuente principal del catálogo. La migración e importación local terminaron sin errores: **134 líneas, 557 ramales, 1.104 recorridos, 102 líneas con colores y 55 paletas reutilizables**. Se conservaron los 24 trazados existentes y las 202 paradas ilustrativas.

Antes y después de importar se verificaron los mismos **19 usuarios, 13 viajes, 39 avances, 39 eventos y 39 puntos**. Estos conteos corresponden a la instancia de desarrollo antes de las nuevas pruebas E2E, que crean sus propias cuentas y viajes de prueba. Reimportar el CSV produjo `UNCHANGED`, con 1.104 registros omitidos y cero errores.

Se agregaron 12 pruebas de catálogo CSV: fuente predeterminada, importación completa y cobertura de colores, UTF-8/BOM, comillas, nombres de ramal, cabeceras inválidas, archivos vacíos, errores por fila, checksums tras cambiar y revertir una revisión, geometrías opcionales, preservación de viajes y reconciliación de la muestra. CSV conserva la prioridad de metadata cuando se incorporan geometrías GeoJSON.

La API acepta geometrías nulas y expone modalidad, jurisdicción y cámara; la interfaz muestra estados específicos cuando aún no hay trazado o secuencia de paradas. No se fabrican geometrías ni paradas a partir del CSV.

La suite E2E posterior al cambio CSV aprobó sus seis escenarios, incluidas 48 capturas renovadas en desktop/móvil y claro/oscuro. Las pruebas visuales usan escala CSS y tiempos de espera adecuados al catálogo ampliado; se conservan las comprobaciones de geometrías dibujadas, ausencia de overflow y ausencia de excepciones JavaScript.
