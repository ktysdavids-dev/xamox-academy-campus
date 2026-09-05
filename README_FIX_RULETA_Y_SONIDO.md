# Fix · Ruleta con texto amontonado + sonido simplificado

## 1) Ruleta: bug real, previo a mis cambios
`challenge-wheel-v2.css` (código original, no lo escribí yo) nunca declaraba
`position` en `.roulette-wheel-v2` ni en `.wheel-label-v2`. Sin eso, las
propiedades `left`/`top`/`transform` que posicionan cada categoría alrededor
del círculo no tienen efecto ninguno en CSS — los 8 textos caían todos en el
mismo punto, amontonados. No se notaba antes porque con `challenge.css`
vacío toda la pantalla era un caos visual y nadie llegó a fijarse en ese
detalle en concreto.

Fix: añadidas las 2 líneas que faltaban (`position:relative` en el
contenedor, `position:absolute` en cada etiqueta). Nada más tocado en ese
archivo.

## 2) Sonido: simplificado a fondo
Quité por completo: la reverberación por convolución (probable causante de
sonar "metálico"/raro) y las capas de ruido blanco (usadas en rayo/fallo).
Ahora cada sonido es 1-2 tonos limpios y cortos, sin adornos. Mismo mapeo de
nombres (correct/wrong/reward/etc.) así que nada más del juego cambia.

## Instalación
    git checkout -b fix/ruleta-y-sonido
    git add -A
    git commit -m "Fix: etiquetas de la ruleta + sonido simplificado"
    git push -u origin fix/ruleta-y-sonido
    # PR -> main -> mergear. Sin migraciones.
