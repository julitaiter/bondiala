# Catálogo de transporte y muestra local

`recorrido-colectivos.csv` es la fuente principal del catálogo, provista por el usuario y conservada sin modificaciones: **134 líneas, 557 ramales y 1.104 recorridos por sentido**, con `fid`, `linea`, `recorrido`, `sentido`, `l_r_s`, `modalidad`, `jurisdicci`, `camara`, `desde` y `hasta`. No contiene geometrías ni paradas. Se importa por defecto mediante `import_badata_recorridos`; `BADATA_RECORRIDOS_FILE` permite configurar otra ubicación. El JSON de colores cubre 102 de esas líneas.

`recorridos.sample.geojson` conserva 24 features de las líneas 4, 39, 64 y 68 del [GeoJSON oficial de BA Data](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-recorridos/recorrido-colectivos.geojson), descargado el 29 de octubre de 2026. Conserva metadata, identificadores `l_r_s`, geometría y orden de coordenadas. Es un subconjunto para desarrollo; no es un catálogo completo del AMBA.

`paradas.sample.geojson` contiene 202 **paradas ilustrativas**, seleccionadas en 12 vértices distribuidos por cada recorrido. Los nombres e IDs son de muestra. Las coordenadas proceden de los trazados; **no se afirma que sean paradas físicas oficiales**. Las relaciones y el orden son explícitos para probar el importador. Estas secuencias ilustrativas no habilitan viajes nuevos; los tests de viajes usan fixtures aisladas con datos adecuados al caso. Las coincidencias de coordenadas se reutilizan entre recorridos dentro de esta muestra.

`bootstrap` importa primero el CSV en `badata` y luego complementa esos mismos recorridos con las geometrías de muestra por `l_r_s`. Las relaciones de paradas apuntan a los recorridos `badata`, mientras que las paradas ilustrativas mantienen su namespace `muestra-paradas`. No usar esas secuencias como paradas reales en producción. La fuente histórica `badata-muestra` se conserva en el registro de importaciones y se reconcilia sin eliminar viajes ni progreso. No hay credenciales ni usuarios demo en estos archivos.

## Paradas oficiales

La fuente productiva es el [GeoJSON directo “Paradas de Colectivo” de BA Data](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/colectivos-paradas/paradas-de-colectivo.geojson), configurable con `BA_DATA_PARADAS_GEOJSON_URL`. No se incorpora una copia mutable de ese archivo como catálogo maestro versionado. `import_badata_paradas` descarga o acepta un archivo local; `--match-routes` asocia con los trazados existentes y `--dry-run` informa el efecto sin persistir. El CSV de recorridos conserva su prioridad para líneas, ramales, sentidos y metadata.

Auditoría del **30 de octubre de 2026**: 7.027 features Point, 2.814.529 bytes; SHA-256 `9f56e90159ac44f8217dd7ff0a27a85c2565b6516f60811832978bd83af04d1c`. El GeoJSON no publica IDs; se generan claves reproducibles con coordenadas y dirección normalizadas y se unen los servicios de filas duplicadas. El dataset contiene referencias a 131 líneas del CSV y `eBUS`, sin ramales ni orden de paradas explícitos. Las asociaciones espaciales son derivaciones de Bondiala y las ambigüedades se conservan para revisión.

Atribución: **Gobierno de la Ciudad de Buenos Aires / BA Data, “Colectivos: paradas”, Secretaría de Transporte y Obras Públicas, Jefatura de Gabinete de Ministros**, bajo [CC BY 2.5 AR](https://creativecommons.org/licenses/by/2.5/ar/), según la [metadata oficial](https://data.buenosaires.gob.ar/dataset/colectivos-paradas). Se normalizan y consolidan registros y se deriva el orden sobre los trazados; los datos de origen no se presentan como una secuencia oficial por ramal. El recurso describe paradas de la Ciudad de Buenos Aires; no se afirma cobertura total del AMBA. Más detalle en [Importaciones](../docs/importaciones.md) y resultados reales en [Verificación](../docs/verificacion.md).

`paradas.official.sample.geojson` conserva **138 features reales** del recurso anterior que mencionan la línea 4 en alguna de sus parejas `L1`…`L6`. Sólo cambia el formato JSON; las propiedades, coordenadas y referencias a otras líneas permanecen intactas. Es una fixture offline de fuente oficial para CI y E2E, separada de las 202 paradas ilustrativas. Su atribución y licencia son las mismas que las del recurso completo. No representa cobertura total de esa línea ni de CABA.

```sh
docker compose exec backend python manage.py import_badata_paradas --file /data/paradas.official.sample.geojson --match-routes
```
