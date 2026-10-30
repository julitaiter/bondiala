# Verificación de la implementación

Validación inicial realizada el **29 de octubre de 2026**. La actualización de paradas oficiales del **30 de octubre** se detalla al final. No se publicaron servicios externos ni se hicieron commits.

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

La muestra ilustrativa no representa paradas oficiales ni toda la red del AMBA. La integración del recurso oficial de BA Data, incorporada el 30 de octubre, se verifica debajo. El contrato real de USIG sigue pendiente. El catálogo CSV incorpora 134 líneas, 557 ramales y 1.104 recorridos. Hay colores para 102 líneas y las restantes usan fallback; faltan geometrías para la mayoría de los recorridos.

No se verificó entrega SMTP de un proveedor real, DNS/TLS públicos ni backups externos: requieren el destino y credenciales del operador. La configuración Nginx HTTPS se comprobó con certificados de prueba, no certificados públicos del dominio. [Pendientes externos](pending.md) enumera esas dependencias; [Decisiones](decisions.md) explica los criterios adoptados.


## Actualización: catálogo desde CSV

Por indicación del usuario, `data/recorrido-colectivos.csv` pasó a ser la fuente principal del catálogo. La migración e importación local terminaron sin errores: **134 líneas, 557 ramales, 1.104 recorridos, 102 líneas con colores y 55 paletas reutilizables**. Se conservaron los 24 trazados existentes y las 202 paradas ilustrativas.

Antes y después de importar se verificaron los mismos **19 usuarios, 13 viajes, 39 avances, 39 eventos y 39 puntos**. Estos conteos corresponden a la instancia de desarrollo antes de las nuevas pruebas E2E, que crean sus propias cuentas y viajes de prueba. Reimportar el CSV produjo `UNCHANGED`, con 1.104 registros omitidos y cero errores.

Se agregaron 12 pruebas de catálogo CSV: fuente predeterminada, importación completa y cobertura de colores, UTF-8/BOM, comillas, nombres de ramal, cabeceras inválidas, archivos vacíos, errores por fila, checksums tras cambiar y revertir una revisión, geometrías opcionales, preservación de viajes y reconciliación de la muestra. CSV conserva la prioridad de metadata cuando se incorporan geometrías GeoJSON.

La API acepta geometrías nulas y expone modalidad, jurisdicción y cámara; la interfaz muestra estados específicos cuando aún no hay trazado o secuencia de paradas. No se fabrican geometrías ni paradas a partir del CSV.

La suite E2E posterior al cambio CSV aprobó sus seis escenarios, incluidas 48 capturas renovadas en desktop/móvil y claro/oscuro. Las pruebas visuales usan escala CSS y tiempos de espera adecuados al catálogo ampliado; se conservan las comprobaciones de geometrías dibujadas, ausencia de overflow y ausencia de excepciones JavaScript.

## Actualización: paradas oficiales de BA Data — 30 de octubre de 2026

Se descargó e importó directamente [el GeoJSON oficial de paradas](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-paradas/paradas-de-colectivo.geojson), sin scraping. SHA-256 `9f56e90159ac44f8217dd7ff0a27a85c2565b6516f60811832978bd83af04d1c`; 2.814.529 bytes. El CSV maestro, su metadata y los 24 trazados existentes conservaron sus huellas exactas para los 1.104 recorridos.

El dry-run contra ese recurso terminó correctamente. Se compararon los conteos de `DataSource`, `ImportRun`, `ImportError`, `StopMatchIssue`, `Parada` y `RecorridoParada` antes y después: ninguno cambió. La posterior importación persistente terminó como `SUCCESS` (ejecución local 38).

| Métrica de la importación real | Resultado |
|---|---:|
| Features leídas | 7.027 |
| Identidades físicas consolidadas/importadas | 6.989 |
| Filas duplicadas consolidadas | 38 |
| Líneas reconocidas dentro del CSV | 131 |
| Paradas sin línea reconocida | 42 (`eBUS`) |
| Advertencias de servicios | 52: 42 denominaciones `eBUS` y 10 sentidos ausentes/desconocidos |
| Features físicas inválidas | 0 |
| Asociaciones nuevas | 32 |
| Ocurrencia ilustrativa reconciliada | 1, reutilizando su PK |
| Ocurrencias oficiales activas resultantes | 33 |
| Asociaciones ambiguas pendientes | 355 |
| Ocurrencias ilustrativas conservadas como legacy en los recorridos actualizados | 71 |
| Recorridos con geometría | 24 / 1.104 (2,17 %) |
| Recorridos sin geometría | 1.080 |
| Recorridos con paradas oficiales y secuencia utilizable | 6 / 1.104 (0,54 %) |
| Recorridos aún sin asociación oficial | 1.098, incluidos 18 con geometría |
| Duplicados de parada dentro de una secuencia oficial activa | 0 |

Las incidencias se auditan por pareja línea/sentido, por lo que sus conteos no son una partición de las paradas físicas: 11.003 casos sin geometría, 355 ambiguos entre ramales, 10 con sentido desconocido y 2 fuera del umbral. El resumen de la ejecución contabilizó 6.808 paradas con alguna pareja sin candidato; una parada puede declarar más de una línea. No se asignaron paradas a todos los ramales superpuestos ni se presentaron esas aproximaciones como relaciones oficiales publicadas.

Los seis recorridos utilizables son `004AIDA` (5 paradas), `004AVUELTA` (5), `004BIDA` (8), `004BVUELTA` (9), `064AVUELTA` (3) y `064BVUELTA` (3). Estos conteos describen asociaciones confiables del catálogo disponible y no una secuencia completa de toda la línea o del AMBA. Una parada puede declarar varias líneas: se verificó `1524 DEFENSA`, con línea 22/vuelta y 53/ida. Las asociaciones compartidas entre recorridos están cubiertas por pruebas, aunque con los trazados actuales ninguna de las 33 asociaciones activas comparte parada física con otro recorrido.

La segunda importación real terminó `UNCHANGED` (ejecución 39): 7.027 features omitidas, cero altas/actualizaciones y las mismas 6.989 paradas, 33 asociaciones y 355 ambigüedades pendientes.

También se ejecutó `--rematch` sobre los datos almacenados (ejecución 40), sin descargar el recurso: cero altas o actualizaciones de asociaciones, con las mismas 355 ambigüedades actuales. Se compararon todas las filas de `RecorridoParada`, incluidos PK, parada, orden, estado, método, fuente y distancias: fueron idénticas antes y después. Las huellas del historial tampoco cambiaron durante ese reprocesamiento.

### Conservación del historial

Antes de migrar/importar se guardó `backups/bondiala-20261030T180359Z.dump` (archivo local ignorado por Git). Se compararon huellas SHA-256 de **todas las filas y todos sus campos** en usuarios, viajes, avances, eventos, logros obtenidos y amistades antes y después de la importación. Fueron idénticas: **31 usuarios, 25 viajes, 75 avances, 75 eventos, 75 puntos, 25 logros obtenidos y 0 relaciones de seguimiento**. No hubo cambios de puntos ni recalculo de premios. Esta comparación se hizo antes de las pruebas E2E, que crean sus propias cuentas y viajes de desarrollo.

Las pruebas de reconciliación también incluyen historias con progreso en la parada a migrar, colisiones con progreso oficial ya existente, ocurrencias referenciadas por viajes y eventos inmutables. Comprueban que se conservan viajes, valores del ledger y primeras fechas, y que no aparecen ocurrencias oficiales duplicadas ni premios nuevos. Las equivalencias sin evidencia suficiente quedan como legacy.

### Verificación automatizada de esta actualización

- Suite backend completa: **91 pruebas aprobadas** sobre una base aislada con PostgreSQL/PostGIS.
- Tras el último ajuste del bloqueo del catálogo: **55 pruebas de importación y concurrencia aprobadas**; no se reutilizó la base de la aplicación para tests.
- Una prueba adicional de integración offline de CI aprobada: bootstrap completo, fixture oficial real de 138 features, reimportación y reinicio sin reactivar ilustrativas ni alterar IDs/orden oficiales. Total de pruebas backend verificadas: **92**, entre la suite completa y esta prueba adicional.
- Frontend: **13 pruebas aprobadas**, TypeScript y ESLint correctos; imagen Next compilada correctamente.
- E2E Chromium sobre la imagen final: **8 de 8 aprobados en 50,2 segundos**, incluyendo viaje oficial real, catálogo sin geometría y bloqueo de respuestas ilustrativas aunque su disponibilidad sea obsoleta. Se renovaron **48 capturas** en claro/oscuro y desktop/móvil, sin overflow ni excepciones JavaScript.
- Auditoría visual adicional sobre la imagen final: **12 de 12 verificaciones aprobadas** para línea 1 con un ramal, `001AIDA` sin geometría y `039AIDA` con trazado pero sin paradas oficiales. El mapa y el bloqueo del registro resultaron correctos en ambos temas y tamaños; capturas y resumen en `frontend/test-results/official-audit/`. Los recorridos vacíos no muestran progreso `0 de 0` ni afirman tener paradas disponibles. Se revisaron visualmente catálogo, lista de paradas reales, mapa, atribución y estados vacíos. Total de capturas de esta actualización: **60**.
- Migraciones: `makemigrations --check --dry-run` sin cambios.
- OpenAPI: `spectacular --validate --fail-on-warn` sin observaciones.
- Las dos imágenes fueron construidas y las migraciones aplicadas en el entorno local respaldado. Los cuatro servicios quedaron saludables.

El alcance y la licencia publicada por BA Data, las configuraciones y la estrategia de identidad están en [Importaciones](importaciones.md) y [Decisiones](decisions.md). Los límites de cobertura y datos externos restantes se mantienen en [Pendientes](pending.md).
