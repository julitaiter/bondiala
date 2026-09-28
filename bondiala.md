# Proyecto: Bondiala

#
# Identidad del proyecto

## Nombre

El nombre elegido para el proyecto es:

```text
Bondiala
```

El nombre busca reforzar la idea de una colección y un registro personal de recorridos en colectivo dentro del AMBA.

Combina:

- una identidad claramente local y argentina;
- una asociación inmediata con los colectivos;
- el componente personal de la experiencia;
- un nombre corto y fácil de recordar.

## Dominio

El dominio previsto para el proyecto es:

```text
bondiala.ar
```

Este dominio todavía no fue registrado.

La elección de `.ar` busca reforzar la identidad local del proyecto y su foco inicial en la red de colectivos del AMBA.


# 1. Idea general

Aplicación web/mobile orientada a amantes de los colectivos y del transporte público del AMBA.

El objetivo principal es que cada usuario pueda registrar qué partes de las líneas de colectivo ya recorrió y construir, con el tiempo, una colección personal de líneas, ramales, sentidos y paradas transitadas.

La app no busca resolver cómo viajar de un punto a otro, sino funcionar como una mezcla de:

- tracker personal;
- colección;
- sistema de progreso;
- gamificación;
- rankings;
- exploración de la red de colectivos del AMBA.

Conceptualmente:

> Coleccioná las líneas de colectivo del AMBA recorriendo sus paradas.

---

## 2. Usuarios

La aplicación tendrá cuentas personales.

Funciones iniciales:

- Sign up.
- Sign in.
- Perfil de usuario.
- Historial/progreso personal.
- Puntaje.
- Nivel.
- Posición en rankings.
- Colección de logros.

Cada usuario tendrá su propio registro de paradas transitadas por línea.

---

## 3. Estructura del transporte

La información debe organizarse aproximadamente así:

```text
Línea
└── Ramal
    ├── Ida
    │   └── Secuencia de paradas
    └── Vuelta
        └── Secuencia de paradas
```

### Línea

Representa una línea de colectivo.

Ejemplo:

```text
Línea 152
```

### Ramal

Una línea puede tener uno o varios ramales.

Ejemplo:

```text
Línea 152
├── Ramal A
├── Ramal B
└── Ramal C
```

### Sentido

Cada ramal puede tener:

- Ida.
- Vuelta.

Las paradas de ida y vuelta se consideran recorridos diferentes cuando físicamente son paradas distintas.

### Parada

Una parada representa una ubicación física.

Una misma parada puede ser utilizada por:

- varios ramales de una misma línea;
- varias líneas diferentes.

Por lo tanto, la parada física debe ser independiente de la línea y del ramal.

---

## 4. Regla principal de progreso

El progreso del usuario se registra por:

```text
usuario + línea + parada
```

Esto significa que una parada se considera transitada dentro de una línea únicamente cuando el usuario pasó por ella viajando en esa línea.

Ejemplo:

```text
Parada: Av. Santa Fe y Pueyrredón

Línea 12   ✅ transitada
Línea 39   ✅ transitada
Línea 152  ❌ no transitada
```

Aunque físicamente sea la misma parada, haber pasado por ella en una línea no completa esa parada para las demás líneas.

---

## 5. Registro de recorridos

El usuario no debería tener que marcar cada parada manualmente.

El flujo ideal para registrar un viaje será:

1. Elegir línea.
2. Elegir ramal.
3. Elegir sentido.
4. Elegir parada inicial.
5. Elegir parada final.
6. Guardar.

La aplicación conoce la secuencia de paradas del recorrido y marca automáticamente como transitadas todas las paradas comprendidas entre la inicial y la final.

Ejemplo:

```text
A → B → C → D → E → F → G
```

Si el usuario registra:

```text
Inicio: B
Fin: F
```

se consideran transitadas:

```text
B → C → D → E → F
```

El registro debe ser rápido y requerir la menor cantidad posible de interacción.

---

## 6. Paradas compartidas entre ramales

Una misma línea puede tener varios ramales que compartan gran parte de sus paradas.

Ejemplo:

```text
Ramal A
A → B → C → D → E

Ramal B
A → B → C → F → G
```

Si el usuario transitó las paradas A, B y C en el Ramal A, esas mismas paradas cuentan automáticamente como transitadas para evaluar el progreso del Ramal B.

La condición es que siempre hayan sido transitadas dentro de la misma línea.

Por lo tanto, el progreso no pertenece exclusivamente al ramal.

Pertenece a:

```text
usuario + línea + parada
```

Los ramales simplemente consultan qué paradas necesita cubrir el usuario.

---

## 7. Progreso de un sentido

Un sentido se considera completado cuando el usuario transitó todas las paradas que forman parte de ese recorrido.

Ejemplo:

```text
Ramal A - Ida

45 paradas totales
45 transitadas

Estado: COMPLETO
```

No importa en cuántos viajes diferentes fueron transitadas.

---

## 8. Progreso de un ramal

Un ramal se considera completado cuando el usuario completó todos sus sentidos requeridos.

Inicialmente:

```text
Ida completada
+
Vuelta completada
=
Ramal completado
```

No es necesario haber hecho el recorrido completo de punta a punta en un único viaje.

---

## 9. Progreso de una línea

Una línea se considera completada cuando el usuario completó todos sus ramales.

Ejemplo:

```text
Línea 152

Ramal A ✅
Ramal B ✅
Ramal C ✅

Línea completada ✅
```

---

## 10. Visualización del progreso

El usuario debería poder ver cuánto recorrió de:

- una línea;
- un ramal;
- un sentido.

Ejemplo:

```text
Línea 152

Ramal A
Ida      38 / 45   84%
Vuelta   41 / 46   89%

Ramal B
Ida      45 / 45  100%
Vuelta   46 / 46  100%
```

También debería poder visualizar qué paradas todavía le faltan.

---

# Gamificación

## 11. Sistema de puntos

Los puntos representan el progreso acumulado del usuario y sirven para:

- rankings;
- niveles;
- motivación;
- comparación entre usuarios.

Sistema inicial propuesto:

| Evento | Puntos |
|---|---:|
| Nueva parada única transitada dentro de una línea | +1 |
| Sentido completado | +5 |
| Ramal completado | +15 |
| Línea completada | +50 |

Una parada solo otorga puntos la primera vez que el usuario la transita dentro de esa línea.

Repetirla no suma puntos adicionales.

---

## 12. Ejemplo de puntaje

```text
Línea 152

84 paradas únicas transitadas      +84
Ida Ramal A completada              +5
Vuelta Ramal A completada           +5
Ramal A completado                 +15

Subtotal                           109 pts
```

Al completar toda la línea:

```text
Línea 152 completada               +50
```

---

## 13. Eventos de puntos

El sistema no debería almacenar únicamente un número total de puntos.

Conviene registrar cada evento que otorgó puntos.

Ejemplo conceptual:

```text
EventoPuntos

usuario
tipo
puntos
línea
ramal
fecha
```

Tipos iniciales:

```text
PARADA_TRANSITADA
SENTIDO_COMPLETADO
RAMAL_COMPLETADO
LINEA_COMPLETADA
LOGRO
```

Esto permitirá:

- calcular rankings semanales;
- mostrar actividad reciente;
- auditar puntos;
- cambiar reglas futuras;
- recalcular estadísticas.

---

# Niveles

## 14. Sistema de niveles

Los niveles se calculan a partir de los puntos acumulados.

No es necesario tener una moneda o XP separada.

Ejemplo de títulos:

```text
Nivel 1   Pasajero
Nivel 5   Frecuente
Nivel 10  Bondiero
Nivel 20  Inspector
Nivel 30  Coleccionista
Nivel 40  Experto del AMBA
Nivel 50  Leyenda del Bondi
```

Los nombres y umbrales definitivos se podrán ajustar cuando se conozca mejor la cantidad total de paradas y contenido disponible.

---

## 15. Progresión de nivel

La progresión debería ser creciente, no necesariamente lineal.

Ejemplo inicial:

```text
Nivel 1       0 pts
Nivel 2      50 pts
Nivel 3     120 pts
Nivel 4     200 pts
Nivel 5     300 pts

Nivel 10  1.000 pts
Nivel 20  3.000 pts
Nivel 30  6.000 pts
Nivel 40 10.000 pts
Nivel 50 15.000 pts
```

Estos valores son orientativos y deben balancearse cuando exista información real de la red.

---

## 16. Presentación del nivel

Ejemplo:

```text
Nivel 17
Bondiero

1.840 / 2.000 pts
████████████████░░░░

Faltan 160 pts para Nivel 18
```

El nivel funciona como motivación personal aunque el usuario no esté cerca de los primeros puestos del ranking global.

---

# Logros

## 17. Colección de logros

Los usuarios tendrán una colección de logros.

Ejemplos:

```text
Primera parada transitada
100 paradas transitadas
1.000 paradas transitadas

Primer sentido completado
Primer ramal completado
10 ramales completados

Primera línea completada
5 líneas completadas
10 líneas completadas

Completar ida y vuelta de un ramal
Completar todos los ramales de una línea
```

Los logros pueden funcionar principalmente como insignias.

Opcionalmente algunos pueden otorgar puntos adicionales.

---

# Rankings

## 18. Ranking global

Muestra el puntaje histórico total de los usuarios.

Ejemplo:

```text
1. Usuario A    4.821 pts
2. Usuario B    4.510 pts
3. Usuario C    4.322 pts
```

---

## 19. Ranking semanal

Cuenta únicamente los puntos obtenidos durante la semana.

Su objetivo es permitir que usuarios nuevos puedan competir sin quedar demasiado lejos de quienes usan la aplicación desde hace años.

Ejemplo:

```text
Ranking semanal

1. Usuario B    312 pts
2. Usuario D    290 pts
3. Usuario A    274 pts
```

---

## 20. Ranking entre amigos

Permite comparar el progreso únicamente contra usuarios agregados o seguidos.

Ejemplo:

```text
Ranking amigos

1. Nico    4.510 pts
2. Juli    4.221 pts
3. Juan    3.980 pts
```

---

## 21. Rankings secundarios

A futuro se pueden sumar rankings adicionales:

- mayor cantidad de paradas transitadas;
- mayor cantidad de ramales completos;
- mayor cantidad de líneas completas;
- mayor porcentaje de la red recorrida;
- rankings por zona;
- rankings mensuales;
- rankings anuales.

---

# Perfil del usuario

## 22. Perfil

Ejemplo conceptual:

```text
Juli
Nivel 23 · Inspector

4.821 pts

🚏 3.940 paradas transitadas
🚌 74 líneas recorridas
🌿 38 ramales completos
🏆 12 líneas completas

Ranking global:   #38
Ranking semanal:   #4
Ranking amigos:    #2
```

También puede mostrar:

- logros recientes;
- líneas favoritas;
- actividad;
- progreso hacia el siguiente nivel.

---

# Modelo conceptual inicial

## 23. Entidades principales

### User

Usuario registrado en la plataforma.

---

### Linea

```text
Linea
- id
- numero
- nombre
- empresa
- activa
```

---

### Ramal

```text
Ramal
- id
- linea
- nombre
- descripcion
- activo
```

---

### Recorrido

Representa un sentido de un ramal.

```text
Recorrido
- id
- ramal
- sentido
```

Valores iniciales de sentido:

```text
IDA
VUELTA
```

---

### Parada

Representa una parada física.

```text
Parada
- id
- nombre
- latitud
- longitud
```

---

### RecorridoParada

Relaciona una parada con un recorrido y define su posición.

```text
RecorridoParada
- recorrido
- parada
- orden
```

Una misma parada puede pertenecer a muchos recorridos.

---

### UsuarioLineaParada

Representa una parada transitada por un usuario dentro de una línea.

```text
UsuarioLineaParada
- usuario
- linea
- parada
- primera_fecha
```

La combinación debe ser única:

```text
usuario + linea + parada
```

Esta entidad es la base principal del progreso.

---

### RegistroViaje

Representa la acción mediante la cual el usuario registra un tramo.

```text
RegistroViaje
- usuario
- linea
- ramal
- recorrido
- parada_inicio
- parada_fin
- fecha
```

Al registrarlo se generan automáticamente las `UsuarioLineaParada` correspondientes.

---

### Logro

```text
Logro
- id
- nombre
- descripcion
- tipo
```

---

### UsuarioLogro

```text
UsuarioLogro
- usuario
- logro
- fecha_obtenido
```

---

### EventoPuntos

```text
EventoPuntos
- usuario
- tipo
- puntos
- linea
- ramal
- fecha
```

---

# Reglas fundamentales

## 24. Reglas de negocio

1. El progreso pertenece a `usuario + línea + parada`.

2. La misma parada física puede contar independientemente para distintas líneas.

3. Una parada transitada varias veces dentro de una misma línea solo cuenta una vez para progreso y puntaje base.

4. Las paradas compartidas por varios ramales de una misma línea cuentan para todos esos ramales.

5. No es necesario completar un ramal en un solo viaje.

6. No es necesario recorrer las paradas en orden para completar un ramal.

7. Un sentido se completa cuando todas sus paradas fueron transitadas.

8. Un ramal se completa cuando se completaron sus sentidos requeridos.

9. Una línea se completa cuando se completaron todos sus ramales.

10. Los puntos por parada se otorgan únicamente la primera vez que se registra esa combinación `usuario + línea + parada`.

11. Los bonuses por sentido, ramal y línea se otorgan una única vez.

12. Los rankings semanales se calculan a partir de eventos de puntos generados durante esa semana.

---

# MVP

## 25. Alcance inicial

La primera versión debería incluir:

### Usuarios

- Registro.
- Inicio de sesión.
- Perfil.

### Datos de transporte

- Líneas.
- Ramales.
- Ida/vuelta.
- Paradas.
- Orden de paradas.

### Registro

- Elegir línea.
- Elegir ramal.
- Elegir sentido.
- Elegir parada inicial.
- Elegir parada final.
- Registrar automáticamente todas las paradas intermedias.

### Progreso

- Paradas transitadas.
- Porcentaje de cada sentido.
- Porcentaje de cada ramal.
- Porcentaje de cada línea.
- Estados completados.

### Gamificación

- Puntos.
- Niveles.
- Logros.

### Rankings

- Global.
- Semanal.
- Entre amigos.

---

# Futuras funcionalidades

## 26. Posibles extensiones

Una vez validado el MVP se podrían incorporar:

- mapa interactivo;
- visualización geográfica de paradas recorridas;
- GPS para detectar viajes automáticamente;
- favoritos;
- viajes recientes;
- repetir un viaje con un toque;
- sugerencia de paradas cercanas;
- perfiles públicos;
- seguir/agregar amigos;
- actividad social;
- compartir progreso;
- estadísticas por zona;
- mapas de calor;
- recorridos históricos;
- líneas o ramales fuera de servicio;
- insignias especiales;
- estadísticas anuales;
- resumen tipo "Wrapped";
- ranking por CABA / Zona Norte / Zona Oeste / Zona Sur.

---



## Identidad visual de las líneas

La identidad visual de una línea se modelará mediante una entidad separada `LineaColor`.

`LineaColor` representa una paleta completa:

```text
LineaColor
- id
- color_principal
- color_secundario_1
- color_secundario_2
- color_texto
```

El modelo `Linea` tendrá una relación `ForeignKey` hacia `LineaColor`:

```text
Linea
- id
- numero
- nombre
- colores → LineaColor
- source
- external_id
```

La relación será:

```text
LineaColor 1 ───── N Linea
```

Esto permite que varias líneas compartan exactamente la misma combinación de colores sin duplicarla.

La relación desde `Linea` deberá ser opcional para permitir líneas cuya identidad visual todavía no haya sido cargada.

Ante la eliminación de una paleta, la línea no deberá eliminarse; la referencia podrá quedar en `null`.

Los colores se almacenarán en formato hexadecimal:

```text
#BE1F1C
#CCC7B1
#1D3B78
#FFFFFF
```

### Unicidad de paletas

No deberían existir dos registros `LineaColor` con exactamente la misma combinación de:

```text
color_principal
color_secundario_1
color_secundario_2
color_texto
```

Por lo tanto, la combinación completa deberá tener una restricción de unicidad.

### Fuente de los colores

Los colores no provienen del GeoJSON de BA Data.

Se cargarán desde un JSON complementario mantenido por Bondiala:

```text
colores_lineas_bondiala.json
```

Ejemplo:

```json
{
  "linea": 2,
  "color_principal": "#BE1F1C",
  "color_secundario_1": "#CCC7B1",
  "color_secundario_2": "#1D3B78",
  "color_texto": "#FFFFFF"
}
```

Durante la importación, Bondiala deberá:

```text
leer combinación de colores
        ↓
buscar o crear LineaColor
        ↓
buscar Linea por número normalizado
        ↓
asignar Linea.colores
```

El JSON de colores es una fuente complementaria de identidad visual y no reemplaza a BA Data como fuente principal del catálogo.
# Fuentes de datos

## 27. BA Data como fuente principal

La aplicación utilizará **Buenos Aires Data (BA Data)** como fuente principal para importar y mantener el catálogo de transporte.

La idea es que BA Data alimente la base propia de Bondiala con la información estructural necesaria para representar la red de colectivos del AMBA.

El objetivo es importar y normalizar, cuando los datasets lo permitan:

- líneas;
- recorridos o ramales;
- sentidos;
- paradas;
- orden de paradas por recorrido;
- geometrías o trazados;
- empresas u operadores;
- identificadores externos.

BA Data no funcionará como backend operativo de la aplicación.

El flujo esperado será:

```text
BA Data
   ↓
Importador Bondiala
   ↓
Normalización
   ↓
Base de datos propia
   ↓
Progreso / puntos / niveles / logros / rankings
```

La aplicación mantendrá su propia copia normalizada de la información de transporte.

Esto permite:

- no depender de la disponibilidad de una fuente externa durante el uso cotidiano;
- mejorar los tiempos de respuesta;
- controlar la estructura interna de los datos;
- conservar históricos;
- detectar cambios entre importaciones;
- adaptar los datasets externos al modelo propio de Bondiala;
- combinar en el futuro información proveniente de otras fuentes.

### Identificadores externos

Las entidades importadas deberían conservar el identificador original de la fuente.

Por ejemplo:

```text
Linea
- id
- external_id
- source
```

El mismo criterio debería aplicarse, cuando corresponda, a:

- ramales o recorridos;
- paradas;
- empresas;
- geometrías.

La combinación de `source` y `external_id` permitirá resincronizar datos sin generar duplicados y relacionar correctamente los registros internos con su fuente original.

### API Transporte GCBA

La API Transporte del Gobierno de la Ciudad de Buenos Aires queda como fuente secundaria o complementaria.

Puede utilizarse para:

- contrastar información importada desde BA Data;
- completar datos faltantes;
- consultar información adicional que no esté disponible en los datasets principales;
- servir como fuente alternativa ante necesidades puntuales.

No será la fuente principal del catálogo ni se consultará como backend operativo durante el uso normal de la aplicación.

Referencia:

`https://api-transporte.buenosaires.gob.ar/console`


### USIG como servicio geográfico auxiliar

USIG puede utilizarse como una fuente complementaria para enriquecer geográficamente la información importada desde BA Data.

No será la fuente principal para determinar líneas, ramales, sentidos o secuencias de paradas.

Su función será agregar contexto geográfico útil a las paradas y facilitar búsquedas por ubicación.

Posibles usos:

- geocodificación;
- geocodificación inversa;
- normalización de direcciones;
- identificación de calles o esquinas cercanas;
- enriquecimiento con barrio;
- enriquecimiento con comuna;
- conversión y validación de coordenadas;
- búsqueda de paradas cercanas a una dirección.

Ejemplo:

```text
BA Data
   ↓
Parada
latitud / longitud
   ↓
USIG
   ↓
Dirección / esquina / barrio / comuna
   ↓
Parada enriquecida en Bondiala
```

La información enriquecida debería almacenarse en la base propia de Bondiala, evitando depender de consultas a USIG durante el uso cotidiano de la aplicación.

Ejemplo conceptual:

```text
Parada
- id
- nombre
- latitud
- longitud
- direccion
- esquina
- barrio
- comuna
```

Esto puede mejorar especialmente la experiencia de registro manual, permitiendo mostrar opciones más comprensibles para el usuario.

Por ejemplo:

```text
Av. Cabildo y Juramento
Av. Cabildo y Mendoza
Av. Cabildo y Olazábal
```

en lugar de presentar únicamente identificadores técnicos o coordenadas.

### Uso de barrio y comuna

El enriquecimiento territorial también puede utilizarse para estadísticas y logros.

Ejemplos:

```text
12 comunas recorridas
48 barrios recorridos
```

Posibles logros futuros:

```text
Visitaste las 15 comunas en colectivo
Recorriste 25 barrios
```

El criterio de progreso territorial deberá definirse más adelante, pero USIG puede aportar la información necesaria para construir estas funcionalidades.

### Búsqueda por dirección

USIG también puede servir para transformar una dirección ingresada por el usuario en coordenadas.

Flujo posible:

```text
"Cabildo 2500"
      ↓
USIG
      ↓
Coordenadas
      ↓
Bondiala
      ↓
Paradas cercanas
```

Esto permitiría en el futuro buscar líneas o paradas cercanas a una dirección sin utilizar USIG como fuente de recorridos.


### Múltiples fuentes

El diseño no debe quedar atado exclusivamente a BA Data.

La arquitectura debería permitir incorporar en el futuro otras APIs, datasets o fuentes de transporte del AMBA.

Por lo tanto, conviene considerar desde el inicio el concepto de `source` o `data_source` para identificar el origen de cada registro importado.
# Principio de producto

La aplicación debe priorizar siempre una experiencia de registro sencilla.

Registrar un viaje no debería sentirse como cargar datos administrativos.

La idea es que el usuario pueda registrar rápidamente:

```text
Línea
Ramal
Sentido
Desde
Hasta
Guardar
```

y que el sistema haga automáticamente todo lo demás:

- detectar paradas intermedias;
- actualizar progreso;
- detectar sentidos completados;
- detectar ramales completados;
- detectar líneas completadas;
- otorgar puntos;
- otorgar logros;
- actualizar nivel;
- actualizar rankings.

La experiencia central debe sentirse como explorar y completar una colección de la red de colectivos del AMBA.