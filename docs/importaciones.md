# Importaciones

BA Data alimenta una base propia; la navegación consulta los datos ya importados. Cada comando deja `DataSource`, `ImportRun` y errores consultables en el admin. Las importaciones de catálogo, geometrías y secuencias comparten un bloqueo de PostgreSQL que las excluye del registro concurrente de viajes. Los errores de feature se registran y permiten seguir con las demás; un fallo inesperado revierte la fase completa. Una fuente vacía nunca implica borrar el catálogo. Los modos `--dry-run` revierten también los registros de auditoría después de obtener el resumen.

## Recorridos

El catálogo principal es **`data/recorrido-colectivos.csv`**, provisto en el repositorio: **135 líneas, 565 ramales y 1.120 sentidos/recorridos**. El arranque de desarrollo y el comando sin argumentos lo usan por defecto. No se descarga otra fuente para decidir qué líneas o ramales existen.

```sh
docker compose exec backend python manage.py import_badata_recorridos
docker compose exec backend python manage.py import_badata_recorridos --file /data/recorrido-colectivos.csv
docker compose exec backend python manage.py import_badata_recorridos --geojson --dry-run
docker compose exec backend python manage.py import_badata_recorridos --geojson
docker compose exec backend python manage.py import_badata_paradas --rematch --dry-run
docker compose exec backend python manage.py import_badata_paradas --rematch
docker compose exec backend python manage.py import_badata_recorridos --file /data/recorridos.geojson
docker compose exec backend python manage.py import_badata_recorridos --url https://proveedor.example/recorridos.geojson
```

`BADATA_RECORRIDOS_FILE` permite cambiar el archivo predeterminado (`/data/recorrido-colectivos.csv` en Docker). `--file` y `--url` tienen prioridad. El formato se deduce de la extensión; `--format csv|geojson` permite indicarlo explícitamente para URLs sin extensión. El CSV acepta UTF-8, BOM, campos entre comillas y cabeceras únicas; requiere `linea`, `recorrido`, `sentido`, `l_r_s`. Conserva además `fid`, `modalidad`, `jurisdicci`, `camara`, `desde` y `hasta`. Normaliza el número y valida que `l_r_s` corresponda a línea + ramal + sentido, preservando nombres como `F-variante` o `C NUEVO`.

El CSV **no incluye geometrías ni paradas**. Se crean recorridos con `geometria=null`, sin inventar trazados, secuencias ni completitud. La API y la interfaz permiten explorarlos y muestran que faltan el trazado o las paradas; no se puede registrar un viaje sin una secuencia válida. El JSON actual de colores coincide con 102 de sus 135 líneas; las otras 33 usan fallback.

### Geometrías complementarias

`--geojson` y `--format geojson` son equivalentes. Sin archivo/URL usan `BA_DATA_RECORRIDOS_GEOJSON_URL`, cuyo valor predeterminado es el [GeoJSON oficial de recorridos](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-recorridos/recorrido-colectivos.geojson). La variable anterior `BADATA_RECORRIDOS_URL` permanece como fallback compatible; la nueva tiene prioridad. `--file` o `--url` permiten sobrescribir la ubicación. El comando sin esos flags sigue importando el CSV.

Esta fase **sólo enriquece recorridos CSV ya existentes**: no crea líneas, ramales ni un catálogo paralelo. Primero busca `l_r_s` exacto y después su representación normalizada, respetando la semántica del ramal y el sentido. Normaliza espacios, mayúsculas y ceros del número de línea; si no hay identificador compatible, intenta línea + ramal + sentido normalizados. Un identificador que contradice los atributos, varios candidatos o features distintas para el mismo recorrido generan incidencias. Los casos sin correspondencia quedan trazados con candidatos para revisión; no incorporan recorridos nuevos.

Se validan FeatureCollection no vacía, propiedades, WGS84 y geometrías 2D LineString/MultiLineString. LineString se convierte a MultiLineString. Se conservan todos los componentes y coordenadas en el orden publicado, sin simplificar ni invertir. Una geometría idéntica no escribe; una geometría válida diferente actualiza sólo `geometria`, `geometria_source`, estado de rematch y fecha. No modifica metadata, identidad, checksum ni prioridad CSV. Una feature sin geometría válida queda como error y conserva el trazado anterior; la ausencia de una feature no elimina geometrías.

Cada alta o cambio de geometría marca `requiere_rematch=True`. Hasta ejecutar explícitamente el rematch, la API oculta las secuencias anteriores y bloquea los viajes nuevos de ese recorrido para evitar usar proyecciones obsoletas. Los viajes e IDs históricos permanecen. La importación de trazados no ejecuta asociaciones automáticamente. `import_badata_paradas --rematch --dry-run` anticipa el efecto; `--rematch` aplica la fase y limpia el estado pendiente sólo al finalizar correctamente. Una ambigüedad crítica de posición sigue impidiendo viajes aunque se haya reprocesado.

Los tipos de importación tienen checksums independientes: `catalogo_csv`, `geometrias` y `geometrias_muestra`. El último corresponde a `--only-missing`, utilizado por el bootstrap para cargar trazados offline únicamente donde falta geometría. Reiniciar el entorno no reemplaza una geometría productiva con la muestra ni cambia el checksum de la fase oficial. La comparación de geometrías incluye la firma del catálogo; ampliar el CSV obliga a evaluar de nuevo una fuente ya descargada. `--force` fuerza evaluación y `--dry-run` valida y calcula métricas sin persistir. Volver de una revisión B a una revisión A aplica A otra vez; una versión con errores se puede reintentar.

`ImportRun.metrics` registra features, matches exactos y secundarios, casos sin match/conflictos, geometrías nuevas/actualizadas/sin cambios, huellas anterior y nueva por cambio, cobertura y duración. Los archivos y URLs quedan en `location`; los casos no resueltos o inválidos se guardan en `ImportError`. La descarga observada el **6 de noviembre de 2026** contiene **112 features MultiLineString**, cada una con un componente, y referencias a 26 denominaciones de línea, incluida `EBUS`. No trae `fid` en esta revisión. La revisión inicial frente al CSV de 1.104 recorridos dio **96 correspondencias exactas** y **16 sin fila de catálogo**; tras la ampliación documentada de esta sección las 112 features coinciden con el CSV de 1.120 recorridos. Tamaño: **655.234 bytes**; SHA-256 `405e3f1aebc4c3dbca56547fa8595a71cbc5c1906566b60d62aeeb056ec0054f`.

Atribución de trazados: GCBA / BA Data, **“Colectivos: recorridos”**, bajo [CC BY 2.5 AR](https://creativecommons.org/licenses/by/2.5/ar/), según la [metadata oficial](https://data.buenosaires.gob.ar/dataset/colectivos-recorridos), cuya fecha publicada de actualización es **21 de septiembre de 2026**. El alcance real queda limitado a las features publicadas y sus coincidencias con el CSV.

La transición desde el bootstrap anterior promueve solamente recorridos de `badata-muestra` con el mismo `l_r_s`, ramal y sentido a `badata`. Conserva sus IDs, geometrías, secuencias, viajes, avances y eventos. Las fuentes ajenas o cambios de identidad generan un error para revisión. La migración conserva el origen de las geometrías existentes. Para revertir la nulabilidad, primero deben existir trazados para todos los recorridos; el rollback no elimina entradas CSV automáticamente.

### Revisión previa de los 16 identificadores sin match — 6/11/2026

Esta revisión tuvo alcance de equivalencias, anterior a la autorización para ampliar el catálogo. Se compararon los cuatro campos reales `linea`, `recorrido`, `sentido` y `l_r_s` de cada feature con las 1.104 filas originales del CSV. **Los 16 identificadores son internamente consistentes; ninguno se resuelve por espacios, mayúsculas, ceros iniciales o normalización de sentido.** Catorce corresponden a siete ramales que no existen en el CSV; los otros dos pertenecen a una línea eBUS ausente y no numérica. El CSV contiene 50 A/B, 12 A/B, 151 A, 102 A y 42 A/B. Conserva además las identidades históricas 6 A/B/C/D y 90 A/B, que no se pueden sustituir por recorridos posteriores de otras líneas.

| Prefijo GeoJSON, ida/vuelta | Comparación y causa comprobada | Decisión de identidad |
|---|---|---|
| `050C` | Correo Central–Terminal Dellepiane. La [fusión oficial 6/50](https://buenosaires.gob.ar/gcaba_historico/infraestructura/fusion-de-las-lineas-50-y-6-de-colectivos-conoce-los-nuevos-recorridos) incorpora C con cambios de calles y cabeceras; el CSV sólo tiene 50 A/B y recorridos anteriores de la 6. | Alta de ramal documentada, sin equivalencia con un recorrido CSV existente. |
| `012C` | Puente Pueyrredón–Plaza Falucho, **por Centro Metropolitano de Diseño**. El [anexo de la Resolución 3-SECT/26](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MIGC-SECT-3-26-ANX.pdf) distingue A, B y C. A comparte cabeceras con C pero no itinerario, en ambos sentidos. | Variante distinta; no alias de `012A` ni `012B`. |
| `151B` | Barrio 21-24–Vicente López. El [anexo de la reforma 132-SECT/25](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MIGC-SECT-132-25-ANX.pdf) distingue B de A. El CSV sólo tiene 151 A; las cabeceras de 90 A/B son Constitución–Villa Devoto/Lacroze. | Fusión/reorganización con cambios de itinerario; no identidad con 151 A ni 90 A/B. |
| `151C` | Constitución–Concepción Arenal y Álvarez Thomas, frente a 151 A hasta Vicente López. El [foro previo 118-SECT/25](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MIGC-SECT-118-25-ANX.pdf) describe el renombre de un antiguo 151 B a C; el [anexo aprobado 132-SECT/25](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MIGC-SECT-132-25-ANX.pdf) publica C como recorrido separado. **Ese antiguo B tampoco está en el CSV.** | Renombre documentado sin identidad de origen disponible en este catálogo; no alias de 151 A. |
| `151D` | Constitución–Plaza Miserere. La reforma anterior lo propone como nuevo fraccionamiento y el anexo aprobado lo enumera por separado. | Fraccionamiento ausente; no se reemplaza el trazado completo de 151 A por su tramo corto. |
| `102B` | Lisandro de la Torre–Constitución, publicado como B por [GCBA](https://buenosaires.gob.ar/gcaba_historico/linea-102). El CSV sólo contiene A, Palermo Chico–Barracas. El GeoJSON también actualiza la denominación de cabecera de A a Lisandro de la Torre, pero mantiene A hasta Barracas. | Servicio corto distinto de A; su existencia está documentada, su fecha de alta no se determinó en esta revisión. |
| `EBUSA` | `linea=EBUS`, `recorrido=A`, Lezama–Terminal de Cruceros. [GCBA documenta ese servicio](https://buenosaires.gob.ar/gcaba_historico/recorrido-del-bus-electrico). No existe línea EBUS en el CSV y `normalize_line`/Linea requieren números positivos. | Servicio ausente y tipo de identidad incompatible con el modelo actual. No convertir a 0 ni a otra línea. |
| `042C` | Nueva Pompeya–Parque de los Niños por Barrio Espora, mientras el CSV sólo incluye A/B hasta Ciudad Universitaria. El [anexo 4-SECT/26](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MIGC-SECT-4-26-ANX.pdf) distingue los tres recorridos. | Extensión/variante ausente, sin equivalencia con A/B. |

Las [aclaraciones oficiales de parámetros](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/indicadores-colectivos/aclaraciones_parametros_colectivos.pdf) corroboran las reformas 6/50, 12, 42 y 90/151 y la operación de eBUS desde el 7/5/2025. Esto explica diferencias entre revisiones de las fuentes; no prueba por sí solo la identidad de un recorrido histórico. No se atribuye una fecha de publicación al CSV que el archivo no contiene.

Se compararon también las geometrías del GeoJSON con las de sus candidatos de igual línea/sentido en EPSG:32721: **ninguna de las 14 features numéricas es geométricamente igual a A/B existentes**. La geometría sirve para descartar duplicados, no para autorizar un renombre. `elr_sube` tampoco es clave de ramal: 151 A/B comparten `8_47_69`, y 102 A/B comparten `2_156_8902`.

El registro versionado [recorridos.reconciliation.json](../data/recorridos.reconciliation.json) conserva las 16 propiedades reales, identidades normalizadas, filas CSV de comparación, huellas de geometría, medidas UTM, fuentes y causa individual. **Es evidencia de revisión, no una tabla de aliases consumida por el importador.** La fase previa concluyó con cero equivalencias aprobadas y 16 features pendientes de revisar el catálogo; sus incidencias originales siguen en `ImportError` como auditoría histórica. La ampliación autorizada posterior se detalla debajo y actualiza el estado del registro sin convertirlo en una tabla de aliases.

### Ampliación autorizada del catálogo — 6/11/2026

Una nueva solicitud autorizó incorporar variantes verificadas como identidades propias y dar soporte a eBUS. Se revalidaron las fuentes anteriores, la publicación vigente del GeoJSON (mismo hash), la [Resolución 221-SECT/26 de la línea 102](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/882357), su [anexo del 13/10/2026](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MMIGC-SECT-221-26-ANX.pdf), la [revisión 106-SECT/26 de la línea 42](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MMIGC-SECT-106-26-ANX.pdf) y la [publicación GCBA de septiembre de 2026 sobre eBUS](https://buenosaires.gob.ar/gcaba_historico/noticias/el-bus-electrico-extiende-su-recorrido-y-ahora-llega-caminito). Se priorizaron normas aprobadas; el foro de 151 sólo describe antecedentes, no autoriza por sí solo las altas.

| Variante, ambos sentidos | Estado final de catálogo | Identidad y alcance verificados |
|---|---|---|
| `050C` | Agregado | Correo Central–Terminal Dellepiane, por la fusión 6/50 documentada por GCBA. Se conservan 6 A/B/C/D y 50 A/B. |
| `012C` | Agregado | Variante por Centro Metropolitano de Diseño, distinta de 12 A/B según Resolución 3-SECT/26. |
| `151B` | Agregado | Barrio 21-24–Vicente López según anexo aprobado 132-SECT/25; se conservan 90 A/B y 151 A. |
| `151C` | Agregado | Constitución–Concepción Arenal y Álvarez Thomas según el mismo anexo; no se simula un renombre de una fila inexistente del CSV. |
| `151D` | Agregado | Fraccionamiento Constitución–Plaza Miserere previsto separadamente en el anexo aprobado. |
| `102B` | Agregado | Lisandro de la Torre–Constitución, confirmado por 221-SECT/26. El anexo limita su operación a lunes a viernes 6–20 y sábados 6–14; no implica disponibilidad horaria permanente. |
| `EBUSA` | Agregado | Servicio eBUS y base Lezama–Terminal de Cruceros publicada por BA Data. Las extensiones a Usina/Caminito y sus días de operación no se inventan como geometrías o ramales adicionales. |
| `042C` | Agregado | Nueva Pompeya–Parque de los Niños por Barrio Espora; anexo 4-SECT/26 y revisión 106-SECT/26 mantienen su identidad separada de A/B. |

Se añadieron **16 filas** al final del CSV, conservando byte por byte las 1.104 originales. No se renombraron ni borraron entidades. `fid` queda vacío en las altas porque el recurso no lo publica; `l_r_s` conserva el valor oficial, y cabeceras, modalidad, jurisdicción y cámara proceden de sus propiedades verificadas. El catálogo pasa a 135 líneas, 565 ramales y 1.120 recorridos. La línea eBUS y los ocho ramales se crean exclusivamente al importar esas filas CSV; la fase GeoJSON sigue sin crear catálogo. Las líneas 6 y 90 no tenían viajes, avances ni eventos en la base auditada, pero se conservaron igualmente sus identidades y estado anterior.

`Linea.numero` ya era un `CharField(max_length=5)`, por lo que **no hace falta migrar el esquema ni renumerar PK**. `normalize_line` ahora acepta identificadores ASCII alfanuméricos de 1 a 5 caracteres: recorta espacios externos, mantiene números positivos sin ceros iniciales y convierte códigos con letras a mayúsculas, sin eliminar sus dígitos. `060` → `60`, `eBus` → `EBUS`, `A0001` → `A0001`. Rechaza booleanos, nulos, espacios internos, signos, caracteres no ASCII y valores demasiado largos. El CSV exige prefijo numérico de tres dígitos o código alfanumérico intacto: `012CIDA` / `EBUSAIDA`.

La API conserva `numero`/`linea_numero` como strings y URLs/filtros por PK. Ordena primero números por valor, luego códigos alfanuméricos en orden léxico; buscar `ebus` encuentra EBUS sin distinguir mayúsculas. Badges, mapa, progreso, viajes y rankings mantienen ese código, con paleta fallback al no existir colores verificados para eBUS.

El rematch recupera servicios ahora reconocidos desde `Parada.metadata.origen` preservado, sin descargar ni mover Points. **Une** los servicios recuperados con `metadata.lineas`; no reemplaza la lista por la de una única fila original, porque una parada consolidada puede contener otras líneas/sentidos. Verifica que la identidad física derivada siga siendo la misma, actualiza sólo metadata/fecha de las paradas afectadas y deja intactos viajes, avances y ledger. El dry-run revierte también esa recuperación y repetirlo sin cambios no escribe nuevamente. La evidencia de corredor, los umbrales y el bloqueo de proyecciones críticas conservan la política v2.

Los resultados persistidos, huellas y pruebas de esta ampliación se registran en [Verificación](verificacion.md). La incorporación al catálogo no equivale a afirmar cobertura completa o vigencia operativa permanente de todos los servicios históricos conservados.

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

Con un único candidato y una proyección inequívoca se crea la asociación. Con varios recorridos plausibles de la misma línea/sentido se evalúa **evidencia de corredor compartido**, en lugar de decidir por una diferencia entre sus distancias. Todos los pares de candidatos deben coincidir en una ventana longitudinal orientada alrededor de sus proyecciones:

| Configuración | Default | Evidencia que controla |
|---|---:|---|
| `PARADA_SHARED_CORRIDOR_WINDOW_METERS` | 60 m | Máximo hacia atrás y hacia adelante desde cada proyección |
| `PARADA_SHARED_CORRIDOR_TOLERANCE_METERS` | 12 m | Separación máxima entre muestras alineadas de los trazados |
| `PARADA_SHARED_CORRIDOR_MAX_ANGLE_DEGREES` | 20° | Diferencia máxima de orientación entre intervalos sucesivos |
| `PARADA_SHARED_CORRIDOR_MIN_SUPPORT_METERS` | 90 m | Longitud común mínima para aceptar evidencia |
| `PARADA_SHARED_CORRIDOR_SAMPLE_STEP_METERS` | 15 m | Espaciado máximo entre muestras de la ventana |

Una coincidencia puntual, una calle paralela, un cruce, una orientación invertida o un tramo demasiado corto no prueban que se comparta corredor. Si todos los pares cumplen, se asocia la parada a cada ramal con su propia posición y orden. Si dos candidatos comparten y un tercero cercano diverge, el caso completo continúa ambiguo. El parámetro histórico `PARADA_MATCH_MIN_MARGIN_METERS` queda por compatibilidad de configuración y no decide la asociación en la política v2.

Las ventanas usan trazados UTM guardados en caché por recorrido durante la ejecución. Se respetan componentes y coordenadas; una discontinuidad mayor de 1 m separa la ventana, evitando inventar una unión. El prefiltrado SQL por línea/sentido y GIS evita comparar cada parada con todos los recorridos; la comparación por pares se limita a sus candidatos plausibles. Los umbrales documentan una inferencia conservadora y configurable, no una certificación oficial de pertenencia al ramal.

La proyección utiliza **EPSG:32721** (UTM 21S para Buenos Aires). Para MultiLineString se recorren todos los componentes en su orden almacenado y se acumula su longitud sobre geography antes de sumar la fracción proyectada del componente elegido. La secuencia sigue esa distancia acumulada, con desempate reproducible, y no la latitud, longitud ni distancia recta a la cabecera. Si dos segmentos, incluso dentro de un mismo componente, ofrecen distancias laterales dentro de 1 m pero posiciones acumuladas separadas por más de 10 m, la proyección queda ambigua y no se asigna una ocurrencia arbitraria.

`RecorridoParada` conserva el método y fuente de asociación, distancia lateral, posición acumulada, estado activo y `evidencia` JSON. Esta última registra política `single_candidate`/`shared_corridor`, confianza geométrica, parámetros, candidatos y las comparaciones cuantitativas. Se audita en administración sin exponer detalles técnicos innecesarios en la interfaz pública. Se mantiene la unicidad de orden por recorrido y se impiden duplicados de asociaciones espaciales activas. Las ocurrencias históricas siguen identificadas por su PK; las muestras circulares pueden conservar repeticiones físicas que ya existían.

### Historial, cobertura y reimportación

El comando no adjudica puntos ni recalcula bonus. Las paradas ilustrativas sin equivalencia concluyente se conservan como legacy. La reconciliación exige una correspondencia recíproca, cercana y compatible dentro del mismo recorrido (`PARADA_RECONCILE_MAX_DISTANCE_METERS`, **10 m** por defecto). Cuando la ilustrativa carece de uso histórico, puede reutilizar su ocurrencia manteniendo la PK y sin eliminar la parada anterior.

Cuando existen referencias desde viajes, progreso o eventos, se mantienen **exactamente** las filas de `RegistroViaje`, `UsuarioLineaParada` y `EventoPuntos`, y la identidad de parada de las ocurrencias históricas. Una equivalencia inequívoca se guarda únicamente como alias `Parada.metadata.official_equivalences[numero_linea] = id_parada_oficial`. No se reasignan endpoints ni se fusionan avances históricos. Los conflictos de identidad conservan el caso sin una equivalencia nueva. `legacy_history_preserved` permite auditar estas decisiones.

El cálculo de visitas resuelve esos alias para reflejar el progreso sobre el catálogo actual. Al registrar viajes futuros, Django reconoce que la parada equivalente ya fue transitada y evita volver a otorgar su punto; el avance histórico original y su evento siguen intactos. Los recorridos y secuencias pueden ampliar el denominador de progreso actual, pero no revocan ni recalculan premios del pasado. Las ilustrativas permanecen excluidas de nuevas altas de viajes.

Los viajes nuevos requieren geometría válida, al menos dos paradas oficiales activas ordenadas, ausencia de un rematch pendiente y ausencia de ambigüedad crítica de proyección. Una ambigüedad entre ramales puede coexistir con una secuencia parcial de otras paradas confiables: esa secuencia sigue utilizable sin afirmar completitud de toda la línea. Las métricas de recorridos utilizables y la API comparten el criterio de calidad. Una cobertura parcial de CABA no equivale a cubrir todo el AMBA.

Cada ejecución registra `DataSource` (`badata-paradas` por defecto; `--source` permite otro namespace), `ImportRun`, URL/archivo, checksum, fechas, métricas y problemas revisables en admin. Los fallos de feature se guardan en `ImportError`; las decisiones de matching en `StopMatchIssue`, con parada, línea/sentido, motivo, candidatos, distancias y estado pendiente/resuelto. Un rematch cierra las decisiones previas y crea la evidencia vigente, conservando la auditoría anterior. Las métricas incluyen paradas leídas/creadas/actualizadas, líneas reconocidas, falta de candidatos/geometrías, asociaciones creadas/actualizadas/ambiguas, casos y asociaciones de corredor compartido, reconciliadas y legacy conservadas. Estas últimas métricas de reconciliación se cuentan por ocurrencia de recorrido, no como paradas físicas únicas. Los porcentajes separan recorridos con geometría, con alguna parada oficial y con secuencia utilizable. El checksum evita importar otra vez una versión ya aplicada, salvo `--force`; `--rematch` recalcula asociaciones aunque las paradas no cambien. `--dry-run` revierte **toda** la transacción, incluyendo fuente, ejecuciones y errores, después de obtener el resumen.

### Atribución y alcance

Fuente: **BA Data / Gobierno de la Ciudad de Buenos Aires, “Colectivos: paradas”**, Secretaría de Transporte y Obras Públicas, Jefatura de Gabinete de Ministros. La [metadata oficial](https://data.buenosaires.gob.ar/dataset/colectivos-paradas), consultada el **30 de octubre de 2026**, publica licencia [CC BY 2.5 AR](https://creativecommons.org/licenses/by/2.5/ar/), actualización del **21 de septiembre de 2026** y frecuencia semestral. El recurso describe ubicaciones de la Ciudad de Buenos Aires; no se afirma cobertura total del AMBA. Bondiala normaliza y consolida registros, y deriva asociaciones y orden espaciales; estas derivaciones no son relaciones ramal/parada publicadas por la fuente.

La descarga auditada contiene **7.027 features**, **2.814.529 bytes**, SHA-256 `9f56e90159ac44f8217dd7ff0a27a85c2565b6516f60811832978bd83af04d1c`. Tiene 131 números de línea presentes en el CSV y la denominación no reconocida `eBUS`. Los conteos efectivos de paradas y cobertura tras normalización están en [Verificación](verificacion.md).

### Fuentes locales de desarrollo

`data/paradas.official.sample.geojson` contiene 138 features reales seleccionadas por su referencia a la línea 4, sin alterar geometrías ni propiedades. Se usa en CI y E2E para validar viajes sobre datos oficiales sin conexión al CDN. Conserva el esquema oficial y se importa con `--file /data/paradas.official.sample.geojson --match-routes`. Las líneas adicionales publicadas en cada feature se mantienen, aunque sus trazados no estén en la muestra. Su procedencia y licencia se documentan en [data/README.md](../data/README.md).

### Formato normalizado ilustrativo

Se conserva `--format normalized` para los archivos locales con `id`, `nombre`, Point y `recorridos: [{l_r_s, source, orden}]`; `--format auto` reconoce el esquema. `bootstrap` lo usa para las muestras, manteniéndolas como ilustrativas. Una relación explícita de una muestra no certifica una parada oficial. Las referencias a recorridos usan el namespace `badata`; las paradas de muestra usan `muestra-paradas`. No se deben presentar como datos oficiales ni habilitar viajes nuevos sobre ellas.

## Descargas y entradas externas

La descarga tiene un plazo total configurable `IMPORT_TIMEOUT` (**45 s**), límite `IMPORT_MAX_BYTES` (**150 MiB**) y máximo `IMPORT_MAX_FEATURES` (**100.000 features**). Se revisan tamaño declarado y recibido, JSON/CSV y MIME compatible; una respuesta HTML se rechaza. Se permiten hasta tres redirecciones, revalidando cada destino, y no se utilizan proxies heredados del entorno.

Las URLs deben ser HTTP(S), sin credenciales ni fragmentos, con puerto estándar. Se rechaza cualquier resolución DNS local, privada o reservada. Con `DEBUG=False` se exige HTTPS y un hostname incluido en `IMPORT_ALLOWED_HOSTS`, cuyo default es `cdn.buenosaires.gob.ar`. En desarrollo se admiten otros hosts públicos para archivos de prueba; agregar un host productivo es una decisión de operación explícita. `--file` admite archivos locales dentro del contexto autorizado del operador. Estas opciones son management commands, no un endpoint público de descarga arbitraria.

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
