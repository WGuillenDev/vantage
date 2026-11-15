# VANTAGE — Plan de fiabilidad (borrador)

> Nota de trabajo, no es un spec. Los umbrales de «Terminada cuando» quedaron **fijados el 14 nov** por R, por escrito antes de calcular, como en `SPIKING.md`; si cambian, se registra una versión nueva, nunca en silencio.
> Alcance por ahora: **solo Costa Rica**, con la Ruta 32 como caso. Fecha: 14 nov 2026.

## Versión 2 (15 nov 2026): estado, desviaciones y determinismo

La v1 de abajo queda como se escribió el 14 nov. Cambios y resultados, sobre la Ruta 32:

| Paso | Estado | Resultado |
|---|---|---|
| 5 Unidad fina | [x], con desviación | 115 unidades por uniones del grafo, con las dos calzadas, de 15 m a 34,5 km. Sin tope de ~5 km (desviación 1) |
| 4 Población | [x] | 758 de 758 comunidades con valor; 2 899 678 asignados frente a 2 957 560 del ráster (−1,96 %, margen ±5 %) |
| 2 Revisión manual | [x], veredicto `fail` | 0 de 4 aislamientos reales; los 4 son `snapping_artifact`. Corregir los sospechosos (excluirlos o reenganchar) deja el top 10 igual (`planning.md`, D4), así que no se toca el modelo |
| 1 Sensibilidad | [x], `pass` | Velocidad ×0,8 y ×1,2 y quitar cada hospital: top 5 y top 10 iguales. Distancia de ajuste 1 500, 3 000 y 5 000 m: top 5, 10 y 20 iguales, correlación ≥ 0,999 (desviación 2) |
| 3 Contraste de tiempos | [x], `pass` | 20 pares contra OSRM, error relativo mediano 15,3 % (sesgo −15,2 %); 4 referencias citadas con errores de 12 %, 33 %, 34 % y 10 % |
| 6 Marcas de confianza | [x] | La interfaz marca los aislamientos sospechosos, redondea los tiempos y dice «sin ruta al hospital de referencia» |

**Desviaciones respecto de v1** (decididas en los specs el 14 nov; aquí quedan registradas):

1. **Sin tope de ~5 km.** Cortar a una longitud fija en medio de un tramo sin uniones pone los cortes en puntos arbitrarios, y dónde se corta decide qué comunidades quedan enganchadas al tramo cerrado, que es justo el artefacto medido en el paso 2. Los cortes caen en uniones reales de la red y salen de una regla fija. Hay 6 unidades de más de 5 km; la mayor, de 34,5 km, es un tramo sin uniones (T-24).
2. **La perturbación de la distancia de ajuste no está en la etapa `rank-sensitivity`.** Re-ajustar exige repetir tres etapas, así que el spec la quitó. Se midió aparte con `projects/pipeline/spikes/snap_distance/measure.py`, que copia el pipeline a una carpeta temporal, cambia `MAX_SNAP_M` y compara con la salida real; el control de 3 000 m reproduce la salida real exactamente. Resultado: con 1 500 m hay 643 comunidades, con 3 000 m 758 y con 5 000 m 799, y el ranking de cabeza no cambia. La proporción de aislamientos sospechosos tampoco depende de la distancia (20,5 %, 21,6 % y 21,9 %). La cobertura sí cambia mucho; el orden no.
3. **El tercer cierre revisado a mano es «el más largo»**, regla fijada antes de mirar resultados; en la Ruta 32 es el tramo T-24 (34,5 km), que recorre la zona del parque Braulio Carrillo.

**Reservas que el `pass` no quita:** el factor de velocidad es uniforme, así que casi no puede cambiar el orden; y quitar un hospital solo habla de los tres de San José, que están juntos. Con Tony Facio y Guápiles añadidos el top 20 no coincide en ninguno (`planning.md`, D5): el ranking es un resultado sobre el acceso a los hospitales nacionales.

**Determinismo y trazabilidad.** Verificado el 15 nov:

- `graph.json`, `scenarios.json` y `rain.csv` salen idénticos byte a byte entre corridas y con distintas semillas de hash (la causa de la diferencia era el orden de nombres y clases de aristas fusionadas, ya corregido). `meta.json` solo cambia en `generated_at`.
- `make inputs AREA=ruta-32` escribe `reports/ruta-32/inputs.json` con el SHA-256 y el tamaño de la configuración, el extracto OSM, el ráster WorldPop, las celdas IMERG y las tres salidas. `make inputs-check AREA=ruta-32` comprueba que siguen coincidiendo: tras regenerar con `make all` la comprobación pasa. Los textos se normalizan a LF para que el hash sea igual en Windows y Linux.
- **Lo que no es determinista por naturaleza:** las descargas (Overpass devuelve datos vivos, IMERG Late puede revisarse), el router OSRM público y `generated_at`. Se registran las fechas del extracto y de la consulta, y los hashes permiten ver si una entrada cambió.
- **Límite:** la comprobación corre en local, no en CI, porque `work/` no se versiona (14,8 MB de OSM y 31,5 MB de ráster). La salida se generó en Windows y el CI no la regenera.

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
| 5 | **Unidad de cierre fina** (hoy 19 cierres de 1 a 61 km) | Convierte «este corredor es crítico» en «este tramo es crítico» | 2–3 h, **requiere spec** | — | [x] (v2) |
| 4 | **Población** (E4, WorldPop sobre las comunidades) | `criticality` deja de ser 0; «crítico» pasa a significar «mucha gente depende» | ya en el plan | — | [x] (v2) |
| 2 | **Revisión manual de 3 cierres** | Lo que más falta: ningún caso se ha revisado a mano | 1–2 h | 5 | [x] (v2) |
| 1 | **Análisis de sensibilidad** | «El ranking es estable ante estos supuestos» | 1–2 h | 5, 4 | [x] (v2) |
| 3 | **Contraste de tiempos con fuente externa** | Detecta si las velocidades constantes se alejan de la realidad | 1 h | — (en paralelo) | [x] (v2) |
| 6 | **Marcas de confianza en la interfaz** | No sube la exactitud; sube la honestidad con que se lee | 1 h | 2 | [x] (v2) |

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

Resueltas el 15 nov (v2): la unidad de cierre se define por uniones del grafo; la revisión manual la hizo R con apoyo de mapas por comunidad; la lista de hospitales de referencia es la de D9 (`STATUS.md`). Los umbrales de arriba se mantuvieron sin cambios, salvo las dos desviaciones registradas en la v2.
