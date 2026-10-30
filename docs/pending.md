# Dependencias externas pendientes

- Ampliar cobertura fuera del recurso de paradas de BA Data, cuyo alcance declarado es CABA. La integración oficial está implementada; no se afirma cobertura completa del AMBA. Los sentidos ausentes o desconocidos y las líneas fuera del CSV requieren una fuente o revisión adicional.
- Completar geometrías para el catálogo CSV de 134 líneas, 557 ramales y 1.104 recorridos. El CSV define la estructura, pero no los trazados ni las paradas. Los 24 trazados existentes cubren un subconjunto; las 32 líneas sin paleta usan fallback hasta disponer de colores verificados.
- Resolver asociaciones espaciales ambiguas con evidencia adicional de ramal/orden. Los tramos superpuestos no permiten asignar automáticamente una parada a todos los ramales. Las incidencias quedan en el admin; los recorridos sin al menos dos paradas oficiales confiables no habilitan viajes nuevos. Las paradas ilustrativas sin equivalencia inequívoca se conservan como historial legacy.
- Revisar correcciones de dirección/coordenadas y bajas de paradas en futuras versiones de la fuente. Al no existir un ID oficial estable, una identidad nueva no reemplaza silenciosamente a otra anterior y las ausencias no desactivan registros automáticamente. Esa revisión conserva las referencias históricas.
- Validar un endpoint/contrato real de USIG, si se decide usar el enriquecimiento opcional. El comando tiene retries, persistencia, trazabilidad y degradación sin afectar la app.
- Para publicación: registrar/configurar dominio, TLS, proveedor de mapas productivo, SMTP y almacenamiento externo de backups. Son credenciales e infraestructura no suministradas. Verificar entrega de emails y restauración en ese destino.

Las funciones locales, migraciones, suites y construcción de imágenes no dependen de resolver esos puntos. Sus resultados concretos se registran en `docs/verificacion.md`.
