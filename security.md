# Bondiala — Seguridad

Este documento complementa `bondiala.md` y `stack.md`.

Define los criterios mínimos de ciberseguridad para desarrollar, desplegar y operar Bondiala.

## 1. Principios

La seguridad se implementará por capas.

Principios principales:

- el frontend nunca será una frontera de seguridad;
- toda autorización y validación relevante ocurre en Django;
- aplicar mínimo privilegio;
- no exponer servicios internos innecesariamente;
- minimizar la información sensible almacenada;
- mantener trazabilidad de acciones sensibles;
- mantener dependencias e infraestructura actualizadas;
- diseñar backups y recuperación desde el inicio.

Regla central:

> El frontend nunca será una frontera de seguridad. Toda autenticación, autorización, validación, cálculo de progreso y asignación de puntos debe ser verificada por Django.

---

## 2. Arquitectura de seguridad

```text
Internet
   ↓
HTTPS / TLS
   ↓
Nginx
├── rate limiting
├── security headers
├── límites de requests
└── reverse proxy
        ↓
┌─────────────────┬─────────────────┐
│     Next.js     │ Django + DRF    │
│    frontend     │ auth + permisos │
└─────────────────┴────────┬────────┘
                           ↓
                    red Docker interna
                           ↓
                  PostgreSQL + PostGIS
                  NO expuesto a Internet
```

---

## 3. Autenticación

Para la web/PWA se utilizarán inicialmente sesiones de Django.

Las cookies de sesión deberán configurarse con:

```text
Secure
HttpOnly
SameSite
```

No almacenar:

- session IDs;
- access tokens;
- refresh tokens;
- JWT sensibles;

en `localStorage`.

Requisitos:

- login mediante email/usuario y contraseña;
- recuperación de contraseña mediante token temporal;
- verificación de email cuando corresponda;
- contraseñas almacenadas únicamente mediante hashing seguro;
- MFA recomendado para administradores.

Para una futura app móvil podrá evaluarse un mecanismo de autenticación específico para clientes nativos.

---

## 4. Autorización

Autenticarse no implica poder acceder a cualquier recurso.

Todos los endpoints deberán verificar permisos sobre los objetos solicitados.

Ejemplo:

```text
GET /api/v1/viajes/583/
```

Django deberá comprobar que el usuario tenga permiso para consultar ese viaje.

Aplica especialmente a:

- viajes;
- historial;
- progreso privado;
- amistades;
- preferencias;
- actividad;
- edición y eliminación de registros;
- endpoints administrativos.

Los permisos deberán seguir un criterio `deny by default`.

---

## 5. Integridad del progreso y los puntos

El frontend nunca enviará directamente la cantidad de puntos obtenidos.

Ejemplo incorrecto:

```json
{
  "viaje": 528,
  "puntos": 150
}
```

Ejemplo correcto:

```json
{
  "recorrido": "002BIDA",
  "inicio": "parada_a",
  "fin": "parada_b"
}
```

Django deberá:

- validar que el recorrido exista;
- validar que las paradas pertenezcan al recorrido;
- validar el orden inicio/fin;
- calcular las nuevas paradas transitadas;
- detectar progreso ya existente;
- calcular puntos y bonificaciones;
- registrar eventos de puntos;
- evitar adjudicar dos veces una misma recompensa.

El cliente nunca será autoridad sobre:

- puntos;
- niveles;
- logros;
- progreso;
- rankings.

---

## 6. HTTPS

Todo tráfico de producción deberá utilizar HTTPS.

```text
http://bondiala.ar
       ↓
redirect
       ↓
https://bondiala.ar
```

Configuración esperada de Django:

```text
DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
```

También deberá configurarse correctamente la comunicación entre Django y Nginx para reconocer HTTPS detrás del reverse proxy.

Se utilizará HSTS cuando el despliegue esté correctamente estabilizado.

---

## 7. CSRF

Al utilizar sesiones de Django, todas las operaciones que modifiquen estado deberán estar protegidas contra CSRF.

Aplica a:

```text
POST
PUT
PATCH
DELETE
```

La protección CSRF no deberá desactivarse simplemente para facilitar la integración entre Next.js y Django.

---

## 8. XSS y contenido del usuario

No renderizar HTML arbitrario proporcionado por usuarios.

Medidas:

- escapar contenido;
- sanitizar contenido enriquecido si alguna funcionalidad futura lo requiere;
- utilizar Content Security Policy;
- evitar ejecución de scripts inline innecesarios;
- validar URLs proporcionadas por usuarios.

---

## 9. Security headers

Nginx/Django deberán configurar headers de seguridad apropiados.

Como mínimo evaluar:

```text
Content-Security-Policy
X-Content-Type-Options
X-Frame-Options
Referrer-Policy
Strict-Transport-Security
```

La política CSP deberá comenzar de forma compatible con el frontend y endurecerse progresivamente.

---

## 10. Rate limiting

Se aplicará rate limiting especialmente sobre:

- login;
- registro;
- recuperación de contraseña;
- verificación de email;
- creación de viajes;
- búsquedas costosas;
- endpoints geoespaciales;
- endpoints públicos susceptibles a abuso.

Dos niveles:

```text
Nginx
  ↓
limitación básica por IP
  ↓
Django / DRF
  ↓
limitación por usuario / acción
```

---

## 11. Validación de requests

Toda entrada recibida desde frontend o clientes externos debe considerarse no confiable.

Django deberá validar:

- tipos;
- rangos;
- IDs;
- relaciones entre objetos;
- tamaños máximos;
- permisos;
- coherencia de negocio.

No confiar en valores ocultos en formularios ni en validaciones JavaScript.

---

## 12. Datos personales

Los datos deberán clasificarse.

Ejemplo:

```text
Público
───────
nickname
nivel
puntos
logros
ranking

Privado
───────
email
historial detallado
fechas
ubicaciones
preferencias
```

El historial de movilidad puede revelar información sensible sobre hábitos de una persona.

Por eso:

- guardar únicamente datos necesarios;
- no hacer público el historial detallado por defecto;
- minimizar retención de ubicaciones;
- evitar GPS continuo mientras no exista una funcionalidad que lo requiera;
- definir consentimiento y retención si se incorpora tracking GPS.

---

## 13. PostgreSQL + PostGIS

PostgreSQL no deberá estar expuesto directamente a Internet.

Arquitectura:

```text
Django
   ↓
red Docker privada
   ↓
PostgreSQL/PostGIS
```

No publicar `5432` externamente en producción.

Requisitos:

- usuario propio para Bondiala;
- no utilizar superusuario PostgreSQL desde Django;
- contraseña fuerte;
- permisos mínimos;
- backups automáticos;
- pruebas de restauración.

---

## 14. Docker

Buenas prácticas:

- ejecutar procesos como usuario no root cuando sea posible;
- utilizar imágenes confiables;
- fijar versiones;
- mantener imágenes actualizadas;
- no utilizar `privileged: true`;
- no montar `/var/run/docker.sock` dentro de contenedores de aplicación;
- publicar únicamente los puertos estrictamente necesarios;
- mantener redes internas entre servicios.

En producción:

```text
Expuestos:
80
443

No expuestos:
3000
8000
5432
```

---

## 15. Nginx

Nginx será la única entrada pública principal al stack.

Funciones:

- HTTPS;
- reverse proxy;
- rate limiting;
- security headers;
- límites de tamaño;
- redirecciones;
- manejo del dominio;
- ocultamiento de puertos internos.

Flujo:

```text
bondiala.ar
   ↓
Nginx
├── /api/* → Django
└── /*     → Next.js
```

---

## 16. Secrets

Nunca incluir secretos en el repositorio.

No commitear:

```text
SECRET_KEY
DATABASE_PASSWORD
API keys
tokens
certificados privados
.env
```

En desarrollo pueden utilizarse archivos `.env` ignorados por Git.

En producción, los secretos deberán inyectarse mediante variables de entorno o el mecanismo de secretos del proveedor utilizado.

Django:

```text
DEBUG=False
```

y `ALLOWED_HOSTS` limitado a dominios conocidos.

---

## 17. Django deployment checks

Antes de cada despliegue de producción ejecutar:

```bash
python manage.py check --deploy
```

Los warnings de seguridad deberán revisarse antes de publicar.

---

## 18. Dependencias

Mantener vigilancia sobre vulnerabilidades conocidas.

Backend:

```text
pip-audit
```

Frontend:

```text
npm audit
```

Repositorio:

- Dependabot;
- secret scanning;
- revisión de dependencias nuevas;
- versiones fijadas cuando corresponda.

Las vulnerabilidades críticas y altas deben priorizarse.

---

## 19. Logs de seguridad

Registrar eventos útiles como:

- login exitoso;
- login fallido;
- recuperación de contraseña;
- errores 403;
- errores 429;
- errores 5xx;
- modificaciones administrativas;
- importaciones de datos;
- cambios sensibles;
- cambios manuales de puntos o progreso.

Nunca registrar:

- contraseñas;
- cookies de sesión;
- tokens;
- secretos;
- headers `Authorization`;
- claves privadas.

---

## 20. Auditoría administrativa

Las acciones administrativas sensibles deberían poder auditarse.

Ejemplos:

```text
administrador modifica línea
administrador modifica recorrido
administrador modifica puntos
administrador elimina usuario
administrador ejecuta importación manual
```

Registrar cuando sea razonable:

- usuario;
- acción;
- objeto;
- fecha;
- resultado.

---

## 21. Backups

PostgreSQL deberá contar con backups automáticos.

Política inicial sugerida:

```text
7 backups diarios
4 backups semanales
3 backups mensuales
```

La retención definitiva dependerá del proveedor y costos.

Los backups externos deberán cifrarse cuando corresponda.

Periódicamente se deberá comprobar que una restauración completa funciona.

---

## 22. VPS / servidor

Hardening mínimo:

- SSH mediante clave;
- login SSH por contraseña deshabilitado;
- login remoto directo de root deshabilitado;
- firewall;
- actualizaciones de seguridad;
- sistema operativo soportado;
- acceso administrativo restringido.

Puertos públicos esperados:

```text
22    SSH
80    HTTP
443   HTTPS
```

SSH podrá restringirse adicionalmente por IP o VPN cuando sea viable.

---

## 23. Importadores y fuentes externas

BA Data y USIG son fuentes externas y deben considerarse no confiables desde el punto de vista de entrada de datos.

Los importadores deberán:

- validar estructura;
- validar tipos;
- controlar geometrías inválidas;
- evitar borrados masivos ante respuestas vacías;
- registrar errores;
- guardar estado de cada importación;
- comparar cambios antes de aplicar modificaciones destructivas.

Una fuente temporalmente vacía o caída no deberá interpretarse automáticamente como que todos los registros fueron eliminados.

---

## 24. CI/CD

Cuando exista pipeline CI/CD, deberá incorporar progresivamente:

```text
tests
↓
lint
↓
dependency audit
↓
Django deploy checks
↓
build
↓
deploy
```

No permitir despliegues automáticos si existen errores críticos conocidos del pipeline.

---

## 25. Checklist mínimo de producción

Antes del primer deploy público:

- [ ] `DEBUG=False`
- [ ] HTTPS activo
- [ ] cookies `Secure`
- [ ] cookies `HttpOnly`
- [ ] CSRF activo
- [ ] HSTS evaluado/configurado
- [ ] security headers
- [ ] rate limiting
- [ ] permisos por objeto revisados
- [ ] PostgreSQL no expuesto
- [ ] contenedores sin privilegios innecesarios
- [ ] secrets fuera de Git
- [ ] backups activos
- [ ] restauración probada
- [ ] logs sin datos sensibles
- [ ] dependencia scanning activo
- [ ] `python manage.py check --deploy`
- [ ] firewall configurado
- [ ] SSH por clave
- [ ] MFA administrativo evaluado/activo

---

## 26. Fuera del alcance inicial

No se incorporarán durante el MVP salvo necesidad concreta:

- WAF enterprise;
- SIEM;
- IDS/IPS avanzado;
- Vault;
- Kubernetes security policies;
- arquitectura Zero Trust interna;
- SOC;
- pentesting continuo.

Estas herramientas podrán evaluarse si la escala, exposición o criticidad del servicio aumenta.

---

## 27. Revisión

`security.md` deberá revisarse cuando cambien aspectos relevantes como:

- autenticación;
- infraestructura;
- proveedor de hosting;
- aplicaciones móviles;
- tracking GPS;
- datos personales almacenados;
- integraciones externas;
- sistema de permisos;
- monetización;
- crecimiento significativo de usuarios.
