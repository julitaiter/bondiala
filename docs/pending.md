# Dependencias externas pendientes

- Identificar y validar el dataset oficial de paradas y su relación/orden por recorrido. El importador normalizado está implementado y probado; no hay URL ni semántica de ese dataset en el repositorio. La muestra utiliza paradas ilustrativas y no debe usarse como catálogo productivo.
- Completar geometrías y paradas reales para el catálogo CSV de 134 líneas, 557 ramales y 1.104 recorridos. El CSV ya define la estructura de transporte, pero no incluye esos datos geográficos. Los 24 trazados de desarrollo cubren un subconjunto; las 32 líneas sin paleta usan fallback hasta disponer de colores verificados.
- Validar un endpoint/contrato real de USIG, si se decide usar el enriquecimiento opcional. El comando tiene retries, persistencia, trazabilidad y degradación sin afectar la app.
- Para publicación: registrar/configurar dominio, TLS, proveedor de mapas productivo, SMTP y almacenamiento externo de backups. Son credenciales e infraestructura no suministradas. Verificar entrega de emails y restauración en ese destino.

Las funciones locales, migraciones, suites y construcción de imágenes no dependen de resolver esos puntos. Sus resultados concretos se registran en `docs/verificacion.md`.
