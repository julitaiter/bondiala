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

## Paradas

La documentación original no fija un dataset/URL ni un esquema oficial de relaciones. `BADATA_PARADAS_URL`, `--url` o `--file` son obligatorios. El importador recibe un GeoJSON normalizado con identificadores físicos estables y relaciones explícitas:

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-58.4, -34.6]},
    "properties": {
      "id": "parada-fisica-123",
      "nombre": "Nombre de la parada",
      "direccion": "Dirección opcional",
      "barrio": "Barrio opcional",
      "recorridos": [
        {"l_r_s": "002BIDA", "source": "badata", "orden": 1},
        {"l_r_s": "002CIDA", "source": "badata", "orden": 5}
      ]
    }
  }]
}
```

También admite `l_r_s` y `orden` directamente en `properties` para una sola relación. El namespace físico de paradas es el `--source` del comando; el `source` de cada relación identifica la fuente de su recorrido. Una parada puede repetirse en un recorrido, usando distintos órdenes. No se asocian puntos por cercanía ni se inventa el orden espacial: un caso sin relación, con múltiples recorridos candidatos o un orden ocupado por otra parada se registra como error. Se conserva la ocurrencia referenciada por viajes existentes. Una actualización de secuencias requiere un proceso revisado; el MVP no reemplaza ni elimina secuencias históricas automáticamente.

El adaptador del dataset oficial de paradas queda condicionado a conocer esa fuente y su semántica de IDs/orden. Los archivos `data/*.sample.geojson` muestran el contrato y permiten trabajar sin esa dependencia.

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

En producción usar los dos archivos Compose y alertar ante salida no cero. El checksum evita reprocesar fuentes válidas sin cambios. No programar importación de paradas hasta validar su fuente y relaciones. Las paradas ilustrativas siguen teniendo el namespace `muestra-paradas`; no son paradas oficiales ni deben usarse en producción.
