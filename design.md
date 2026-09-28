# Bondiala — Diseño e identidad visual

Este documento complementa:

- `bondiala.md`
- `stack.md`
- `security.md`

Define las decisiones actuales de identidad visual, sistema de diseño y criterios de experiencia para Bondiala.

Los archivos visuales finales —logo, isotipo, favicon, app icon y demás assets gráficos— se definirán en una etapa posterior.

---

## 1. Concepto de marca

Bondiala convierte viajar en colectivo en una experiencia de exploración, colección y progreso.

La marca no debe sentirse como:

- una aplicación oficial de transporte;
- un simple planificador de viajes;
- una app institucional;
- un juego infantil.

Debe transmitir:

- exploración;
- movimiento;
- colección;
- progreso;
- identidad urbana;
- cultura del colectivo;
- pertenencia local.

Idea central:

> Bondiala transforma recorrer el AMBA en colectivo en algo que se puede explorar, completar y coleccionar.

---

## 2. Personalidad

La personalidad de Bondiala será:

```text
Urbana
Cercana
Curiosa
Activa
Lúdica
Argentina
Coleccionable
```

El tono debe sentirse informal y reconocible sin caer en una estética infantil.

La gamificación debe acompañar el producto, no dominarlo.

---

## 3. Lenguaje de marca

El nombre Bondiala nace de convertir el uso del bondi en una acción.

La marca puede construir lenguaje propio alrededor de esa idea.

Ejemplos:

```text
Bondiá una línea nueva.
¿Ya la bondiaste?
Te faltan 4 paradas.
Este ramal ya lo bondiaste.
Seguir bondiando.
Salí a bondiar.
```

Este lenguaje puede utilizarse en:

- microcopy;
- onboarding;
- logros;
- CTA;
- mensajes de progreso;
- notificaciones.

Debe utilizarse con moderación para no sacrificar claridad.

---

## 4. Identidad visual general

La identidad de Bondiala debe convivir con una interfaz donde los colores de las líneas de colectivo tendrán mucho protagonismo.

Por ese motivo, la marca utilizará una paleta propia relativamente sobria.

Regla central:

> Bondiala tiene una identidad propia, pero no compite visualmente con la identidad cromática de cada línea.

Separación conceptual:

```text
Identidad Bondiala
→ navegación
→ interfaz
→ acciones
→ estados
→ marca

Identidad de cada línea
→ badge
→ número
→ recorrido
→ detalles visuales propios
```

---

## 5. Paleta principal

### Bondiala Navy

```text
#17213A
```

Uso principal:

- marca;
- títulos;
- navegación;
- superficies oscuras;
- elementos institucionales;
- iconografía;
- botones principales en light mode.

### Bondiala Yellow

```text
#FFD447
```

Uso principal:

- acentos;
- CTA;
- progreso;
- highlights;
- logros;
- estados activos;
- detalles de marca.

El amarillo deberá utilizarse como acento y no como fondo dominante en grandes superficies.

### Bondiala Cream

```text
#FAFAF7
```

Uso principal:

- fondo general en light mode;
- superficies amplias;
- zonas de lectura.

### Bondiala Blue

```text
#26A7E8
```

Uso principal:

- links;
- información;
- selección;
- controles interactivos;
- mapas;
- elementos secundarios.

---

## 6. Colores funcionales

```text
Éxito       #198754
Advertencia #F59E0B
Error       #DC3545
Info        #26A7E8
```

Estos colores son funcionales y no forman parte de la identidad principal de marca.

---

## 7. Light mode

Tokens iniciales:

```text
background       #FAFAF7
surface          #FFFFFF
surface-alt      #F1F3F5
text-primary     #1D2433
text-secondary   #667085
border           #D9DEE7
brand-primary    #17213A
brand-accent     #FFD447
interactive      #26A7E8
```

---

## 8. Dark mode

Dark mode es una funcionalidad prioritaria y deberá diseñarse desde el inicio.

Tokens iniciales:

```text
background       #0E1320
surface          #17213A
surface-alt      #202A44
text-primary     #F7F8FA
text-secondary   #AAB2C0
border           #303B55
brand-primary    #FFD447
brand-accent     #FFD447
interactive      #39B5F4
```

En dark mode el amarillo gana protagonismo como color de marca, mientras que el azul noche funciona naturalmente como superficie.

---

## 9. Modos de apariencia

Bondiala deberá soportar:

```text
light
dark
system
```

`system` será el valor inicial recomendado.

---

## 10. Tokens semánticos

Los componentes no deberán depender directamente de colores hexadecimales.

Se utilizarán tokens semánticos:

```text
--background
--surface
--surface-alt
--text-primary
--text-secondary
--border
--brand-primary
--brand-accent
--interactive
--success
--warning
--error
```

---

## 11. Identidad cromática de las líneas

Los colores de las líneas de colectivo son independientes de la paleta de Bondiala.

Cada línea utiliza una paleta `LineaColor` con:

```text
color_principal
color_secundario_1
color_secundario_2
color_texto
```

Regla:

> Los colores propios de una línea no cambian entre light mode y dark mode.

La interfaz puede agregar borde, sombra, halo o superficie contextual para garantizar contraste sin alterar la identidad de la línea.

---

## 12. Line Badge

El badge de línea será uno de los componentes visuales centrales de Bondiala.

Referencia conceptual:

```text
┌──────────────┐
│ ▬▬▬ ▬▬▬      │
│      60      │
└──────────────┘
```

Elementos:

- bloque principal;
- número grande;
- color principal;
- dos acentos superiores;
- color de texto;
- borde contextual opcional.

La estética debe recordar a una chapa o cartel de línea de colectivo, pero con diseño propio de Bondiala.

---

## 13. Estados de progreso

Los badges y tarjetas podrán representar:

```text
No recorrida
Parcial
Completa
```

El progreso no debe modificar los colores propios de la línea.

Puede mostrarse mediante:

- porcentaje;
- anillo;
- barra;
- check;
- borde;
- pequeña insignia;
- texto adicional.

---

## 14. Tipografía

Tipografía propuesta:

```text
Archivo
```

Uso recomendado:

```text
Archivo Black / ExtraBold
→ marca
→ números de línea
→ títulos destacados

Archivo Medium / Regular
→ interfaz
→ textos
→ formularios
→ navegación
```

La tipografía podrá reevaluarse al cerrar el logo definitivo.

---

## 15. Wordmark

La marca visual se explorará inicialmente como:

```text
bondiala
```

en minúsculas.

En texto editorial y documentación se utilizará:

```text
Bondiala
```

---

## 16. Logo e isotipo

Todavía no se define un logo final.

Criterios preliminares:

- evitar el cliché `colectivo + pin de mapa`;
- priorizar formas simples;
- funcionar en tamaños pequeños;
- convivir con badges de líneas muy coloridos;
- poder utilizarse como app icon;
- mantener buena legibilidad en light y dark mode.

Ideas a explorar:

- letra `B`;
- recorrido;
- parada;
- línea continua;
- chapa;
- número;
- señalética urbana.

Los archivos gráficos se crearán en una etapa posterior.

---

## 17. Iconografía

La iconografía deberá ser simple, consistente, de trazo limpio y fácilmente reconocible.

Categorías principales:

```text
línea
parada
recorrido
viaje
progreso
logro
ranking
perfil
mapa
amigos
```

En producto final no se utilizarán emojis como sistema de iconografía principal.

---

## 18. Lenguaje gráfico

### Recorridos

```text
●──────●──────●──────●
```

Pueden utilizarse en separadores, progreso, fondos, ilustraciones, loaders y onboarding.

### Paradas

```text
○ pendiente
● recorrida
✓ completada
```

### Números de línea

Los números deberán tener presencia visual importante en cards, mapas, rankings, logros y perfiles.

---

## 19. Mapas

El mapa será parte central de la experiencia.

Principios:

- los recorridos deben ser visualmente protagonistas;
- las líneas deben conservar sus colores;
- la interfaz Bondiala debe mantenerse secundaria;
- estados transitados y pendientes deben distinguirse sin destruir la identidad de la línea.

En dark mode se evaluará un mapa base oscuro para mejorar la visibilidad de los recorridos.

---

## 20. Componentes visuales prioritarios

Primer conjunto:

```text
LineBadge
LineCard
RouteCard
StopMarker
ProgressBar
ProgressRing
AchievementBadge
RankingRow
UserAvatar
MapLegend
ThemeToggle
```

Todos deberán funcionar correctamente en light y dark mode.

---

## 21. Bordes, radios y sombras

Dirección preliminar:

```text
radio pequeño     6px
radio medio       10–12px
radio grande      16px
```

Los badges de línea pueden utilizar radios más contenidos para conservar sensación de chapa/cartel.

Las sombras deberán ser sutiles.

---

## 22. Espaciado

Escala propuesta:

```text
4px
8px
12px
16px
24px
32px
48px
64px
```

La interfaz será mobile-first.

---

## 23. Accesibilidad

El diseño deberá considerar desde el inicio:

- contraste suficiente;
- navegación mediante teclado;
- foco visible;
- tamaños táctiles adecuados;
- no depender exclusivamente del color;
- soporte de zoom;
- texto legible;
- estados claros.

Cuando una combinación de una línea no alcance contraste suficiente, Bondiala podrá agregar bordes o superficies auxiliares sin modificar el color original.

---

## 24. Responsive design

Bondiala será mobile-first.

Prioridades:

```text
mobile
tablet
desktop
```

La experiencia de registro de viajes debe funcionar especialmente bien desde el celular.

---

## 25. Microcopy

El tono será cercano y directo.

Ejemplos:

```text
¿Qué vas a bondiar hoy?
Seguir bondiando
Bondiá una línea nueva
Te faltan 8 paradas
Ramal completado
Línea completada
Ya bondiaste esta parada
```

Evitar:

- lenguaje excesivamente formal;
- terminología técnica innecesaria;
- exceso de chistes;
- lenguaje infantil.

---

## 26. Qué evitar

Bondiala no debe parecer:

- Google Maps;
- Moovit;
- una aplicación gubernamental;
- un panel administrativo;
- una app de horarios;
- un simulador de transporte;
- un videojuego infantil.

También evitar:

- exceso de colores de marca;
- degradados decorativos innecesarios;
- exceso de glassmorphism;
- animaciones que distraigan;
- cards con sombras fuertes;
- mezclar colores de Bondiala con colores propios de las líneas.

---

## 27. Dirección visual resumida

```text
Nombre
Bondiala

Dominio previsto
bondiala.com.ar

Concepto
Explorar y coleccionar el AMBA en colectivo.

Personalidad
Urbana · cercana · curiosa · activa · lúdica · argentina

Paleta
Navy    #17213A
Yellow  #FFD447
Cream   #FAFAF7
Blue    #26A7E8

Tipografía
Archivo

Apariencia
Light / Dark / System

Elementos
Recorridos
Paradas
Números de línea
Chapas
Progreso
Mapas
Colección
```

---

## 28. Archivos visuales pendientes

Todavía deben definirse:

```text
logo
wordmark final
isotipo
favicon
app icon
PWA icons
social preview
Open Graph image
splash screen
paleta exportable
tokens finales
iconografía
componentes visuales definitivos
```

Estos elementos se diseñarán después de cerrar la dirección visual general.

---

## 29. Estado

Este documento representa la primera definición del sistema visual de Bondiala.

Las decisiones podrán evolucionar cuando se diseñen el logo, las primeras pantallas, los componentes reales, el mapa, el onboarding, el perfil y el sistema de logros.
