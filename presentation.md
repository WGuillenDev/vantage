# VANTAGE — Guion de la presentación

> Para ensayar (tarea X4). Duración: **30 segundos**, más preguntas. Todos los números del respaldo salen de los informes del repositorio; la fuente va entre paréntesis. Está en español; la entrega a Space Apps puede requerir inglés.

## Guion (30 s, unas 70 palabras)

> Quisimos usar NISAR para anticipar derrumbes en la Ruta 32. Probamos tres señales con criterios escritos de antemano: ninguna funcionó, y lo reportamos con su número. Entonces cambiamos la pregunta: ¿qué pasa si se corta un tramo? VANTAGE muestra qué tramos críticos, si se cortan, dejan a comunidades sin ruta a un hospital de referencia, y cuánto tiempo extra implica. Solo lo probamos en la Ruta 32, y la zona aparece como no validada.

Mientras se habla: el sitio publicado con el primer tramo (T-20) abierto.

Reglas: decir «tramo crítico» y «señal»; nunca «cierre confirmado», «causado por la lluvia» ni «funciona en cualquier lugar». Lo que no cabe en 30 s no se improvisa: va a las preguntas.

---

## Respaldo para preguntas (no se dice en los 30 s)

### Los tres resultados negativos

Decir claramente: **no afirmamos que NISAR no pueda**. GUNW, offsets y series por píxel quedan sin probar.

| Señal | Resultado | Fuente |
|---|---|---|
| NISAR GCOV a 10 m para detectar cambio a escala de derrumbe | Mínimo detectable ≈ 1 ha a −5 dB: no se ven derrumbes pequeños con este flujo | `SPIKING.md` S2 |
| Humedad del suelo SME2 antes de un cierre | Sobre su p75 en 2 de 6 cierres (se pedían 5) | `SPIKING.md` S2c |
| Lluvia IMERG de los 12 días previos | Sobre su p75 en 3 de 8 cierres (se pedían 6) | `SPIKING.md` S5 |

### Cuánto confiar en esto

| Prueba | Resultado |
|---|---|
| Tiempos contra el router OSRM (20 pares) | Error relativo mediano 15,3 % (umbral 25 %); el modelo es ~15 % más rápido |
| Revisión manual de aislamientos (4 comunidades) | **0 reales**: las 4 son artefactos de enganche (`fail`). Excluir los 208 sospechosos (21,6 %) deja el top 10 igual |
| Cambiar el conjunto de hospitales (añadir Limón y Guápiles) | El top 20 no coincide en ninguno: **el ranking es un resultado sobre el acceso a los hospitales nacionales de San José**, no sobre «criticidad general» |

Por eso la zona se publica como «no validada».

### Límites

- Una sola zona demostrada. «Hospital de referencia» puede no trasladarse a otro país.
- La red no trae caminos locales: algunos «sin ruta» son artefactos (marcados en la aplicación).
- Tiempos de límites publicados, no de viaje; `unclassified` se apoya en 22 vías etiquetadas.
- Limón queda sin ruta en 22 unidades, todas al este de Siquirres (único tramo sin alternativa); Limón tiene su hospital, que no cuenta como referencia.
- Probado en un viewport móvil emulado, no en celular físico.

### Preguntas probables

- **¿Predice derrumbes?** No. Muestra consecuencia de un corte; la lluvia es contexto y no se probó como señal.
- **¿Por qué no usaron más NISAR?** Probamos la detección con GCOV; no alcanzó. Se descartó con un número, y GUNW y otras vías quedan abiertas.
- **¿Funciona en otro lugar?** Está diseñado para ello (la zona es un archivo de configuración), pero solo se probó en la Ruta 32.
- **¿Por qué esos tres hospitales?** Son los hospitales nacionales; es un supuesto de modelo y lo medimos: con otros, el ranking cambia por completo.
- **¿El ranking es estable?** Sí ante velocidades ×0,8/×1,2 y al quitar cada hospital (top 5 y top 10 iguales), con la reserva de que el factor de velocidad es uniforme y casi no puede cambiar el orden.
- **¿Qué tan exactos son los tiempos?** Del orden de magnitud: límites publicados, ~15 % más rápidos que el router; mostramos «≈» y se redondea a múltiplos de 5 min.
- **¿Está validado?** No: la revisión manual dio 0 de 4. Lo decimos en la aplicación.
- **¿Cómo se reproduce?** `make osm worldpop imerg all publish`, todo en el repositorio, MIT.
