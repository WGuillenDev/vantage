# VANTAGE — SPIKING

> Guía de orden y registro de resultados de la fase 2 (sáb 14 nov, 11:00–15:00, hora de Costa Rica).
> Sirve para tres cosas: **qué hacer y en qué orden**, **qué depende de qué**, y **dejar el resultado de cada spike en un solo lugar** para decidir en la Puerta 1 (G1, sáb 15:00).
> `STATUS.md` sigue siendo el tablero (estado `[ ]`/`[~]`/`[x]` y dueños). Este archivo guarda el detalle y la evidencia. Si algo no coincide, `STATUS.md` manda para dueños y estado.

## Reglas

- Un spike termina con un **veredicto** (`PASA`, `FALLA → plan B` o `PARCIAL`) y **evidencia** (enlace, comando, captura o archivo). Sin evidencia no se marca hecho.
- No inventes datos: un valor desconocido se escribe `pendiente` o `null`, nunca un número o fecha supuesta.
- Lenguaje cauto: «candidato», «señal», «hipótesis». Nunca «cierre confirmado» ni «causado por la lluvia».
- No se commitean datos crudos de NISAR, rásters grandes ni credenciales. Solo se anota dónde están y cómo se obtuvieron.
- Al terminar un spike: llená su ficha abajo, actualizá su fila en `STATUS.md` (columna «Resultado», una línea) y anotá el relevo si cambia de manos.
- Si un spike falla, pasá a su plan B y registrá la decisión en el Registro de decisiones de `STATUS.md`.

## Dueños

| Spike | Dueño | Ventana |
|---|---|---|
| S3 Evento de validación | R | 11:00–11:30 |
| S1 Cobertura de NISAR | R | 11:30–12:30 |
| S2 Resolución y detectabilidad | R | 12:30–14:00 |
| S4 Red vial y métrica | I | 11:00–13:00 |
| S5 IMERG | I | 13:00–15:00 |
| S6 Prueba de humo del frontend | W, V | 13:30–15:00 |
| S7 Acceso a población (WorldPop) | W | durante el spiking |
| S8 `graph.ts` | V | durante el spiking |

## Dependencias

No son totalmente independientes. Hay un camino crítico y el resto corre en paralelo.

```
S1 ──► S2            S2 necesita las dos pasadas que encuentra S1
 ▲
 └──── S3            se retroalimentan: S1 busca fechas que encierren el cierre real,
                     S3 confirma con fuente oficial que ese cierre existió y cuándo

S5  ·· (usa las fechas de S1, pero se puede probar con cualquier día de lluvia)

S4   independiente (OSM, sin NISAR)
S6   independiente (mock del contrato)
S7   independiente (WorldPop)
S8   independiente (usa el mock; después se contrasta con la salida de S4)
```

| Spike | Necesita | Desbloquea | ¿Puede empezar ya? |
|---|---|---|---|
| S1 | pista de S3 (fecha del evento) | S2, P1, fechas para S5 | Después de S3 (mismo dueño, 11:30) |
| S2 | pasadas de S1 | P2 | No, espera a S1 |
| S3 | — (idealmente S1 en paralelo) | acotar S1, el relato de validación | Sí |
| S4 | — | P3, P4, P5 | Sí |
| S5 | fechas de S1 (para el resultado final) | P6, F6 | Sí, con un día cualquiera |
| S6 | — | F1, F7 | Sí |
| S7 | — | P5 (población), F4 | Sí |
| S8 | — | F3, F4, F5 | Sí |

## Orden de trabajo sugerido

R lleva toda la cadena S3 → S1 → S2, así no hay relevos entre personas en el camino crítico. I queda libre para S4 y S5.

1. **11:00** Arrancan en paralelo: R con S3 (corto: solo la fecha y la fuente del evento), I con S4, W con S6 y S7, V con S8.
2. **11:30** R pasa a S1 con la fecha de S3. Si S3 no da fecha, S1 busca con el evento candidato y se anota.
3. **12:30** R pasa a S2 con las pasadas de S1. Si S1 aún no entrega pasadas, S2 espera; no la adivines.
4. **13:00** I pasa a S5 con las fechas de S1/S3. W y V cierran S6 (meta 15:00).
5. **14:00** Todos llenan sus fichas; R consolida la tabla de resultados.
5. **15:00** G1: se decide con la tabla de abajo.

## Criterios de la Puerta 1

| Pregunta de G1 | Se responde con | Si no se cumple |
|---|---|---|
| ¿Hay pasadas compatibles de NISAR? | S1 | Otro evento u otra zona dentro de Costa Rica |
| ¿Se nota el cambio? | S2 | Zonas de perturbación a escala de ladera |
| ¿El evento tiene respaldo oficial? | S3 | Presentar todo como «candidatos» |
| ¿La red vial da números razonables? | S4 | Red regional hasta Limón; si es lenta, simplificar por clase de vía |

S5, S6, S7 y S8 no deciden G1 por sí solos: si fallan, se aplica su plan B y se sigue.

## Resumen de resultados

Se llena al terminar cada spike. Una línea por spike.

| Spike | Veredicto | Resultado en una línea | Hora | Quién |
|---|---|---|---|---|
| S1 | pendiente | — | — | — |
| S2 | pendiente | — | — | — |
| S3 | pendiente | — | — | — |
| S4 | PARCIAL | Red regional conecta y un corte en el parque da +77,6 min San José→Guápiles por alterna; con área solo-corredor hay aislamientos falsos, y la métrica «hospital más cercano» da 0 comunidades afectadas en el parque (redes hasta -83.40; hasta Limón, 1 aislada sin revisar). Ninguna de las 18 aisladas del corte Guápiles–Siquirres es real (revisión a mano) | 13:40 | I (agente) |
| S5 | pendiente | — | — | — |
| S6 | PASA | Mapa base y overlay de cambio visibles en local, build y Pages, sin errores de consola | — | W, V |
| S7 | PASA | WorldPop CRI 2020 (100 m) se descarga completo y se recorta al corredor; hay población | 14:18 | W |
| S8 | PASA | `graph.ts` coincide con la línea base y con los 4 candidatos del mock, incluido el aislamiento de c4 en T-03 | — | V |

---

## Fichas por spike

Copiá la plantilla en cada ficha al terminar. Dejá `pendiente` en lo que no sepas.

### S1 · Cobertura de NISAR sobre la Ruta 32

- **Objetivo:** dos fechas con el mismo track, dirección y CRID que encierren un cierre real, fuera del hueco del 27 jul–10 ago.
- **Plan B:** otro evento u otra zona dentro de Costa Rica.
- **Depende de:** S3 (fecha del evento). **Desbloquea:** S2, P1.
- **Qué esperar:** pocas pasadas compatibles; la revisita no es diaria. Anotá también las que no sirvieron y por qué.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Pasada «antes» (fecha, track, dirección, CRID) | pendiente |
| Pasada «después» (fecha, track, dirección, CRID) | pendiente |
| Cuántas pasadas compatibles hay en total | pendiente |
| Cómo se consultó (producto, herramienta, comando) | pendiente |
| Evidencia (enlace/archivo) | pendiente |
| Notas / riesgos | pendiente |

### S2 · Resolución y detectabilidad

- **Objetivo:** una mancha coherente de varios píxeles sobre un derrumbe conocido.
- **Plan B:** zonas de perturbación a escala de ladera.
- **Depende de:** S1. **Desbloquea:** P2.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Derrumbe o sitio de referencia usado | pendiente |
| Tamaño aproximado de la mancha (píxeles) | pendiente |
| ΔdB observado (rango) | pendiente |
| Ruido de fondo / falsos positivos vistos | pendiente |
| Evidencia (captura/archivo) | pendiente |
| Notas / riesgos | pendiente |

### S3 · Evento de validación

- **Objetivo:** una fuente oficial (MOPT, CONAVI, CNE) respalda la fecha del cierre.
- **Plan B:** presentar todo como «candidatos».
- **Depende de:** nada. **Desbloquea:** acotar S1 y el relato de validación.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Evento (lugar y descripción) | pendiente |
| Fecha(s) según la fuente | pendiente |
| Fuente (institución, enlace, fecha de publicación) | pendiente |
| ¿Cierra la fecha entre las pasadas de S1? | pendiente |
| Notas / riesgos | pendiente |

### S4 · Red vial y métrica de impacto

- **Objetivo:** el grafo conecta; quitar un tramo da números razonables.
- **Plan B:** red regional hasta Limón; si es lenta, simplificar por clase de vía en lugar de recortar el área.
- **Depende de:** nada. **Desbloquea:** P3, P4, P5.

| Campo | Valor |
|---|---|
| Veredicto | PARCIAL: el grafo y la métrica funcionan sobre un área regional; quedan aislamientos dudosos en los bordes del área |
| Área y fuente (OSM, fecha de descarga) | OSM vía Overpass (OSMnx 2.1.1), descargado el 14 nov 2026. Clases `motorway`…`unclassified` (+ `_link`), sin `residential`. Corredor `[-84.10, 9.90, -83.72, 10.25]` y regional `[-84.30, 9.80, -83.40, 10.45]` (con Ruta 126 y Ruta 10). Ruta 32 en OSM: `ref=32`, 281 vías `trunk`, de (-84.08, 9.94) a (-83.02, 10.22) |
| Nodos / aristas / componentes conexas | Corredor: 1 687 nodos, 2 216 aristas, 74 componentes (la mayor tiene el 89,6 % de los nodos). Regional: 6 124 nodos, 7 068 aristas, 590 componentes (la mayor tiene el 73,4 %). `graph.json` estimado para el corredor: ~990 KB, o ~540 KB con geometría simplificada a ~10 m |
| Hospitales y comunidades encontrados | `amenity=hospital`: 27 (corredor) / 63 (regional), con ruido (clínica dental, banco de sangre, psiquiátrico, privados); `amenity=clinic` 211 / 537; `amenity=doctors` 43 / 195. Hospital Guápiles = `way/326924912`. Comunidades `place=city/town/village/hamlet`: 124 / 718; distancia al nodo más cercano p50 / p90 / máx = 462 / 2 047 / 7 018 m (corredor) y 783 / 2 896 / 10 089 m (regional) |
| Caso de prueba: tramo quitado → tiempo extra / aislamiento | (1) Ruta 32 dentro del parque (una sola arista simplificada de 34,5 km): 0 comunidades afectadas en las dos áreas de este spike, la del corredor (borde este -83.72) y la regional (borde este -83.40). Ninguna de las dos es la red del plan B (hasta Limón, borde este -82.95): ahí la medición para G1 da 1 comunidad afectada en ese tramo, aislada y sin revisar a mano; Hospital Calderón Guardia → Hospital Guápiles pasa de 68,8 a 146,4 min en el regional (+77,6 min por alterna) y queda SIN camino en el corredor. (2) Ruta 32 entre Guápiles y Siquirres (lon -83.70 a -83.55, 20,3 km), en la regional hasta -83.40: 51 afectadas, 33 con tiempo extra (mediana 21,2 min, máx 72,8 min) y 18 aisladas; la revisión a mano (fila siguiente) muestra que ninguna de las 18 es real |
| ¿Los números son razonables? (revisado a mano) | Sí la línea base San José→Guápiles (68,8 min) y el desvío (+77,6 min). Revisión a mano de las 18 aisladas del caso 2 (`review_isolated.py`: red hasta Limón con aristas ≤ 1 km, mismos hospitales y mismo corte): **ninguna es un aislamiento real**. 3 (La Isleta, Las Colinas, La Argentina) quedan fuera del grafo por estar a más de 3 km de una vía. 2 dejan de estar aisladas: Portón de Iberia pasa a +67,5 min hacia el Hospital William Allen Taylor y Trinidad no se ve afectada. 6 (Parismina, Mercedes, Pocora, Altos de Germania, Germania, Herediana) están ajustadas a un nodo de la propia Ruta 32 cortada y quedan en un componente de 1 o 2 nodos, porque el grafo no tiene sus calles locales. 7 (Codela, Milano, Bellavista, El Cairo, Louisiana, El Peje, 3 Millas) siguen unidas a la red y a los hospitales sin mirar el sentido de las vías, pero no tienen ruta dirigida: probable artefacto de tramos de un solo sentido (`oneway`) |
| Medición para G1 (14 nov, ~14:35) | Red real hasta Limón (extracto OSM del 14 nov, `road_graph.build` de P3): 7 136 nodos, 8 715 aristas, 758 comunidades, 7 sin camino en la línea base. Tramos de prueba: Ruta 32 y las 17 rutas numeradas que la tocan, partidas en cruces → 495 tramos; quitados uno a la vez con la métrica de la spec de impact-scoring. **`criticality > 0`: 0** (población `null` en todas). Con alguna comunidad afectada: 280 (57 %); con `extra_time_s > 0`: 229; con aisladas: 99; **empatan en 0 (nadie afectado): 215 (43 %)**. Solo Ruta 32: 191 tramos, 115 afectan a alguien, 44 con aisladas, 76 en 0. El tramo del parque (34,5 km) afecta a 1 comunidad, que queda aislada. Supuestos SOLO de esta medición: `unclassified` a 30 km/h y hospitales = `amenity=hospital` con nombre «Hospital…» (25). Las aisladas no se revisaron a mano. Script y comando exacto: `projects/pipeline/spikes/s4/g1_measure.py` (README) |
| Notas / riesgos | Velocidad del spike: mediana OSM `maxspeed` por clase (trunk 60; primary, secondary y tertiary 40; unclassified 30 con solo 20 de 2 319 aristas etiquetadas). Riesgo G1: con «hospital más cercano», un corte en el parque no afecta a ninguna comunidad (hospitales a ambos lados). El plan B «reducir al corredor» empeora el resultado: crea aislamientos falsos. Riesgo para P3 y P5 (fase 3): aislamientos falsos por comunidades ajustadas a un nodo de la vía cortada y por tramos de un solo sentido. Evidencia: scripts y comandos exactos en `projects/pipeline/spikes/s4/` (README); las descargas no se commitean |

### S5 · IMERG

- **Objetivo:** un día de lluvia descargado y graficado.
- **Plan B:** lluvia solo como texto.
- **Depende de:** fechas de S1 (para el resultado final). **Desbloquea:** P6, F6.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Producto y versión IMERG | pendiente |
| Acceso (autenticación, herramienta) | pendiente |
| Día(s) descargado(s) | pendiente |
| Agregación (`area_mean` del corredor) | pendiente |
| Evidencia (gráfico/archivo) | pendiente |
| Notas / riesgos | pendiente |

### S6 · Prueba de humo del frontend

- **Objetivo:** MapLibre carga un mock del contrato, en local y desplegado.
- **Plan B:** resolver antes de seguir.
- **Depende de:** nada. **Desbloquea:** F1, F7.

| Campo | Valor |
|---|---|
| Veredicto | PASA |
| Local (`bun run dev`) | OK: mapa base y overlay de cambio visibles, sin errores de consola |
| Build local (`bun run build` + `bun run preview`) | OK: mismo resultado que dev |
| Desplegado (URL de Pages) | OK: https://wguillendev.github.io/vantage/ — overlay visible, sin errores de consola |
| Errores de consola | Ninguno, en los tres casos |
| Notas / riesgos | — |

### S7 · Acceso a población (WorldPop)

- **Objetivo:** funciona, o se elige el respaldo (solo tiempo extra y conteo de comunidades, con `population: null`).
- **Depende de:** nada. **Desbloquea:** P5 (población), F4.

| Campo | Valor |
|---|---|
| Veredicto | PASA |
| Producto y resolución | WorldPop, Costa Rica 2020, personas por píxel (`cri_ppp_2020.tif`), ~100 m (3 arcseg), EPSG:4326, nodata −99999 |
| Forma de acceso (descarga, API, recorte al corredor) | Descarga directa por HTTPS de `https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/CRI/cri_ppp_2020.tif` (31,5 MB, sin cuenta ni clave). El servidor no admite lectura por rangos (responde 200, no 206), así que no hay streaming: se descarga entero y se recorta con `rasterio` (ventana por `bbox`). No se commitea el `.tif` |
| Población total del corredor (si se pudo) | 946 290 personas dentro del `bbox` provisional `[-84.20, 9.95, -83.70, 10.30]` (600×420 px, 251 862 píxeles válidos, máximo 181,8 personas/píxel). Cifra del `bbox` de ejemplo, no del corredor final |
| Decisión: usar WorldPop o respaldo | Usar WorldPop. El respaldo (`population: null`) sigue soportado por el contrato |
| Notas / riesgos | La población por comunidad se asigna sumando píxeles cercanos al nodo (criterio de P5, por decidir). El `bbox` real sale de S1/P1. El producto es una estimación modelada de 2020, no un censo: rotular como estimación. `rasterio` no está en `pyproject.toml`; se añade en P5 si hace falta. Probado solo en esta máquina |

### S8 · `graph.ts`

- **Objetivo:** camino más corto al hospital más cercano, con conjunto de tramos cerrados; coincide con el `scenarios.json` mock en la línea base.
- **Depende de:** nada (se contrasta con S4 después). **Desbloquea:** F3, F4, F5.

| Campo | Valor |
|---|---|
| Veredicto | PASA |
| ¿Coincide con el mock en la línea base? | Sí: `computeAccess(graph, [])` es idéntico al `baseline` de `scenarios.json` (5 comunidades, mismo `time_s` y `hospital_id`) |
| Casos de cierre probados | Los 4 candidatos del mock coinciden con su `per_community`: T-01 (e2), T-02 (e3), T-03 (e9) y T-04 (e4). En T-03, c4 queda aislada (`time_s: null`, `hospital_id: null`). También se probó una vía de un solo sentido (`oneway: true`) |
| Rendimiento (tiempo de recálculo) | Mock (9 nodos): ~0,03 ms por llamada (1000 llamadas en 27 ms). Grafo sintético de 10 000 nodos y 50 comunidades: ~230 ms, medido una vez con `bun`, no en navegador |
| Notas / riesgos | Un Dijkstra por comunidad; si el grafo real es grande y el recálculo se nota al cerrar tramos, pasar a una sola búsqueda desde los hospitales. Con hospitales a igual tiempo gana el primero de la lista. Solo contrastado con el mock; falta cruzarlo con el grafo real de S4. `*.test.ts` queda fuera de `tsc -b` porque los tipos de `bun:test` no están instalados |

---

## Decisión en G1

Se llena el sáb 15:00 con el agente, leyendo la tabla de resultados.

| Campo | Valor |
|---|---|
| Hora | pendiente |
| Decisión | pendiente — seguir / plan B |
| Planes B activados | pendiente |
| Ajustes a las tareas de la fase 3 | pendiente |
| Registrado en `STATUS.md` (Registro de decisiones) | pendiente |
