# API REST v1

Base: `/api/v1/`. JSON, sesiones Django y CSRF. OpenAPI: `GET /api/v1/schema/`. Las listas paginadas usan `count`, `next`, `previous`, `results` y `?page=N`, con 24 entradas por página. Errores DRF: `{"error": {...}}`. Nginx puede devolver un 429 sin JSON; el cliente contempla ese caso.

## Sesión

1. `GET auth/csrf/` devuelve `csrfToken` y fija una cookie HttpOnly.
2. Enviar ese token como `X-CSRFToken` y mantener cookies same-origin en cada POST/PATCH/DELETE.
3. Login/registro rotan sesión/CSRF: obtener un token nuevo antes de la siguiente modificación. No usar tokens de autenticación en localStorage.

| Método | Ruta | Datos / resultado |
|---|---|---|
| POST | `auth/registro/` | `username`, `nickname`, `email`, `password`; crea sesión |
| POST | `auth/login/` | `identifier` (email o usuario), `password` |
| POST | `auth/logout/` | Cierra la sesión |
| POST | `auth/recuperar/` | `email`; respuesta igual exista o no la cuenta |
| POST | `auth/restablecer/` | `uid`, `token`, `password`; token temporal de un uso |
| GET | `me/` | `{"user": perfil_privado_o_null}` |
| PATCH | `me/` | `nickname`, `avatar` HTTPS opcional, `public_profile`, `theme` |

El usuario no puede cambiar roles, puntos, email ni ownership desde preferencias. El email se modifica únicamente mediante un procedimiento administrativo validado; no se implementa un cambio de email sin verificación.

## Catálogo público

| Ruta GET | Resultado |
|---|---|
| `lineas/?search=60` | Líneas activas con paleta, ramales y progreso contextual |
| `lineas/?estado=recorridas` | Con sesión, filtra líneas transitadas |
| `lineas/{id}/` | Línea y árbol de completitud |
| `lineas/{id}/recorridos/` | Sus recorridos activos con MultiLineString y secuencias |
| `recorridos/?linea={id}&ramal={id}` | Recorridos paginados |
| `recorridos/{id}/` | Geometría WGS84 opcional, paradas ordenadas, modalidad, jurisdicción, cámara y cabeceras |
| `paradas/?search=Palermo&recorrido={id}` | Paradas físicas paginadas |
| `estado/` | Indica si está presente el catálogo de muestra |

`LineBadge` recibe los cuatro hexadecimales de `colores`. Sin paleta usa el fallback. El catálogo no publica metadata interna ni errores de importación.

El catálogo procede del CSV. `geometria` puede ser `null` y `paradas` puede estar vacío porque ese archivo no incluye datos geográficos. La UI distingue ese estado de un error de carga. Solo se pueden registrar viajes cuando existe una secuencia de paradas válida. `modalidad`, `jurisdiccion` y `camara` son campos explícitos tomados del CSV.

## Viajes privados

`GET viajes/` y `GET viajes/{id}/` solo devuelven viajes propios. `GET progreso/` devuelve el progreso de las líneas transitadas por la sesión. No hay edición ni borrado de viajes en el MVP para mantener la integridad de fuentes/ledger.

`POST viajes/`:

```json
{
  "recorrido": 1,
  "inicio": 10,
  "fin": 20,
  "idempotency_key": "c9d79d35-bd71-4b91-a39f-37971b074190"
}
```

**`inicio` y `fin` son IDs de ocurrencias `RecorridoParada`**, obtenidos del campo `paradas[].id` del recorrido; no son IDs de la parada física. Esto distingue dos pasos por la misma parada en recorridos circulares. La bajada debe tener un orden mayor a la subida y ambas deben pertenecer al recorrido activo. El segmento es inclusivo.

La respuesta incluye el viaje y `resultado`: nuevas paradas, puntos otorgados, nuevos logros y completitud de línea/ramales/sentidos. Se calcula íntegramente en Django. Campos como `puntos`, `usuario` o `logros` en el payload se rechazan.

Reintentar con la misma clave y payload devuelve el viaje original (200; creación 201). Reusar la clave con otro payload es 400. Una clave nueva puede registrar otro viaje físico idéntico, pero no duplica avances ni premios. Omitir la clave genera una nueva en servidor. El bloqueo del usuario serializa registros concurrentes; las restricciones de unicidad protegen el ledger y el progreso.

## Comunidad

| Método | Ruta | Alcance |
|---|---|---|
| GET | `perfiles/?search=...` | Perfiles públicos; sin email/historial |
| GET | `perfiles/{username}/` | Métricas agregadas, nivel, logros y posiciones públicas |
| GET | `rankings/?tipo=global` | Puntos históricos de perfiles públicos |
| GET | `rankings/?tipo=semanal` | Eventos desde lunes 00:00 hasta lunes siguiente en Argentina |
| GET | `rankings/?tipo=amigos` | Con sesión: seguidos públicos y usuario, si es público |
| GET | `logros/?obtenidos=true` | Catálogo, progreso e insignias de la sesión |
| GET | `amigos/` | Relaciones propias paginadas |
| POST | `amigos/` | `{"seguido": user_id}`; idempotente |
| DELETE | `amigos/{relation_id}/` | Solo una relación propia |

Los empates en ranking se resuelven por ID ascendente para mantener paginación y posiciones estables. Al ocultar un perfil desaparece de búsquedas/rankings y listas públicas de seguidos. El usuario conserva su colección privada. No hay endpoint de escritura pública del catálogo, ledger, importaciones ni acciones admin.
