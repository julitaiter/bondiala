# Bondiala — Stack técnico

Este documento complementa `bondiala.md` y define el stack técnico propuesto para la primera versión de Bondiala.

## 1. Objetivo

Construir una aplicación web/PWA para registrar recorridos en colectivo, visualizar progreso, puntos, logros y rankings, manteniendo una arquitectura simple, extensible y preparada para incorporar una app móvil más adelante.

Principios:

- priorizar velocidad de desarrollo;
- evitar sobrearquitectura;
- mantener una API reutilizable;
- usar una base geoespacial desde el inicio;
- desacoplar la aplicación de las fuentes externas;
- conservar trazabilidad de importaciones.

---

## 2. Stack elegido

| Capa | Tecnología |
|---|---|
| Frontend web | Next.js |
| Lenguaje frontend | TypeScript |
| UI | Tailwind CSS |
| Mapas | MapLibre GL JS |
| Backend | Django |
| API | Django REST Framework |
| GIS backend | GeoDjango |
| Base de datos | PostgreSQL + PostGIS |
| Importadores | Django management commands |
| Jobs iniciales | cron |
| Contenedores | Docker + Docker Compose |
| Reverse proxy producción | Nginx |
| Fuente principal | BA Data |
| Enriquecimiento geográfico | USIG |
| App móvil inicial | PWA |
| App móvil futura | React Native / Expo |

---

## 3. Arquitectura general

```text
                    ┌──────────────┐
                    │   BA Data    │
                    └──────┬───────┘
                           │
                    importar CSV / geometrías GeoJSON
                           │
                           ▼
┌──────────────┐     ┌──────────────┐
│     USIG     │────▶│    Django    │
└──────────────┘     │   + DRF      │
                     │ + GeoDjango  │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ PostgreSQL   │
                     │  + PostGIS   │
                     └──────┬───────┘
                            │
                       REST API
                            │
                     ┌──────▼───────┐
                     │   Next.js    │
                     │  TypeScript  │
                     │   Tailwind   │
                     │   MapLibre   │
                     └──────┬───────┘
                            │
                         PWA/web
                            │
                      bondiala.com.ar
```

---

## 4. Backend

### Django

Django será el backend principal.

Es una buena opción para Bondiala porque el dominio tendrá muchas entidades relacionadas:

- usuarios;
- líneas;
- ramales;
- recorridos;
- sentidos;
- paradas;
- registros de viaje;
- progreso;
- puntos;
- niveles;
- logros;
- rankings;
- amistades;
- importaciones;
- fuentes de datos.

Además aporta desde el inicio:

- ORM;
- autenticación;
- migraciones;
- panel de administración;
- validaciones;
- management commands.

### Django REST Framework

La aplicación se diseñará API-first.

Ejemplos conceptuales:

```text
/api/v1/lineas/
/api/v1/lineas/{id}/
/api/v1/recorridos/{id}/
/api/v1/paradas/
/api/v1/viajes/
/api/v1/progreso/
/api/v1/logros/
/api/v1/rankings/
```

La misma API podrá ser consumida en el futuro por una app móvil.

---

## 5. GIS

### GeoDjango

GeoDjango se utilizará para trabajar con geometrías geográficas desde Django.

Ejemplo conceptual:

```python
class Parada(models.Model):
    ubicacion = models.PointField(srid=4326)

class Recorrido(models.Model):
    geometria = models.MultiLineStringField(srid=4326, null=True, blank=True)
```

### PostgreSQL + PostGIS

PostGIS será utilizado desde el inicio.

Permitirá:

- almacenar `Point`, `LineString`, `MultiLineString` y polígonos;
- calcular distancias;
- buscar paradas cercanas;
- proyectar paradas sobre recorridos;
- realizar intersecciones;
- trabajar con barrios y comunas;
- indexar consultas espaciales.

La naturaleza de Bondiala es geográfica, por lo que PostGIS debe formar parte de la arquitectura base y no agregarse como parche posterior.

---

## 6. Frontend

### Next.js

El frontend web se construirá con Next.js y TypeScript.

Principales pantallas previstas:

```text
/
/lineas
/lineas/{linea}
/lineas/{linea}/{ramal}
/mapa
/perfil/{usuario}
/ranking
/logros
```

También deberá soportar componentes altamente interactivos:

- mapa;
- selector de línea;
- selector de ramal;
- selector de sentido;
- selección de parada inicial y final;
- progreso;
- badges;
- rankings.

### Tailwind CSS

Tailwind CSS será la base de estilos.

Objetivos:

- velocidad de desarrollo;
- consistencia visual;
- buena adaptación mobile-first;
- evitar una capa de CSS compleja durante el MVP.

No se agregará una librería global de estado hasta que exista una necesidad concreta.

---

## 7. Mapas

### MapLibre GL JS

MapLibre será la biblioteca principal para visualización cartográfica.

Debe permitir representar directamente los GeoJSON de BA Data.

Ejemplo de representación:

```text
recorrido completo      → base
tramo transitado        → destacado
parada transitada       → completada
parada pendiente        → pendiente
```

Los recorridos importados desde BA Data podrán utilizarse directamente como geometrías `MultiLineString`.

---

## 8. Fuentes externas

### BA Data

BA Data será la fuente principal del catálogo.

El catálogo principal se importa desde `data/recorrido-colectivos.csv`, según la decisión actual del producto. Contiene líneas, ramales, sentidos, identificadores y metadata:

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
```

El CSV no contiene geometrías ni paradas. Los GeoJSON son un complemento para incorporar trazados mediante `l_r_s`, sin reemplazar la metadata del catálogo CSV. Un recorrido puede existir con `geometria=null` hasta que se importe su trazado. Las paradas oficiales se importan del GeoJSON de BA Data, que declara líneas y sentidos pero no ramales ni orden. PostGIS filtra candidatos, calcula distancias en metros y proyecta las paradas sobre todos los componentes del trazado para ordenar las asociaciones confiables. Las ambigüedades quedan disponibles para revisión; no habilitan viajes.

El identificador `l_r_s` puede utilizarse como identificador externo natural del recorrido.

Ejemplo:

```text
002BIDA
```

representa:

```text
Línea 002
Ramal B
Sentido IDA
```

### USIG

USIG se utilizará como servicio geográfico auxiliar.

Posibles usos:

- geocodificación;
- geocodificación inversa;
- normalización de direcciones;
- barrio;
- comuna;
- calles y esquinas;
- búsqueda de paradas cercanas a una dirección.

La información obtenida deberá persistirse en la base de Bondiala para evitar dependencia en tiempo real.

### API Transporte GCBA

Queda como fuente secundaria o complementaria.

No será el backend operativo ni la fuente principal del catálogo.

---

## 9. Importadores

Los importadores vivirán inicialmente dentro del proyecto Django.

Ejemplos:

```bash
python manage.py import_badata_recorridos
python manage.py import_badata_paradas
python manage.py enrich_usig
```

Pipeline general:

```text
BA Data
   ↓
descargar fuente
   ↓
validar
   ↓
normalizar
   ↓
comparar
   ↓
crear / actualizar
   ↓
PostgreSQL + PostGIS
```

Cada entidad importada debería conservar:

```text
source
external_id
```

cuando corresponda.

---


### Importación de identidad visual de líneas

La carga inicial separa catálogo, trazados e identidad visual.

```text
1. recorrido-colectivos.csv
   ↓
   Linea / Ramal / Recorrido / metadata

2. GeoJSON opcional → geometrías

3. colores_lineas_bondiala.json
   ↓
   LineaColor
   ↓
   Linea.colores
```

El CSV de BA Data es la fuente principal para la estructura de transporte.

El archivo `colores_lineas_bondiala.json` será una fuente complementaria utilizada exclusivamente para enriquecer la identidad visual de cada línea.

### Modelo LineaColor

La combinación completa de colores se almacenará en una entidad independiente:

```text
LineaColor
- id
- color_principal
- color_secundario_1
- color_secundario_2
- color_texto
```

`Linea` tendrá una ForeignKey opcional:

```text
Linea
- id
- numero
- nombre
- colores → LineaColor
- source
- external_id
```

Relación:

```text
LineaColor 1 ───── N Linea
```

Varias líneas podrán reutilizar una misma paleta.

La combinación completa de colores deberá ser única para evitar duplicados de `LineaColor`.

En Django, conceptualmente:

```python
class LineaColor(models.Model):
    color_principal = models.CharField(max_length=7)
    color_secundario_1 = models.CharField(max_length=7)
    color_secundario_2 = models.CharField(max_length=7)
    color_texto = models.CharField(max_length=7)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "color_principal",
                    "color_secundario_1",
                    "color_secundario_2",
                    "color_texto",
                ],
                name="unique_linea_color_palette",
            )
        ]


class Linea(models.Model):
    colores = models.ForeignKey(
        LineaColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lineas",
    )
```

### Normalización del número de línea

BA Data puede representar los números con ceros a la izquierda:

```text
"002"
"060"
"152"
```

Mientras que el JSON de colores utiliza:

```text
2
60
152
```

El importador deberá normalizar ambos formatos antes de relacionarlos.

Ejemplo:

```text
"002" → "2"
"060" → "60"
"152" → "152"
```

### Management command de colores

La identidad visual podrá cargarse mediante un comando independiente:

```bash
python manage.py import_line_colors colores_lineas_bondiala.json
```

Por cada entrada del JSON, el comando deberá:

1. normalizar el número de línea;
2. buscar la `Linea` existente;
3. realizar `get_or_create` de `LineaColor` usando la combinación completa;
4. asignar `Linea.colores`;
5. guardar únicamente si hubo cambios.

El comando no deberá crear líneas nuevas únicamente a partir del JSON de colores.

También deberá:

- mantener sin cambios las líneas no presentes en el JSON;
- informar entradas del JSON sin línea correspondiente;
- emitir un resumen de la importación.

Ejemplo:

```text
103 líneas actualizadas
42 líneas sin colores
3 entradas JSON sin línea correspondiente
27 paletas únicas
```

El frontend deberá disponer de una paleta fallback cuando una línea no tenga `LineaColor` asociado.
## 10. Trazabilidad de importaciones

Conviene registrar cada ejecución de importación.

Modelo conceptual:

```text
DataSource
ImportRun
ImportError
```

Ejemplo:

```text
ImportRun
- source
- started_at
- finished_at
- status
- records_created
- records_updated
- records_deleted
- source_hash
```

Esto permitirá:

- detectar cambios;
- auditar importaciones;
- conocer el estado de cada fuente;
- evitar duplicados;
- diagnosticar errores;
- soportar múltiples fuentes en el futuro.

Una fuente sin datos no debe interpretarse automáticamente como eliminación de registros.

---

## 11. Jobs

Durante el MVP no se utilizará Celery.

Los procesos periódicos se ejecutarán mediante:

```text
Django management commands
+
cron
```

Ejemplo:

```text
cron semanal
   ↓
descargar BA Data
   ↓
calcular hash
   ↓
¿cambió?
   ├── no → finalizar
   └── sí → importar
```

Más adelante, si aparecen procesos asíncronos pesados, se podrá incorporar:

```text
Celery + Redis
```

---

## 12. Infraestructura y despliegue

### Docker

Bondiala utilizará Docker desde el inicio para mantener entornos reproducibles y aislar las dependencias de cada servicio.

La infraestructura base estará compuesta por:

```text
Docker Compose
├── backend     Django + DRF + GeoDjango
├── frontend    Next.js
├── db          PostgreSQL + PostGIS
└── nginx       reverse proxy en producción
```

Docker permitirá:

- reproducir el entorno entre desarrollo y producción;
- aislar dependencias;
- simplificar instalación y despliegue;
- administrar PostgreSQL/PostGIS de manera consistente;
- facilitar futuras automatizaciones de CI/CD.

Durante desarrollo, Nginx no será obligatorio.

### Docker Compose

Docker Compose será utilizado para levantar el stack completo.

Ejemplo conceptual:

```text
docker compose up
```

El proyecto debería mantener una configuración base reutilizable y, cuando sea necesario, ajustes específicos para producción.

### Nginx

Nginx se utilizará en producción como reverse proxy.

Arquitectura prevista:

```text
Internet
   ↓
bondiala.com.ar
   ↓
Nginx
   ├── /api/*  → Django
   └── /*      → Next.js
```

Nginx podrá encargarse de:

- entrada HTTP/HTTPS;
- reverse proxy;
- dominio `bondiala.com.ar`;
- redirecciones;
- headers;
- compresión;
- límites de tamaño;
- ocultar los puertos internos de los servicios.

El frontend y el backend no deberían exponerse directamente a Internet.

### Despliegue inicial

Para el MVP, un único servidor/VPS ejecutando Docker Compose será suficiente.

Arquitectura:

```text
                    Internet
                       ↓
                 ┌──────────┐
                 │  Nginx   │
                 └────┬─────┘
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
   ┌────────────┐          ┌────────────┐
   │  Next.js   │          │   Django   │
   │  frontend  │          │  + DRF     │
   └────────────┘          └─────┬──────┘
                                 │
                          ┌──────▼───────┐
                          │ PostgreSQL   │
                          │  + PostGIS   │
                          └──────────────┘
```

No se requiere Kubernetes ni orquestación distribuida durante esta etapa.

---

## 13. Web/PWA primero


La primera versión será una web responsive instalable como PWA.

```text
bondiala.com.ar
   ↓
Next.js PWA
```

Objetivos:

- funcionar bien desde el celular;
- poder agregarse a la pantalla de inicio;
- consultar líneas y recorridos;
- registrar viajes;
- visualizar mapas;
- consultar progreso;
- ver puntos, niveles, logros y rankings.

No se desarrollarán inicialmente aplicaciones Android/iOS separadas.

---

## 14. App móvil futura

Si el producto valida uso suficiente, la aplicación móvil podrá construirse con:

```text
React Native + Expo
```

Arquitectura:

```text
Next.js web ───┐
               │
               ├── Django REST API
               │
React Native ──┘
```

La lógica de negocio y los datos permanecerán centralizados en el backend.

---

## 15. Tecnologías que no se incorporarán inicialmente

Durante el MVP no se utilizarán:

- FastAPI como backend separado;
- microservicios;
- Kubernetes;
- Kafka;
- Elasticsearch;
- GraphQL;
- backend serverless;
- Redis como dependencia obligatoria;
- Celery;
- aplicaciones móviles independientes.

Solo deberán incorporarse cuando exista una necesidad concreta que justifique su complejidad.

---

## 16. Resumen

Stack inicial de Bondiala:

```text
Frontend
Next.js + TypeScript + Tailwind
          ↓
       MapLibre
          ↓
      REST API
          ↓
Django + DRF + GeoDjango
          ↓
PostgreSQL + PostGIS

Fuentes
BA Data + USIG

Jobs
Management commands + cron

Infraestructura
Docker + Docker Compose + Nginx

Cliente inicial
Web/PWA

Cliente futuro
React Native / Expo
```

La prioridad es mantener una arquitectura sencilla, geoespacial desde el inicio y preparada para evolucionar sin agregar complejidad prematuramente.

Futuro: evaluar credenciales/tokens de API revocables para integraciones externas como MCP, bots, scripts o automatizaciones, separadas de la autenticación normal de la web/app.
