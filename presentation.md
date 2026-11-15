# VANTAGE — Guion de la presentación

> Borrador para ensayar (tarea X4). Todos los números salen de los informes del repositorio; la fuente va entre paréntesis. Duración objetivo: 5 minutos más preguntas. Está en español; la entrega a Space Apps puede requerir inglés.

## Idea en una frase

VANTAGE muestra qué tramos de un corredor vial, si se cortan, dejan a comunidades sin ruta a un hospital de referencia, y cuánto tiempo extra implica. Caso de demostración: la Ruta 32 (San José–Limón).

## 1. El giro (60 s): lo que intentamos y no funcionó

Empezamos para el reto «Dancing with the SARs» con una pregunta: ¿puede NISAR ayudar a anticipar derrumbes en la Ruta 32? Escribimos los criterios antes de calcular y probamos tres señales. Ninguna funcionó:

| Señal | Resultado | Fuente |
|---|---|---|
| NISAR GCOV a 10 m para detectar cambio a escala de derrumbe | Mínimo detectable ≈ 1 ha a −5 dB: no se ven derrumbes pequeños con este flujo | `SPIKING.md` S2 |
| Humedad del suelo SME2 antes de un cierre | Sobre su p75 en 2 de 6 cierres (se pedían 5) | `SPIKING.md` S2c |
| Lluvia IMERG de los 12 días previos | Sobre su p75 en 3 de 8 cierres (se pedían 6) | `SPIKING.md` S5 |

Decir claramente: **no afirmamos que NISAR no pueda**. GUNW, offsets y series por píxel quedan sin probar. Lo que mostramos es que este flujo con GCOV a 10 m no alcanza.

## 2. Qué construimos en su lugar (60 s)

Cambiamos la pregunta de «¿dónde se va a caer?» a «¿qué pasa si se corta?»: la **consecuencia**. Con la red vial de OpenStreetMap, tres hospitales de referencia y población estimada (WorldPop), cortamos cada tramo y medimos quién pierde la ruta y cuánto tiempo extra. La lluvia reciente (IMERG) se muestra solo como **contexto**, etiquetada como hipótesis.

El método está pensado para cualquier corredor con red en OSM; **solo se demostró en la Ruta 32**.

## 3. Demostración (90 s)

Sitio publicado, con datos reales. Guion:

1. Mapa y lista: 115 unidades de cierre, 100 con impacto. Aviso visible: «tramos críticos por consecuencia; no son derrumbes confirmados». Banner: «zona no validada».
2. Abrir el primer tramo (T-20, 168 m): ≈ 3 h 35 min extra, ~377 mil personas que dependen (estimadas).
3. Pestaña Simulación: cerrar un tramo y ver el recálculo instantáneo en el navegador, sin servidor.
4. «Cómo leer estos números»: velocidades, hospitales de referencia y la nota de que el orden depende de ese conjunto.
5. Pestaña «¿Por qué?»: la lluvia, con la etiqueta «Hipótesis, no causa confirmada».

## 4. Cuánto confiar en esto (60 s): lo que medimos

Parte del producto, no una disculpa. Decir solo las tres filas; el resto va a preguntas:

| Prueba | Resultado |
|---|---|
| Tiempos contra el router OSRM (20 pares) | Error relativo mediano 15,3 % (umbral 25 %); el modelo es ~15 % más rápido |
| Revisión manual de aislamientos (4 comunidades) | **0 reales**: las 4 son artefactos de enganche (`fail`). Excluir los 208 sospechosos (21,6 %) deja el top 10 igual |
| Cambiar el conjunto de hospitales (añadir Limón y Guápiles) | El top 20 no coincide en ninguno: **el ranking es un resultado sobre el acceso a los hospitales nacionales de San José**, no sobre «criticidad general» |

Por eso la zona se publica como «no validada».

## 5. Límites que decimos nosotros antes de que pregunten

- Una sola zona demostrada. «Hospital de referencia» puede no trasladarse a otro país.
- La red no trae caminos locales: algunos «sin ruta» son artefactos (marcados en la aplicación).
- Tiempos de límites publicados, no de viaje; `unclassified` se apoya en 22 vías etiquetadas.
- Limón queda sin ruta en 22 unidades, todas al este de Siquirres (único tramo sin alternativa); Limón tiene su hospital, que no cuenta como referencia.
- Probado en un viewport móvil emulado, no en celular físico.

## 6. Cierre (30 s)

Tres resultados negativos con su número, un producto que responde una pregunta distinta y útil, y un conjunto de pruebas que dicen cuánto confiar en él. Reproducible: `make osm worldpop imerg all publish`, todo en el repositorio, MIT.

## Preguntas probables

- **¿Predice derrumbes?** No. Muestra consecuencia de un corte; la lluvia es contexto y no se probó como señal.
- **¿Por qué no usaron más NISAR?** Probamos la detección con GCOV; no alcanzó. Se descartó con un número, y GUNW y otras vías quedan abiertas.
- **¿Funciona en otro lugar?** Está diseñado para ello (la zona es un archivo de configuración), pero solo se probó en la Ruta 32.
- **¿Por qué esos tres hospitales?** Son los hospitales nacionales; es un supuesto de modelo y lo medimos: con otros, el ranking cambia por completo.
- **¿El ranking es estable?** Sí ante velocidades ×0,8/×1,2 y al quitar cada hospital (top 5 y top 10 iguales), con la reserva de que el factor de velocidad es uniforme y casi no puede cambiar el orden.
- **¿Qué tan exactos son los tiempos?** Del orden de magnitud: límites publicados, ~15 % más rápidos que el router; mostramos «≈» y se redondea a múltiplos de 5 min.
- **¿Está validado?** No: la revisión manual dio 0 de 4. Lo decimos en la aplicación.
