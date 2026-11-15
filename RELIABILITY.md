# VANTAGE — Plan de fiabilidad (borrador)

> Nota de trabajo, no es un spec. Los umbrales de «Terminada cuando» quedaron **fijados el 14 nov** por R, por escrito antes de calcular, como en `SPIKING.md`; si cambian, se registra una versión nueva, nunca en silencio.
> Alcance por ahora: **solo Costa Rica**, con la Ruta 32 como caso. Fecha: 14 nov 2026.

## 1. Objetivo y techo

Tras los spikes (D7, D8 en `STATUS.md`), VANTAGE es un **análisis de consecuencias**: qué pasa con el acceso a un hospital de referencia si se cierra un tramo. No predice cierres ni derrumbes; tres señales se probaron y fallaron (S2, S2c, S5).

Lo que se puede subir en la ventana restante es la **exactitud y la verificabilidad de los números**, no el valor predictivo. El techo realista es:

> «Los tiempos y la población afectada se calculan de forma reproducible; el ranking es estable ante estos supuestos; y se verificaron a mano estos casos.»

## 2. Escalera de afirmaciones

Qué se puede decir según lo que esté hecho.

| Nivel | Estado | Qué se puede decir |
|---|---|---|
| Hoy | Método probado en un spike; ningún caso revisado a mano; sin población | «Análisis de consecuencias creíble pero sin validar; cifras como orden de magnitud.» |
| Tras 5, 4, 2 y 1 | Unidad de cierre fina, población, casos verificados, sensibilidad medida | «Ranking estable ante X variaciones; N casos verificados a mano; población incluida.» |
| Tras los seis | Más contraste externo de tiempos y marcas de confianza en la interfaz | Lo anterior, con tiempos contrastados y la incertidumbre visible al usuario. |

Con cualquier nivel sigue valiendo: nunca «predice», nunca «confirmado», nunca «funciona en cualquier lugar».

## 3. Los seis pasos

| # | Paso | Eleva | Costo | Depende de | Estado |
|---|---|---|---|---|---|
| 5 | **Unidad de cierre fina** (hoy 19 cierres de 1 a 61 km) | Convierte «este corredor es crítico» en «este tramo es crítico» | 2–3 h, **requiere spec** | — | [ ] |
| 4 | **Población** (E4, WorldPop sobre las comunidades) | `criticality` deja de ser 0; «crítico» pasa a significar «mucha gente depende» | ya en el plan | — | [ ] |
| 2 | **Revisión manual de 3 cierres** | Lo que más falta: ningún caso se ha revisado a mano | 1–2 h | 5 | [ ] |
| 1 | **Análisis de sensibilidad** | «El ranking es estable ante estos supuestos» | 1–2 h | 5, 4 | [ ] |
| 3 | **Contraste de tiempos con fuente externa** | Detecta si las velocidades constantes se alejan de la realidad | 1 h | — (en paralelo) | [ ] |
| 6 | **Marcas de confianza en la interfaz** | No sube la exactitud; sube la honestidad con que se lee | 1 h | 2 | [ ] |

### Por qué este orden: 5 → 4 → 2 → 1 (3 en paralelo, 6 al final)

- **5 va primero** porque define qué se mide. Revisar a mano o medir sensibilidad sobre cierres de 61 km y repetirlo después con cierres finos es trabajo doble.
- **4 antes de 1** porque sin población `criticality` es 0 y el ranking sale solo por tiempo extra; la sensibilidad se mediría sobre un ranking que va a cambiar.
- **2 antes de 1** porque la revisión puede encontrar artefactos de ajuste que hay que corregir en P3; la sensibilidad debe correrse sobre el grafo ya corregido.
- **3** no depende de nada y se puede hacer en cualquier hueco.
- **6** muestra lo que 2 encontró, así que va al final.

### Si falta tiempo (G2 es el dom 14:00)

Si el paso 5 no está listo, seguir con las 19 unidades y **etiquetarlas como corredores gruesos** en la interfaz; hacer 4, 2 y 1 sobre ellas. Mejor tres pasos terminados que seis a medias.

## 4. Terminada cuando (umbrales fijados el 14 nov)

**5. Unidad de cierre fina.** Cada cierre incluye ambas calzadas, ninguno supera ~5 km salvo tramos sin uniones intermedias, y el número de cierres sube de 19. La unidad se define en un spec antes de construir (hoy no existe una unidad fina; el spec de P5 no la contemplaba).

**4. Población.** `population` poblada en al menos el 90 % de las comunidades dentro de la zona; el resto queda `null`, nunca 0. La suma coincide con el total del recorte del ráster (S7) con un margen de ±5 %, y la diferencia se explica.

**2. Revisión manual.** Tres cierres elegidos con un criterio fijado antes: el de mayor criticidad, uno mediano y el que cruza el parque Braulio Carrillo. Cada comunidad aislada (hasta 20 por cierre) se clasifica como real, artefacto de ajuste, sentido único o fuera de la red. Pasa si al menos el 80 % de las aisladas son reales; los artefactos se corrigen y se vuelve a medir. La revisión la hace una persona con apoyo de scripts; no se puede sustituir por una comprobación automática.

**1. Sensibilidad.** Perturbaciones: velocidad ×0,8 y ×1,2 en todas las clases; distancia máxima de ajuste a la red de 1 500, 3 000 y 5 000 m; con y sin cada hospital de referencia. Se mide el solapamiento del top 5 y del top 10 con la línea base y la correlación de rangos entre tramos con impacto > 0. Pasa si el top 5 comparte al menos 4 tramos en todas las perturbaciones de velocidad y de ajuste. Quitar un hospital cambia el ranking por naturaleza: se **reporta**, no se juzga.

**3. Contraste de tiempos.** De 15 a 20 pares comunidad→hospital contra una fuente independiente (por ejemplo un enrutador público sobre OSM) y 3 a 5 tiempos de referencia documentados, con su cita, para trayectos largos. Pasa si la mediana del error relativo es ≤ 25 %; si no, se ajustan las velocidades y se declara. **Un enrutador sobre OSM comparte los datos: valida el cálculo, no la verdad del terreno.**

**6. Marcas de confianza.** La interfaz señala los aislamientos sospechosos y muestra el tiempo como orden de magnitud o rango, no como cifra exacta. «Aislada» se dice «sin ruta al hospital de referencia».

## 5. Lo que no se hace

- **Subir el valor predictivo.** Tres señales fallaron; GUNW, desplazamientos y series por píxel siguen sin probar, pero no caben en la ventana y son una apuesta de poca probabilidad.
- **Validar el ranking con los cierres de prensa.** La consecuencia mide qué pasa si un tramo se cierra, no si se cierra; que los cierres reales coincidan con tramos «críticos» no prueba nada sobre la consecuencia. Las fechas siguen siendo etiquetas, no semillas (D3).

## 6. Preguntas abiertas

- ¿La unidad de cierre se define por kilómetros (cadenado) o por uniones del grafo? Decide el spec del paso 5.
- ¿Quién hace la revisión manual del paso 2? Sin una persona con conocimiento de la zona, el paso se queda en «artefactos de ajuste detectados por reglas».
- Lista de hospitales de referencia: pendiente de Ian (`STATUS.md`). Los pasos 1 y 2 dependen de ella.
- Umbrales fijados: 80 % de aislados reales (paso 2), error relativo mediano ≤ 25 % (paso 3), top 5 con al menos 4 en común (paso 1), 90 % de comunidades con población (paso 4), cierres de ~5 km (paso 5).
