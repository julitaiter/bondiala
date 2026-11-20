# Bondiala

> Una aplicación web para registrar viajes en colectivo y convertir las paradas recorridas en una colección personal.

## Qué es y qué problema resuelve

Bondiala permite registrar líneas, ramales y sentidos utilizados en colectivo y explorar lo que falta recorrer. Está dirigida a personas interesadas en conocer y coleccionar recorridos del AMBA. El usuario selecciona el recorrido y las paradas de subida y bajada; el sistema acredita las paradas intermedias.

El catálogo permite explorar más recorridos de los que pueden registrarse: sólo habilita viajes con trazado y una secuencia oficial utilizable. La fuente de paradas declara alcance CABA; el proyecto no ofrece cobertura completa del AMBA.

## Funcionalidades principales

- **Cuentas y perfiles:** registro, inicio y cierre de sesión, preferencias, perfiles públicos opcionales y recuperación de contraseña. El flujo de recuperación está implementado; la entrega mediante SMTP productivo sigue pendiente.
- **Catálogo y mapas:** búsqueda de líneas numéricas o alfanuméricas, ramales y sentidos; representación de trazados y paradas, selección sincronizada entre mapa y lista y resaltado del tramo elegido. Los recorridos incompletos muestran su estado de datos.
- **Viajes y progreso:** validación de subida y bajada dentro del mismo recorrido, historial privado y progreso por parada, sentido, ramal y línea. Una parada compartida entre ramales cuenta una sola vez dentro de la misma línea.
- **Puntos y comunidad:** un punto por parada nueva en una línea y premios por completar sentidos, ramales y líneas; niveles, logros, rankings globales, semanales y de personas seguidas. El seguimiento es unilateral y respeta la visibilidad del perfil.
- **Administración de datos:** importaciones CSV/GeoJSON, auditoría de ejecuciones y errores, revisión de asociaciones ambiguas y reprocesamiento espacial. Las paradas ilustrativas históricas se conservan, pero no habilitan viajes nuevos.
- **Interfaz adaptable:** vistas para escritorio y móvil, temas claro, oscuro y del sistema. Incluye manifiesto y service worker para instalación como PWA; sin conexión muestra un aviso y no permite registrar viajes offline.

## Flujo de uso

1. La persona explora el catálogo y consulta recorridos, paradas y disponibilidad.
2. Con una cuenta iniciada, selecciona línea, ramal, sentido y paradas de subida y bajada mediante mapa o lista.
3. El backend verifica la calidad del recorrido, la pertenencia de las paradas y su orden.
4. Una transacción registra el viaje, acredita las paradas nuevas y evalúa premios y logros.
5. La interfaz presenta el resultado y actualiza la colección, el perfil y los rankings.

Un nuevo viaje por un tramo ya registrado se guarda sin volver a premiar las mismas paradas. El reintento de una misma solicitud recupera su resultado anterior.

## Arquitectura y funcionamiento técnico

El frontend Next.js consume una API REST de Django, organizada en módulos de cuentas, transporte, viajes, gamificación, relaciones e importaciones. PostgreSQL/PostGIS almacena usuarios, historial, eventos de puntos y geometrías. MapLibre representa los datos geográficos en el navegador. La API dispone de un esquema OpenAPI.

El flujo de datos separa responsabilidades: **CSV maestro → identidades del catálogo; GeoJSON de BA Data → geometrías y paradas; procesamiento espacial → secuencias utilizables**. El importador geométrico enriquece recorridos existentes sin crear líneas o ramales automáticamente. El enriquecimiento territorial mediante USIG dispone de comando, pero su endpoint y contrato reales siguen pendientes de validación.

La autenticación usa sesiones de Django y protección CSRF, también en acceso y registro. La configuración contempla cookies seguras, límites de solicitudes y restricciones para descargas externas. Nginx comunica frontend y backend; Gunicorn ejecuta Django. Docker Compose define servicios, persistencia y comprobaciones de salud. Existen configuración de producción y script de backup, sin evidencia de publicación vigente.

Las importaciones se ejecutan mediante comandos de administración. La documentación propone cron para programarlas, pero no acredita un planificador activo. El sistema no requiere Celery ni Redis.

## Stack tecnológico

- **Backend:** Python 3.13, Django 5.2, Django REST Framework, GeoDjango, drf-spectacular y Gunicorn.
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4 y MapLibre GL.
- **Datos e integraciones:** PostgreSQL 17, PostGIS 3.5, CSV y GeoJSON oficiales de BA Data; estilos cartográficos configurables y fallback OpenStreetMap para desarrollo.
- **Infraestructura y calidad:** Docker Compose, Nginx, GitHub Actions, pruebas Django sobre PostGIS, Vitest, Testing Library, Playwright, ESLint y comprobación de tipos.

## Desafíos técnicos y decisiones destacables

1. **Evitar premios duplicados:** transacciones, bloqueo de la fila del usuario, claves de idempotencia y restricciones únicas coordinan viajes concurrentes. El puntaje se obtiene del registro de eventos, con claves que evitan repetir premios.
2. **Asociar paradas sin inventar pertenencias:** el procesamiento combina línea, sentido, distancia y evidencia de corredores compartidos. Calcula posiciones acumuladas sobre componentes MultiLineString conservando su orden. Las proyecciones inconcluyentes quedan auditadas; las ambigüedades críticas bloquean viajes.
3. **Actualizar cartografía con seguridad:** cada cambio de geometría exige reprocesar las asociaciones antes de volver a usarlas. Checksums, procedencia y simulaciones con rollback permiten revisar importaciones y evitar trabajo repetido.
4. **Preservar el historial:** las equivalencias demostrables entre paradas ilustrativas y oficiales se representan mediante alias cuando existen referencias históricas. La actualización del catálogo no reescribe viajes, avances ni puntos previos, y los viajes posteriores reconocen esas equivalencias para evitar un segundo premio.
5. **Mantener una interacción geográfica coherente:** mapa y lista comparten la selección por ocurrencia de parada. El tramo resaltado sigue la geometría real y conserva sus discontinuidades; el servidor vuelve a validar los extremos recibidos.

## Beneficios y resultados

El sistema evita cargar cada parada manualmente. Separar disponibilidad de existencia en catálogo permite mostrar cobertura incompleta sin habilitar viajes con datos insuficientes. La auditoría facilita revisar discrepancias conservando referencias históricas.

El CSV actual contiene **135 líneas, 565 ramales y 1.120 recorridos**, comprobados al preparar este resumen. La última verificación documentada, del **6 de noviembre de 2026**, registra **112 geometrías y 108 recorridos utilizables**, con 56 ambigüedades pendientes. Son métricas de cobertura técnica, no de adopción.

Esa verificación informa 140 pruebas backend de la suite completa y una integración offline adicional, 20 pruebas frontend y 12 E2E aprobados, además de validaciones de tipos, lint, migraciones y OpenAPI. También documenta comparaciones de huellas para preservar el historial durante importaciones. Estas pruebas no se repitieron para redactar este archivo.

## Estado actual

Es un MVP implementado y verificado en un entorno local según la documentación. Permanecen pendientes 1.008 trazados, incidencias espaciales, extensiones especiales de eBUS y componentes operativos de publicación: dominio, TLS, SMTP, proveedor cartográfico y backups externos. La configuración de despliegue existe; el repositorio no demuestra una producción pública activa.

## Material para portfolio

- **Tipo y publicación:** aplicación web full stack con procesamiento geoespacial. Visibilidad del repositorio, licencia del código y autorización para publicarlo: por confirmar.
- **Material existente:** 56 capturas locales en `frontend/test-results/`, incluidas `catalogue-extension/mobile-ebus-light.png` y `selection/desktop.png`. Deben revisarse antes de publicar para retirar identificadores de cuentas o información privada. Los recursos de marca están en `assets/`.
- **Capacidades demostrables:** modelado relacional y espacial, APIs, consistencia transaccional, integración de datos públicos, mapas interactivos, pruebas automatizadas e infraestructura reproducible.
- **Caso de estudio sugerido:** mostrar el flujo de viaje y progreso, la decisión ante una asociación espacial ambigua y la actualización de datos conservando el historial, con cuentas de demostración y datos públicos atribuidos.

## Pendiente de confirmar

- Autoría individual, participación de otras personas y contribuciones atribuibles.
- Usuarios reales, uso sostenido e impacto medible fuera de las pruebas.
- Existencia y dirección de una demo pública vigente.
- Permisos para publicar código, marca y capturas, y condiciones de reutilización y atribución de datos y mapas.
