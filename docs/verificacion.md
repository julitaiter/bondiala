# Verificación de la implementación

Validación inicial realizada el **29 de octubre de 2026**. Las actualizaciones de paradas oficiales del **30 de octubre** y geometrías del **6 de noviembre** se detallan al final. Cada sección conserva los resultados de su fecha. No se publicaron servicios externos ni se hicieron commits.

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

## Actualización: geometrías oficiales y corredores compartidos — 6 de noviembre de 2026

Se ejecutó la fase independiente `import_badata_recorridos --geojson` usando el valor predeterminado de `BA_DATA_RECORRIDOS_GEOJSON_URL`, seguida por `import_badata_paradas --rematch`. El CSV conserva la responsabilidad exclusiva de definir líneas, ramales, sentidos y metadata. El GeoJSON de recorridos sólo complementa geometrías; `BA_DATA_PARADAS_GEOJSON_URL` continúa siendo la fuente de ubicaciones oficiales. Las asociaciones de parada a ramal y su orden son **inferencias espaciales de Bondiala**, con evidencia auditable, y no relaciones publicadas por BA Data.

El [recurso oficial de recorridos](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-recorridos/recorrido-colectivos.geojson) descargado contiene **112 features**, todas MultiLineString, **655.234 bytes** y SHA-256 `405e3f1aebc4c3dbca56547fa8595a71cbc5c1906566b60d62aeeb056ec0054f`. La importación persistente fue `SUCCESS` (ejecución local 66): 96 matches exactos por `l_r_s`, 0 secundarios, 16 sin correspondencia, 72 geometrías nuevas, 0 actualizadas y 24 idénticas. No hubo errores de geometría ni conflictos de identidad.

Los 16 identificadores sin match son ida/vuelta de `050C`, `012C`, `151B`, `151C`, `151D`, `102B`, `EBUSA` y `042C`. Quedan en `ImportError` para revisión documental; no crean entradas de catálogo ni se descartan recorridos CSV.

| Métrica | Antes | Después del rematch |
|---|---:|---:|
| Líneas / ramales / recorridos | 134 / 557 / 1.104 | 134 / 557 / 1.104 |
| Recorridos con geometría | 24 (2,17 %) | **96 (8,70 %)** |
| Recorridos sin geometría | 1.080 | **1.008** |
| Paradas físicas oficiales | 6.989 | **6.989** |
| Ocurrencias oficiales activas | 33 | **4.363** |
| Recorridos con paradas oficiales asociadas | 6 | **96 (8,70 %)** |
| Recorridos utilizables | 6 (0,54 %) | **92 (8,33 %)** |
| Asociaciones ambiguas pendientes | 355 | **44** |
| Asociaciones aceptadas por corredor compartido | 0 | **3.000** |

El rematch persistente terminó `SUCCESS` en 69,83 segundos (ejecución 77), con 4.329 asociaciones creadas y 34 actualizadas, sin descargar paradas de nuevo. Se resolvieron 348 de los 355 casos ambiguos anteriores; 7 persisten y surgieron 37 nuevos al ampliar las geometrías. La evidencia compartida corresponde a 1.357 casos parada/línea/sentido y 1.287 paradas físicas distintas; esos conteos no son intercambiables. Por ejemplo, `11804 PAZ, GRAL. AV.` queda asociada a `004AIDA` y `004BIDA`, con una proyección propia por recorrido.

Los estados resultantes son 1.008 recorridos sin geometría, 48 parciales utilizables, 44 disponibles y 4 ambiguos bloqueados por proyección crítica. No quedaron flags de rematch pendiente. Se verificaron cero parejas parada/recorrido duplicadas en las secuencias oficiales activas, órdenes contiguos desde 1, posiciones acumuladas monótonas y evidencia presente en las 4.363 asociaciones. El criterio de disponibilidad de la API coincide con el de las métricas del importador; las 96 geometrías no equivalen a 96 recorridos habilitados.

### Preservación y repetibilidad

El backup previo fue `backups/bondiala-20261106T155312Z.dump`. Tras el corte de sesión se restauró en una **base temporal aislada**, se compararon todas las filas y campos históricos mediante huellas y luego se eliminó esa base temporal. Coinciden exactamente **40 usuarios, 37 viajes, 126 avances, 132 eventos, 36 logros obtenidos, 1 seguimiento y 176 puntos**. También coinciden Linea y Ramal completos, identidad/metadata/checksum CSV de los 1.104 recorridos, extremos físicos de viajes y las 24 geometrías anteriores.

El dry-run inicial de geometrías anticipó las 72 altas sin persistir. Se volvió a comprobar `--geojson --force --dry-run` sobre el estado final: las huellas completas de fuentes, ejecuciones, errores, incidencias, catálogo, paradas y asociaciones quedaron idénticas. `--rematch --dry-run` anticipó exactamente la cobertura de la ejecución persistente y conservó esas mismas huellas, incluido el historial. Las comparaciones posteriores al rematch también conservan todas las filas históricas, extremos y geometrías previas. Esta auditoría se cerró antes de ejecutar E2E, que crea sus propias cuentas y viajes de desarrollo.

Reimportar el GeoJSON terminó `UNCHANGED` (ejecución 79): 112 features omitidas por checksum, cero altas/actualizaciones y las mismas 96 geometrías. El checksum de la fase oficial se mantiene independiente del bootstrap de muestras. Repetir el rematch terminó `SUCCESS` (ejecución 80), con cero asociaciones creadas o actualizadas: las huellas de todas las filas de RecorridoParada, incluidos PK, orden, posición, fuente y evidencia, resultaron idénticas; también historial, catálogo y cobertura. Los resultados de auditoría y sus scripts están en `backups/verification-20261106/`, ignorados por Git.

### Verificación automatizada

- Backend: **134 pruebas aprobadas** sobre PostgreSQL/PostGIS aislado. Tras los últimos ajustes se aprobaron además **42 pruebas de matching/importación oficial** y **9 de secuencias y viajes oficiales**. Cubren geometrías, matching de identidad, validación externa, dry-run integral, acumulación MultiLineString, corredores compartidos/divergentes, proyecciones ambiguas, alias históricos y rollback.
- Frontend: **19 pruebas aprobadas**, TypeScript y ESLint sin errores. Cubren selección lista/mapa, estados de cobertura, segmentos MultiLineString y registro con paradas oficiales.
- E2E Chromium sobre las imágenes finales: **8 de 8 aprobados**, salida 0, aproximadamente **1,1 minutos**. Comprueban orden, selección bidireccional lista/mapa, subida/bajada por IDs de ocurrencia, tramo inclusivo, viaje real y tres paradas transitadas al volver al mapa; también bloquean datos ilustrativos y cobertura ausente.
- Auditoría visual adicional de datos reales: **12 de 12 verificaciones aprobadas**, sin crear cuentas. Casos `004AIDA` parcial utilizable con corredor compartido, `001AIDA` sin geometría y `007AIDA` bloqueado por proyección crítica, en claro/oscuro y desktop/móvil. Se revisaron selección, trazado, lista, bloqueo de botones y estados vacíos; sin overflow ni excepciones JavaScript. Artefactos: **62 PNG** en `frontend/test-results/`: 48 pantallas generales, 2 selecciones de tramo y 12 auditorías de geometría, con resumen en `geometry-audit/summary.json`.
- Migraciones: `makemigrations --check --dry-run` sin cambios. OpenAPI: `spectacular --validate --fail-on-warn` sin observaciones.
- Imágenes backend/frontend construidas; las migraciones están aplicadas y los cuatro servicios locales saludables.
- Comprobación puntual de API tras el rematch: catálogo HTTP 200 en 0,19 s y recorrido HTTP 200 en 0,04 s; `/health/` confirma conexión PostGIS. Son mediciones locales puntuales, no una prueba de carga.

La fuente sólo aporta 96 geometrías compatibles con los 1.104 recorridos CSV. No se afirma cobertura completa de CABA ni del AMBA. Los límites restantes están en [Pendientes](pending.md).

## Revisión individual de los 16 identificadores sin correspondencia — 6 de noviembre de 2026

Se volvió a descargar el recurso oficial: **112 features, 655.234 bytes**, con el mismo SHA-256 `405e3f1aebc4c3dbca56547fa8595a71cbc5c1906566b60d62aeeb056ec0054f`. El CSV mantiene **1.104 registros** y SHA-256 `1f5fef5fe11f05723957883986057cb824d6a9048213ef7227d3e3ac33514c03`. Se compararon literalmente y normalizados `linea`, `recorrido`, `sentido`, `l_r_s`, más cabeceras, geometrías y documentación oficial.

**Resultado: causas esclarecidas para los 16 identificadores, cero equivalencias seguras con recorridos existentes.** Son 14 sentidos de siete ramales ausentes y dos sentidos del servicio eBUS, cuya línea tampoco está en el CSV y no satisface la identidad numérica del modelo. Se documentaron la fusión 6/50, la reorganización 90/151, las variantes 12 C y 42 C, el servicio corto 102 B y el servicio eBUS. El foro oficial describe el renombre 151 B→C, pero B no tiene fila de origen en este CSV. La [comparación por caso](importaciones.md) enlaza las fuentes primarias y el [registro versionado](../data/recorridos.reconciliation.json) conserva propiedades reales, filas candidatas, huellas y decisiones.

Las 14 geometrías numéricas resultan diferentes de todos sus candidatos existentes de igual línea/sentido, tanto por WKB como por igualdad topológica GEOS. Las comparaciones métricas usan EPSG:32721; sus longitudes no se interpretan como longitudes reglamentarias. Para 012 C se comprobó una longitud UTM de 13.879,17 m ida y 13.393,17 m vuelta, frente a 12.590,33 y 12.677,53 m de 012 A. Que ambos compartan cabeceras no autoriza a fusionarlos. Tampoco se usa `elr_sube` para determinar ramal: los valores compartidos entre 151 A/B y 102 A/B lo invalidan como clave única.

No se añadieron aliases ni se modificó el CSV, la lógica del importador o entidades de transporte. Los **16 siguen pendientes de actualización documentada del catálogo**; sus errores de importación anteriores permanecen auditables. No se ejecutó un rematch persistente porque no se incorporó ni cambió ninguna geometría.

| Métrica | Inicio de esta revisión | Final |
|---|---:|---:|
| Geometrías | 96 | **96** |
| Recorridos utilizables | 92 | **92** |
| Ambigüedades espaciales pendientes | 44 | **44** |
| Ocurrencias oficiales activas | 4.363 | **4.363** |
| Features geométricas sin correspondencia CSV | 16 | **16** |

### Comprobaciones ejecutadas en esta revisión

- `import_badata_recorridos --geojson --file /audit/recorridos.geojson --force --dry-run`: `SUCCESS`, 96 matches exactos/sin cambios, 0 secundarios, 16 sin match, 0 altas, actualizaciones, errores o conflictos. La ejecución simulada 81 se revirtió y no quedó como importación persistida.
- Comparación SHA-256 de **todas las filas y campos** de fuentes, importaciones, errores, incidencias, catálogo, paradas y asociaciones antes/después del dry-run: idénticos. También identidad CSV, geometrías y extremos físicos de viajes.
- Historial actual idéntico: **44 usuarios, 41 viajes, 138 avances, 144 eventos, 40 logros obtenidos, 1 seguimiento y 188 puntos**. Este baseline incluye las cuentas y viajes E2E de la fase anterior; esta revisión no creó usuarios ni viajes.
- **48 pruebas backend aprobadas en 22,810 s**, con salida 0, usando una base PostGIS aislada: `imports.test_route_reconciliation`, `imports.test_route_geometries`, `imports.test_csv` y `trips.tests.OfficialSequenceTests`. La regresión nueva usa las 16 propiedades reales y una geometría de fixture deliberadamente idéntica para comprobar que ni coincidencias geométricas ni cabeceras/códigos SUBE compartidos reasignen identidades o amplíen el CSV. Quedan comprobadas auditoría de los 16 rechazos y preservación de todas las filas del catálogo.
- No hubo cambios de frontend ni se repitieron E2E en esta revisión. Los resultados E2E de la fase anterior se conservan en su sección, con su alcance correspondiente.

Los servicios estaban detenidos al comenzar esta revisión. Se inició sólo PostgreSQL y se usaron contenedores temporales sin bootstrap; al finalizar se detuvo de nuevo PostgreSQL para restaurar ese estado. Los snapshots, comparación geométrica y salida de pruebas de esta revisión quedan en `backups/reconciliation-20261106/`, ignorados por Git. La evidencia de identidades queda versionada en `data/recorridos.reconciliation.json` para revisión sin depender de esos archivos locales.

## Ampliación autorizada del catálogo y soporte eBUS — 6 de noviembre de 2026

Una solicitud posterior autorizó incorporar variantes documentadas como recorridos propios y soportar líneas alfanuméricas. Se revalidaron las fuentes de los ocho casos, incluyendo normativa aprobada y documentación GCBA reciente. Se agregaron los dos sentidos de **050 C, 012 C, 151 B, 151 C, 151 D, 102 B, EBUS A y 042 C**. Todos quedaron agregados y utilizables en ambos sentidos; ninguno se resolvió mediante un alias, renombre de una fila anterior o baja automática. [Importaciones](importaciones.md) registra por caso motivo, fuentes, vigencia y límites.

El CSV conserva byte por byte sus 1.104 filas anteriores y añade 16 filas al final, con `fid` vacío por ausencia en la fuente. SHA-256 anterior `1f5fef5fe11f05723957883986057cb824d6a9048213ef7227d3e3ac33514c03`; nuevo `c6e3d589dd06112e98f408ebb697b2d6190b427eeb66d3ce1de289fe33a52002`. Se conservaron los IDs, metadata, checksums, fechas y estados de todas las entidades anteriores de catálogo y las 96 geometrías previas. Las líneas 6 y 90 conservan sus filas: se comprobó que no tenían viajes, avances ni eventos, pero no se eliminaron ni se reasignaron a las líneas posteriores.

| Métrica | Antes | Tras importación/rematch, antes de E2E |
|---|---:|---:|
| Líneas | 134 | **135** |
| Ramales | 557 | **565** |
| Recorridos | 1.104 | **1.120** |
| Geometrías | 96 (8,70 %) | **112 (10,00 %)** |
| Recorridos utilizables | 92 (8,33 %) | **108 (9,64 %)** |
| Ambigüedades espaciales pendientes | 44 | **56** |
| Ocurrencias activas de paradas oficiales | 4.363 | **4.966** |
| Paradas físicas oficiales | 6.989 | **6.989** |
| Features del GeoJSON sin match | 16 | **0** |
| Viajes | 41 | **41** |
| Avances | 138 | **138** |
| Eventos | 144 | **144** |
| Puntos | 188 | **188** |

El aumento de ambigüedades corresponde a **12 casos nuevos** entre ramales; las 44 anteriores permanecen. Hay 52 casos entre ramales y 4 de posición crítica. Se conserva la política v2: más candidatos pueden convertir una asociación anterior en incierta, sin forzarla para aumentar cobertura. Las 618 asociaciones creadas corresponden a las variantes nuevas; el aumento neto es 603 porque algunas asociaciones anteriores se retiran de la secuencia activa ante esa nueva incertidumbre. Sus filas y referencias históricas permanecen. Los cuatro recorridos con proyección crítica siguen bloqueados; no quedan flags de rematch pendiente. Los estados finales son 1.008 sin geometría, 63 parciales utilizables, 45 disponibles y 4 ambiguos.

| Variante agregada | Paradas asociadas ida / vuelta | Viajes habilitados |
|---|---:|---|
| `050C` | 44 / 43 | Ambos sentidos |
| `012C` | 37 / 35 | Ambos sentidos |
| `151B` | 75 / 71 | Ambos sentidos |
| `151C` | 33 / 36 | Ambos sentidos |
| `151D` | 13 / 16 | Ambos sentidos |
| `102B` | 30 / 30 | Ambos sentidos |
| `EBUSA` | 22 / 20 | Ambos sentidos |
| `042C` | 55 / 58 | Ambos sentidos |

Estas asociaciones y órdenes son inferencias espaciales sobre Points oficiales, no pertenencias a ramales publicadas por BA Data. Se verificaron cero duplicados activos parada/recorrido, orden contiguo desde 1, posición acumulada monótona y evidencia presente en las 4.966 ocurrencias. Hay 3.718 asociaciones aceptadas por corredor compartido, correspondientes a 1.594 casos parada/línea/sentido y 1.517 paradas físicas distintas.

### Ejecuciones y preservación comprobadas

Se guardó `backups/catalogue-extension-20261106/before.dump` antes de importar. Se compararon huellas de todas las filas y campos del historial y de los extremos físicos de viajes. Coinciden exactamente **44 usuarios, 41 viajes, 138 avances, 144 eventos, 40 logros obtenidos, 1 seguimiento y 188 puntos**. También coinciden identidad, metadata y fechas del catálogo anterior y la identidad física de las 7.191 paradas totales (6.989 oficiales y 202 ilustrativas).

- CSV: dry-run simulado 82 con rollback íntegro; ejecución persistente **83 SUCCESS**, 16 altas, 0 actualizaciones, 1.104 omitidos y 0 errores.
- Geometrías: recurso directo predeterminado, mismo SHA-256 `405e3f1aebc4c3dbca56547fa8595a71cbc5c1906566b60d62aeeb056ec0054f`, 112 features. Dry-run simulado 84 con rollback íntegro; ejecución **85 SUCCESS**, 112 matches exactos, 0 secundarios, 0 sin match, 16 geometrías nuevas, 0 actualizadas y 96 idénticas.
- Rematch: dry-run simulado 86 anticipó exactamente la cobertura persistida y conservó las huellas completas, incluida metadata, incidencias y auditoría. Ejecución **87 SUCCESS en 86,14 s**, sin descargar ni crear paradas: 618 asociaciones creadas, 534 actualizadas y recuperación de servicios eBUS en **42 paradas existentes**. Se preservaron Point, clave física, dirección y demás datos de cada parada; el único enriquecimiento de servicios procede de su `origen` conservado y se une a la lista consolidada anterior.
- Repetición: CSV **88 UNCHANGED** y geometrías **89 UNCHANGED**, sin altas ni actualizaciones. Rematch **90 SUCCESS**, con 0 asociaciones creadas/actualizadas y 0 servicios recuperados de nuevo. Se conservaron exactamente las filas de RecorridoParada, incluidos PK, parada, orden, posición, fuente y evidencia, además de catálogo, metadata semántica e historial. La revisión de ilustrativas legacy puede actualizar sus timestamps; la auditoría de cada ejecución se conserva por separado.

`Linea.numero` continúa siendo un string de hasta cinco caracteres y admite `EBUS`, con normalización ASCII estable. No se alteran PK, URLs, tipos de API ni se necesita una migración de esquema. La búsqueda `ebus`, filtros por PK, ordenación mixta, badges, viajes y progreso se verificaron tanto en tests como contra la aplicación. El servicio usa colores fallback; no se inventó una paleta de operador. El GeoJSON sólo cubre su base publicada y no se fabricaron trazados para las extensiones especiales.

### Pruebas y aplicación final

- **140 pruebas backend de la suite completa aprobadas en 230,376 s** sobre PostGIS aislado. Incluyen altas, rechazo de aliases cuando falta una fila CSV, 16 identidades reales, idempotencia, normalización alfanumérica, búsqueda/orden/filtros/API, viaje/progreso eBUS, recuperación de servicios consolidados, dry-run, rematch y preservación histórica.
- Tras añadir las fixtures de CI se aprobó **1 prueba de integración offline adicional en 33,384 s**: bootstrap, 16 geometrías oficiales nuevas y 180 features oficiales de línea 4/eBUS, dando 40 geometrías y eBUS utilizable. Un nuevo bootstrap conserva todas las secuencias, y no crea usuarios, viajes ni eventos. **141 pruebas backend verificadas** entre suite completa e integración adicional; no se ejecutaron contra la base de la aplicación.
- Frontend final: **20 pruebas aprobadas**, TypeScript y ESLint correctos. Se corrigió el recorte del badge EBUS detectado por E2E móvil y se mantuvo la comprobación de que el texto completo cabe, esperando las fuentes reales.
- **12 de 12 E2E aprobados en la imagen final, salida 0, en aproximadamente 1,4 minutos**: las ocho variantes por API, búsqueda `ebus`, badges completos y mapa en claro/oscuro, viaje real/progreso eBUS, viaje numérico, bloqueos y pantallas generales en desktop/móvil. Se renovaron **56 capturas**: 48 generales, 2 de selección y 6 de eBUS, en `frontend/test-results/`. Se inspeccionaron visualmente eBUS móvil y el mapa/lista de progreso en desktop.
- Migraciones: `makemigrations --check --dry-run`, sin cambios. OpenAPI: `spectacular --validate --fail-on-warn`, salida 0.
- Las imágenes backend/frontend se construyeron; backend, frontend, PostgreSQL y Nginx quedaron saludables. `/health/` confirmó PostGIS y la búsqueda eBUS vía Nginx respondió HTTP 200. La aplicación quedó ejecutándose localmente en `http://localhost:8080`. No se hicieron commits.

Los E2E de las dos ejecuciones crearon **12 usuarios y 12 viajes de prueba**, con 36 avances/eventos/puntos nuevos y 12 logros obtenidos, todos de esas cuentas. Los totales de desarrollo posteriores son **56 usuarios, 53 viajes, 174 avances, 180 eventos, 224 puntos, 52 logros obtenidos y 1 seguimiento**. Se filtró por los IDs de todas las filas preexistentes y se volvió a comparar cada campo después de E2E: **sus huellas siguen siendo idénticas**. Las altas de prueba no provienen de importaciones ni recalculan puntos históricos.

`data/recorridos.reconciliation.json` conserva evidencia previa, fuentes revalidadas, filas añadidas y resultado por variante, con cero aliases y cero features pendientes de estas 16. Los backups, snapshots, logs y comprobaciones de esta fase están en `backups/catalogue-extension-20261106/`, ignorados por Git. Quedan 1.008 trazados ausentes, 56 incidencias de asociación y las extensiones de eBUS sin cartografía/identidad suficiente; [Pendientes](pending.md) conserva esos límites. No se afirma cobertura completa de CABA ni del AMBA.
