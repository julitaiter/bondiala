# Importaciones

BA Data alimenta una base propia; la navegación no consulta sus servicios en tiempo real. Cada comando deja `DataSource`, `ImportRun` y errores consultables en el admin. La descarga tiene timeout, límite de tamaño y checksum; los registros inválidos se aíslan en transacciones por feature. Las importaciones de una misma fuente/tipo se serializan mediante un advisory lock de PostgreSQL.

## Recorridos

El catálogo principal es **`data/recorrido-colectivos.csv`**, provisto en el repositorio: **134 líneas, 557 ramales y 1.104 sentidos/recorridos**. El arranque de desarrollo y el comando sin argumentos lo usan por defecto. No se descarga otra fuente para decidir qué líneas o ramales existen.

```sh
docker compose exec backend python manage.py import_badata_recorridos
docker compose exec backend python manage.py import_badata_recorridos --file /data/recorrido-colectivos.csv
docker compose exec backend python manage.py import_badata_recorridos --format geojson
docker compose exec backend python manage.py import_badata_recorridos --file /data/recorridos.geojson
docker compose exec backend python manage.py import_badata_recorridos --url https://proveedor.example/recorridos.geojson
```

`BADATA_RECORRIDOS_FILE` permite cambiar el archivo predeterminado (`/data/recorrido-colectivos.csv` en Docker). `--file` y `--url` tienen prioridad. El formato se deduce de la extensión; `--format csv|geojson` permite indicarlo explícitamente para URLs sin extensión. El CSV acepta UTF-8, BOM, campos entre comillas y cabeceras únicas; requiere `linea`, `recorrido`, `sentido`, `l_r_s`. Conserva además `fid`, `modalidad`, `jurisdicci`, `camara`, `desde` y `hasta`. Normaliza el número y valida que `l_r_s` corresponda a línea + ramal + sentido, preservando nombres como `F-variante` o `C NUEVO`.

El CSV **no incluye geometrías ni paradas**. Se crean recorridos con `geometria=null`, sin inventar trazados, secuencias ni completitud. La API y la interfaz permiten explorarlos y muestran que faltan el trazado o las paradas; no se puede registrar un viaje sin una secuencia válida. El JSON actual de colores coincide con 102 de sus 134 líneas; las otras 32 usan fallback.

Los GeoJSON quedan como complemento de geometrías, por archivo o URL, usando los mismos `l_r_s` y `--source` (default `badata`). `--format geojson` sin archivo/URL utiliza `BADATA_RECORRIDOS_URL`. Se validan FeatureCollection/WGS84 y geometrías 2D; LineString se convierte en MultiLineString. Si el catálogo del recorrido ya procede de CSV, un GeoJSON actualiza su geometría sin sobrescribir modalidad, jurisdicción, cabeceras ni checksum del catálogo CSV. `geometria_source` identifica el origen del trazado y `catalogue_format` identifica el formato del catálogo. La [fuente GeoJSON oficial](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-recorridos/recorrido-colectivos.geojson) sigue disponible como enriquecimiento opcional; no garantiza cobertura de todas las líneas del CSV.

Si el checksum coincide con la última importación válida del mismo tipo, se registra `UNCHANGED`. CSV (`catalogo_csv`) y geometrías (`recorridos`) tienen comprobaciones independientes y comparten bloqueo para evitar carreras. Volver de una revisión B a una revisión A aplica A de nuevo. `--force` fuerza la evaluación por registro. Una fuente vacía o inválida genera `FAILED` y **no elimina el catálogo**. Tampoco se desactivan automáticamente recorridos ausentes de una nueva fuente.

La transición desde el bootstrap anterior promueve solamente recorridos de `badata-muestra` con el mismo `l_r_s`, ramal y sentido a `badata`. Conserva sus IDs, geometrías, secuencias, viajes, avances y eventos. Las fuentes ajenas o cambios de identidad generan un error para revisión. La migración conserva el origen de las geometrías existentes. Para revertir la nulabilidad, primero deben existir trazados para todos los recorridos; el rollback no elimina entradas CSV automáticamente.

## Paradas oficiales de BA Data

La fuente predeterminada es el **archivo GeoJSON directo** [Paradas de Colectivo](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-paradas/paradas-de-colectivo.geojson). El comando no descarga ni interpreta el HTML de la página. `BA_DATA_PARADAS_GEOJSON_URL` permite configurar otra URL; `--url` y `--file` la sobrescriben.

```sh
# Descargar, validar e incorporar paradas; no asociar recorridos todavía.
docker compose exec backend python manage.py import_badata_paradas
# Evaluar importación y asociaciones sin persistir cambios.
docker compose exec backend python manage.py import_badata_paradas --match-routes --dry-run
# Incorporar paradas y asociar sólo los casos suficientemente concluyentes.
docker compose exec backend python manage.py import_badata_paradas --match-routes
# Recalcular desde las paradas ya almacenadas, sin volver a descargarlas.
docker compose exec backend python manage.py import_badata_paradas --rematch
docker compose exec backend python manage.py import_badata_paradas --file /data/paradas.geojson --match-routes
docker compose exec backend python manage.py import_badata_paradas --url https://proveedor.example/paradas.geojson --dry-run
```

### Esquema real e identidad

Se inspeccionó el recurso real, que contiene `CALLE`, `ALT PLANO`, `DIRECCION`, `COMUNA`, `BARRIO`, `L1`…`L6` y `l1_sen`…`l6_sen`. Las parejas de línea/sentido son filtros de candidatos: **no indican ramal ni orden**. El [diccionario de datos oficial](https://data.buenosaires.gob.ar/sl/dataset/colectivos-paradas/resource/e51cde8e-da46-41b1-87fb-23d656487671) documenta `I` como ida y `V` como vuelta. Se aceptan diferencias de mayúsculas y nombres normalizados; `060` se relaciona con la línea `60`. Un sentido ausente o inesperado se registra y no se convierte por suposición en ida o vuelta.

Las coordenadas se toman del `Point` GeoJSON, no de los campos redundantes `coord_X`/`coord_Y`. Se valida FeatureCollection no vacía, features, propiedades, tipos y longitudes, geometría 2D Point, números finitos y límites WGS84. Una feature inválida queda en `ImportError` sin descartar las demás. Una fuente vacía o inválida no borra paradas, recorridos ni historial.

El GeoJSON inspeccionado **no contiene IDs oficiales**, por lo que no se interpreta un índice de fila como identidad persistente. La clave reproducible combina el Point redondeado a seis decimales con la dirección normalizada; si falta dirección utiliza calle y altura. La normalización Unicode elimina diferencias de acentos, mayúsculas, puntuación y espacios irrelevantes. Se almacena un SHA-256 de esa representación en `external_id`, con el namespace de su `DataSource`. No intervienen el orden de las filas ni las líneas asociadas. Las filas de igual identidad se consolidan y sus parejas línea/sentido se unen: el recurso real tiene duplicados físicos con distintas listas de líneas. No se fusionan puntos próximos sólo por distancia.

`Parada.es_oficial` diferencia el recurso oficial de las muestras, sin sumar un segundo flag contradictorio; `activa` controla su disponibilidad. Fuente, clave y metadata original quedan conservadas para auditoría. Un cambio real de dirección o coordenadas que produzca otra identidad exige revisión; no se elimina automáticamente la parada anterior.

### Asociación y orden espacial

El CSV sigue siendo el catálogo maestro. Las geometrías existentes y sus fuentes se conservan; el importador de paradas no crea líneas, ramales ni trazados a partir de puntos.

Para cada pareja válida línea/sentido se seleccionan recorridos activos con geometría. El prefiltrado espacial y `ST_DWithin` sobre **geography** limitan candidatos en metros; no se interpretan grados de SRID 4326 como metros. El umbral `PARADA_MATCH_MAX_DISTANCE_METERS` vale **60 m** por defecto: tolera desplazamientos de vereda y pequeñas diferencias entre cartografías, y se mantiene configurable para calibrarlo con evidencia. Se audita la distancia calculada. No garantiza que toda parada dentro del umbral pertenezca a ese recorrido.

Con varios ramales plausibles se exige además una separación de al menos **15 m** entre las distancias de los dos mejores candidatos (`PARADA_MATCH_MIN_MARGIN_METERS`). Cuando esa diferencia no existe, el caso queda ambiguo con los candidatos y sus distancias; no se distribuye automáticamente la parada entre todos los ramales superpuestos. Una parada física sí puede tener asociaciones con varias líneas o sentidos cuando cada pareja se resuelve de manera independiente. Los recorridos sin geometría, las líneas desconocidas y los puntos alejados también quedan identificados para revisión.

La proyección utiliza **EPSG:32721** (UTM 21S para Buenos Aires). Para MultiLineString se recorren todos los componentes en su orden almacenado y se acumula su longitud sobre geography antes de sumar la fracción proyectada del componente elegido. La secuencia sigue esa distancia acumulada, con desempate reproducible, y no la latitud, longitud ni distancia recta a la cabecera. Si dos componentes ofrecen distancias laterales dentro de 1 m pero posiciones acumuladas separadas por más de 10 m, la proyección queda ambigua y no se asigna una ocurrencia arbitraria.

`RecorridoParada` conserva el método y fuente de asociación, distancia lateral, posición acumulada y estado activo. Se mantiene la unicidad de orden por recorrido y se impiden duplicados de asociaciones espaciales activas. Las ocurrencias históricas siguen identificadas por su PK; las muestras circulares pueden conservar repeticiones físicas que ya existían.

### Historial, cobertura y reimportación

El comando no adjudica puntos ni recalcula bonus. Las paradas ilustrativas sin equivalencia concluyente se conservan como legacy. La reconciliación exige una correspondencia recíproca, cercana y compatible dentro del mismo recorrido (`PARADA_RECONCILE_MAX_DISTANCE_METERS`, **10 m** por defecto); cuando es segura migra el progreso dentro de transacción, fusiona la combinación usuario/línea/parada si ya existe y preserva las ocurrencias referenciadas por viajes. No crea ni elimina eventos del ledger. Las secuencias legacy dejan de usarse para registrar viajes nuevos cuando se incorpora una secuencia oficial utilizable.

La API conserva el historial y distingue la cobertura actual. Los viajes nuevos requieren al menos dos paradas oficiales activas con una secuencia utilizable. Una cobertura parcial de CABA no equivale a una secuencia completa de todo el AMBA; los recorridos sin datos suficientes muestran un estado explícito y no permiten registrar viajes basados en muestras.

Cada ejecución registra `DataSource` (`badata-paradas` por defecto; `--source` permite otro namespace), `ImportRun`, URL/archivo, checksum, fechas, métricas y problemas revisables en admin. Los fallos de feature se guardan en `ImportError`; las decisiones de matching en `StopMatchIssue`, con parada, línea/sentido, motivo, candidatos, distancias y estado pendiente/resuelto. Un rematch cierra las decisiones previas y crea la evidencia vigente, conservando la auditoría anterior. Las métricas incluyen paradas leídas/creadas/actualizadas, líneas reconocidas, falta de candidatos/geometrías, asociaciones creadas/actualizadas/ambiguas, reconciliadas y legacy conservadas. Los porcentajes separan recorridos con geometría, con alguna parada oficial y con secuencia utilizable. El checksum evita importar otra vez una versión ya aplicada, salvo `--force`; `--rematch` recalcula asociaciones aunque las paradas no cambien. `--dry-run` revierte **toda** la transacción, incluyendo fuente, ejecuciones y errores, después de obtener el resumen.

### Atribución y alcance

Fuente: **BA Data / Gobierno de la Ciudad de Buenos Aires, “Colectivos: paradas”**, Secretaría de Transporte y Obras Públicas, Jefatura de Gabinete de Ministros. La [metadata oficial](https://data.buenosaires.gob.ar/dataset/colectivos-paradas), consultada el **30 de octubre de 2026**, publica licencia [CC BY 2.5 AR](https://creativecommons.org/licenses/by/2.5/ar/), actualización del **21 de septiembre de 2026** y frecuencia semestral. El recurso describe ubicaciones de la Ciudad de Buenos Aires; no se afirma cobertura total del AMBA. Bondiala normaliza y consolida registros, y deriva asociaciones y orden espaciales; estas derivaciones no son relaciones ramal/parada publicadas por la fuente.

La descarga auditada contiene **7.027 features**, **2.814.529 bytes**, SHA-256 `9f56e90159ac44f8217dd7ff0a27a85c2565b6516f60811832978bd83af04d1c`. Tiene 131 números de línea presentes en el CSV y la denominación no reconocida `eBUS`. Los conteos efectivos de paradas y cobertura tras normalización están en [Verificación](verificacion.md).

### Fuentes locales de desarrollo

`data/paradas.official.sample.geojson` contiene 138 features reales seleccionadas por su referencia a la línea 4, sin alterar geometrías ni propiedades. Se usa en CI y E2E para validar viajes sobre datos oficiales sin conexión al CDN. Conserva el esquema oficial y se importa con `--file /data/paradas.official.sample.geojson --match-routes`. Las líneas adicionales publicadas en cada feature se mantienen, aunque sus trazados no estén en la muestra. Su procedencia y licencia se documentan en [data/README.md](../data/README.md).

### Formato normalizado ilustrativo

Se conserva `--format normalized` para los archivos locales con `id`, `nombre`, Point y `recorridos: [{l_r_s, source, orden}]`; `--format auto` reconoce el esquema. `bootstrap` lo usa para las muestras, manteniéndolas como ilustrativas. Una relación explícita de una muestra no certifica una parada oficial. Las referencias a recorridos usan el namespace `badata`; las paradas de muestra usan `muestra-paradas`. No se deben presentar como datos oficiales ni habilitar viajes nuevos sobre ellas.

## Colores

```sh
docker compose exec backend python manage.py import_line_colors /colores_lineas_bondiala.json
```

Normaliza número y hexadecimales, valida las cuatro componentes, reutiliza la paleta completa con unicidad DB y actualiza solo líneas existentes. Informa actualizadas, sin colores, entradas sin línea, paletas únicas y errores. Repetirlo es seguro.

## USIG opcional

`enrich_usig --limit 100 --max-age-days 90` procesa paradas sin enriquecimiento vigente. `USIG_URL` debe apuntar a un endpoint HTTPS que acepte `x`, `y`, `srid=4326` y devuelva JSON plano con alguna de `direccion`, `esquina`, `barrio`, `comuna`. No se fija una URL/contrato oficial que el repositorio no proporciona: si el endpoint real tiene otro formato, interponer un adaptador validado.

Hay timeout, dos retries acotados, límite de respuesta y persistencia con timestamp. El fallo de una parada no bloquea las siguientes ni el uso de Bondiala; los errores quedan en ImportRun. No se consulta en page loads.

## Jobs

Ejemplo semanal, sin Celery/Redis:

```cron
0 4 * * 1 cd /srv/bondiala && /usr/bin/docker compose exec -T backend python manage.py import_badata_recorridos >> /var/log/bondiala-import.log 2>&1
```

En producción usar los dos archivos Compose y alertar ante salida no cero. El checksum evita reprocesar fuentes válidas sin cambios. El comando de paradas admite separar descarga e importación de la asociación espacial. Revisar las métricas y los casos ambiguos antes de automatizar `--match-routes`; `--dry-run` permite anticipar el efecto. Las paradas ilustrativas del namespace `muestra-paradas` se conservan sólo como historial y no habilitan viajes nuevos.
