# Bondiala

> Explorá, recorré y coleccioná las líneas de colectivo del AMBA.

Bondiala es una web/app pensada para quienes disfrutan viajar en colectivo y quieren convertir sus recorridos en una experiencia de exploración, colección y progreso.

La idea no es decirte cómo llegar de un punto A a un punto B. Bondiala busca responder otra pregunta:

> **¿Cuánto del AMBA ya bondiaste?**

---

## Estado del proyecto

Bondiala se encuentra actualmente en etapa de definición de producto, arquitectura e identidad visual, previo al desarrollo del MVP.

Dominio previsto:

```text
bondiala.com.ar
```

---

## Cómo funciona

El progreso se registra por:

```text
usuario + línea + parada
```

Una misma parada física puede ser utilizada por múltiples líneas, pero el progreso pertenece a cada línea de forma independiente.

Ejemplo:

```text
Av. Santa Fe y Pueyrredón

Línea 12    ✓ transitada
Línea 39    ✓ transitada
Línea 152   ○ pendiente
```

Para registrar un viaje, el usuario selecciona:

1. línea;
2. ramal;
3. sentido;
4. parada de inicio;
5. parada de fin.

Bondiala conoce la secuencia del recorrido y marca automáticamente las paradas transitadas entre ambos puntos.

No es necesario recorrer un ramal completo en un único viaje.

---

## Progreso

La estructura principal del transporte es:

```text
Línea
└── Ramal
    ├── Ida
    │   └── secuencia de paradas
    └── Vuelta
        └── secuencia de paradas
```

El progreso se deriva de las paradas transitadas:

- un sentido se completa al recorrer todas sus paradas;
- un ramal se completa al completar sus sentidos;
- una línea se completa al completar todos sus ramales;
- las paradas compartidas entre ramales de una misma línea cuentan para todos esos ramales.

---

## Gamificación

Bondiala incorpora una capa de progreso y colección con:

- puntos;
- niveles;
- logros;
- ranking global;
- ranking semanal;
- ranking entre amigos.

Propuesta inicial de puntos:

```text
+1   parada nueva dentro de una línea
+5   sentido completado
+15  ramal completado
+50  línea completada
```

Las recompensas se calculan siempre en el backend.

---

## Datos de transporte

### BA Data

La fuente principal del catálogo será **Buenos Aires Data**.

El GeoJSON de recorridos aporta, entre otros datos:

```text
fid
linea
recorrido
sentido
l_r_s
modalidad
jurisdicci
camara
desde
hasta
geometry
```

Cada recorrido se importa y normaliza dentro de la base propia de Bondiala.

La aplicación no dependerá de BA Data durante el uso cotidiano.

### USIG

USIG se utilizará como servicio geográfico auxiliar para enriquecer información como:

- direcciones;
- calles y esquinas;
- barrios;
- comunas;
- geocodificación;
- búsqueda por ubicación.

### Colores de líneas

La identidad visual de las líneas se carga desde:

```text
colores_lineas_bondiala.json
```

Las paletas se almacenan en `LineaColor` y pueden ser compartidas por varias líneas.

---

## Arquitectura

```text
                    BA Data
                       │
                 GeoJSON / import
                       │
                       ▼
USIG ───────────▶ Django + DRF + GeoDjango
                       │
                       ▼
              PostgreSQL + PostGIS
                       │
                    REST API
                       │
                       ▼
               Next.js + MapLibre
                       │
                       ▼
                   Web / PWA
```

La aplicación mantiene una base propia normalizada y trazable.

---

## Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- MapLibre GL JS

### Backend

- Django
- Django REST Framework
- GeoDjango

### Datos

- PostgreSQL
- PostGIS

### Infraestructura

- Docker
- Docker Compose
- Nginx en producción
- management commands + cron para importaciones y tareas iniciales

La primera versión será una web responsive instalable como PWA.

Una futura aplicación móvil podrá reutilizar la misma API.

---

## Seguridad

Bondiala sigue un enfoque de seguridad por capas.

Principios centrales:

- el frontend nunca es una frontera de seguridad;
- autenticación web mediante sesiones seguras de Django;
- cookies `HttpOnly`, `Secure` y `SameSite`;
- CSRF activo;
- permisos validados en backend;
- puntos, niveles y progreso calculados exclusivamente por Django;
- rate limiting;
- HTTPS obligatorio en producción;
- PostgreSQL/PostGIS sin exposición pública;
- secrets fuera del repositorio;
- backups y trazabilidad de acciones sensibles.

A futuro podrá evaluarse un sistema separado de credenciales/API tokens para integraciones externas como MCP, bots o automatizaciones. No forma parte del MVP.

---

## Identidad visual

Bondiala busca una estética:

```text
urbana · cercana · curiosa · activa · lúdica · argentina
```

Paleta principal:

| Token | Color |
| --- | --- |
| Navy | `#17213A` |
| Yellow | `#FFD447` |
| Cream | `#FAFAF7` |
| Blue | `#26A7E8` |

La interfaz soportará desde el inicio:

```text
Light
Dark
System
```

Los colores propios de cada línea permanecen independientes del tema visual de Bondiala.

---

## Documentación

La documentación del proyecto se divide por responsabilidad:

| Archivo | Contenido |
| --- | --- |
| [`bondiala.md`](bondiala.md) | Producto, reglas, progreso, puntos y modelo funcional |
| [`stack.md`](stack.md) | Arquitectura, tecnologías, importadores e infraestructura |
| [`security.md`](security.md) | Criterios de seguridad, despliegue y operación |
| [`design.md`](design.md) | Identidad visual, temas, componentes y criterios de UX |
| [`colores_lineas_bondiala.json`](colores_lineas_bondiala.json) | Paletas visuales de las líneas |

---

## MVP

La primera versión apunta a incluir:

- registro e inicio de sesión;
- catálogo de líneas, ramales y recorridos;
- mapa de recorridos;
- registro de viajes entre parada inicial y final;
- progreso por parada, sentido, ramal y línea;
- puntos y niveles;
- logros;
- rankings;
- perfil de usuario;
- soporte light/dark/system;
- PWA mobile-first.

---

## Principios del proyecto

1. **Registrar un viaje debe tomar segundos.**
2. **La aplicación calcula el resto.**
3. **El progreso pertenece a `usuario + línea + parada`.**
4. **La base propia es la fuente operativa de Bondiala.**
5. **Los datos externos se importan, validan y trazan.**
6. **La gamificación acompaña la exploración; no la reemplaza.**
7. **La seguridad y el dark mode se diseñan desde el inicio.**
8. **Evitar complejidad técnica que el MVP todavía no necesita.**

---

## Roadmap general

```text
Definición de producto
        ↓
Identidad visual
        ↓
Modelos + importadores
        ↓
API
        ↓
Web/PWA
        ↓
MVP público
        ↓
Integraciones y app móvil
```

---

## Licencia

La licencia del repositorio todavía no fue definida.

Antes de publicar código o redistribuir datos externos deberá revisarse la licencia correspondiente de cada fuente utilizada.
