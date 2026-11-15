# VANTAGE — STATUS

> Tablero vivo. Corto y verdadero: actualizalo cuando una tarea cambie de estado.
> Contexto: `context/approach.md` (porqué y método), `structure.md`, `functions.md`, `contracts.md`. Resultados de spikes: `SPIKING.md`.
> Horas de Costa Rica (UTC−6). Ventana: **sáb 14 nov 09:00 → dom 15 nov 23:59** (hora de cierre por confirmar).
> **Equipo completo desde el cierre del día 1 (sáb 14 nov):** R hizo las fases 1 y 2 solo; la fase 3 se reparte entre R Ron · I Ian · W Wilberth · V Iván (columna «Dueño»). **Ian empieza por el pipeline** (ver «Quién empieza por dónde»).

Leyenda: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[-]` descartada (con motivo).

## Resumen de fases

| # | Fase | Cuándo | Objetivo | Estado |
|---|---|---|---|---|
| 1 | **Bootstrap** | Sáb 09:00–11:00 | Repo, herramientas, contrato y mocks, esqueleto desplegado | [x] |
| 2 | **Spiking** | Sáb 11:00–15:00 | Probar los supuestos riesgosos y decidir en la **Puerta 1** | [x] Cerrada: G1 NO-GO de detección; S2c y S5 (señal) FALLAN; S4′ solo pasa «hospital de referencia»; S3 queda parcial (sin comunicado primario) |
| 3 | **Building** | Sáb ~17:00 → dom 14:00 | Datos reales por el pipeline y UI completa sobre el contrato | [x] Cerrada (dom 15 nov): 18 de 18 deltas con spec aprobado y código en `main`; corrida real de la Ruta 32 publicada (P8); 996 pruebas de pipeline y 189 de frontend pasan |
| 4 | **Polish** | Dom 14:00 → cierre | Congelar, corregir errores, probar, desplegar, presentar | [x] Cerrada (dom 15 nov): G2 decidida (X1); sitio publicado verificado con datos reales (X2); README y etiqueta `v1.0` (X3); guion de 30 s ensayado (X4); entrega a Space Apps hecha (X5) |

**G1 decidida (sáb 14 nov ~16:35): NO-GO** para detectar derrumbes con GCOV de NISAR (mínimo detectable ≈10×10 px ≈ 1 ha a −5 dB; detalle en `SPIKING.md` S2 y `context/approach.md` §5). Tras los demás spikes (S2c, S4′, S5; ver `SPIKING.md`) ninguna señal de exposición anticipó los cierres, y el producto se redefine en la **D8**: es la **consecuencia (criticidad)** de cada tramo de la Ruta 32, con la lluvia IMERG como contexto etiquetado «hipótesis». «Riesgo = consecuencia × exposición» (D2) ya no se usa. La capa de radar es opcional y puede ir vacía.

Proyecto terminado: las cuatro fases están cerradas, todo está en `main` y la entrega a Space Apps está hecha.

## Progreso

**46 / 46 tareas · 100 %** `████████████████████` _(solo cuentan las `[x]`; las `[~]` aún no suman; las `[-]` descartadas no cuentan)_

| Fase | Hechas | % |
|---|---|---|
| 1 · Bootstrap | 9 / 9 | 100 % |
| 2 · Spiking | 9 / 9 | 100 % |
| 3 · Building | 23 / 23 | 100 % |
| 4 · Polish | 5 / 5 | 100 % |

_Actualizá este bloque cada vez que marques una tarea `[x]`. Una tarea es `[x]` si su código está en `main`, sus pruebas pasan y cumple su «Terminada cuando». Hoy las 46 están hechas._

## Puertas

| Puerta | Cuándo | Pregunta | Decisión |
|---|---|---|---|
| G1 | Sáb 15:00 (decidida ~16:35) | ¿Hay pasadas compatibles de NISAR y se nota el cambio? | **NO-GO** en detección; el producto pasa a consecuencia × exposición (D1–D6), redefinido después en D8 |
| G2 | Dom 14:00 | Congelar funcionalidades: se corta lo que no esté listo | **Decidida (15 nov):** no se corta ninguna funcionalidad; la lista de no hechos y límites es la D11 |
| G3 | Dom 18:00 | Congelar código: solo corrección de errores | **15 nov:** el sitio publicado pasa el flujo principal sin errores (X2); desde aquí solo se corrigen errores |

---

## Fase 1 · Bootstrap (sáb 09:00–11:00) — completa

| ID | Tarea | Dueño | Estado |
|---|---|---|---|
| B1 | Repo público `vantage`, licencia MIT, README, `Makefile`, `.github/` | R | [x] |
| B2 | Herramientas: `uv` (pipeline) y Bun + TypeScript estricto (frontend) | R | [x] |
| B3 | Cerrar las 6 decisiones abiertas de `contracts.md` §11 | R | [x] |
| B4 | JSON Schemas en `projects/contract/schemas/` (hoy 0.2) | R | [x] |
| B5 | Mocks en `projects/contract/examples/`; `make mock` y `make validate` funcionando | R | [x] |
| B6 | `CODEOWNERS` sobre `contract/` (ver pregunta abierta sobre trabajar solo) | R, W | [x] |
| B7 | Esqueleto del frontend (React + Vite + MapLibre) cargando un mock | R, W | [x] |
| B8 | Workflow de GitHub Pages (`make mock` → `make validate` → build → publicar) | R | [x] |
| B9 | Archivos de contexto y `AGENTS.md` raíz | R | [x] |

## Fase 2 · Spiking (sáb 11:00–15:00; detalle en `SPIKING.md`)

| ID | Spike | Dueño | Estado | Resultado |
|---|---|---|---|---|
| S1 | Cobertura de NISAR | R | [x] | PASA con reservas: 069 D 1→13 jul; GCOV desde el 19 jun |
| S2 | Detectabilidad | R | [x] | **FALLA** → G1 NO-GO; mínimo detectable ≈1 ha a −5 dB |
| S2c | SME2: ¿sube antes de los cierres? | R | [x] | **FALLA**: 2 de 6 eventos sobre p75 en v2 (hacían falta 5; en v1 fueron 1 de 4); exposición solo con IMERG (D7). SME2 sí existe y cubre la ruta (S1′ PASA) |
| S3 | Eventos de validación | R | [x] | Cerrado con veredicto PARCIAL: prensa que cita al MOPT; sin comunicado primario en `mopt.go.cr` ni `conavi.go.cr`. Se corrigió la lista: el 17 jul sí hubo cierre; se añadieron el 8 oct y el 2.º episodio de feb |
| S4 | Red vial y métrica | R | [x] | PARCIAL: la red regional conecta (+77,6 min por alterna al cortar el parque); con «hospital más cercano» el parque afecta a 0 comunidades; recortar al corredor crea aislamientos falsos (ver `SPIKING.md`). **S4′ (red real, 191 tramos):** con una calzada por cierre todo falla; con las dos calzadas (19 cierres) pasa solo «hospital de referencia» (R2); ver `SPIKING.md` |
| S5 | IMERG | R | [x] | Lectura PASA (317 días); señal FALLA: 3 de 8 cierres sobre p75 de lluvia de 12 días (hacían falta 6), todos de ago–oct. La lluvia va como contexto, «hipótesis» (ver `SPIKING.md` S5) |
| S6 | Humo del frontend | W, V | [x] | PASA |
| S7 | WorldPop | W | [x] | PASA |
| S8 | `graph.ts` | V | [x] | PASA; ya está en `main` |

## Fase 3 · Building (sáb ~17:00 → dom 14:00)

### Deltas (specs)

Un delta por rebanada, en `projects/<proyecto>/deltas/<delta>.spec.md`. Nombres de dos palabras y 10–16 caracteres, en inglés (regla de ramas). Estado del spec: `[ ]` sin redactar · `[~]` redactado, en revisión · `[x]` aprobado (el visto bueno es llamar a `/builder`). Crítico = entra en el camino mínimo de entrega; el resto se corta en G2 si falta tiempo.

**Orden = de más fácil a más difícil de implementar** (esfuerzo: S pocas horas · M media jornada · L el más riesgoso). Cada delta se construye contra fixtures y el mock, así que el orden de facilidad se puede seguir; las dependencias solo mandan para la corrida real de punta a punta.

| # | Delta | Proyecto | Esfuerzo | Dueño | Cubre | Depende de | Crítico | Spec |
|---|---|---|---|---|---|---|---|---|
| 1 | `contract-update` | contract | S | R | C1 | — | sí | [x] |
| 2 | `area-config` | pipeline | S | I | E3 | — | sí | [x] |
| 3 | `zone-picker` | frontend | S | V | F11 | map-corridor, pipeline-run | no | [x] |
| 4 | `segment-ranking` | frontend | S | V | F3 | contract-update | sí | [x] |
| 5 | `trust-signals` | frontend | S | V | F8, F10 | segment-detail | F8 sí; F10 no | [x] |
| 6 | `time-crosscheck` | pipeline | S | V | P11 | road-graph | no | [x] |
| 7 | `rank-sensitivity` | pipeline | S | V | P10 | impact-scoring | no | [x] |
| 8 | `manual-review` | pipeline | S | R | P12 | impact-scoring | no | [x] |
| 9 | `mobile-layout` | frontend | M | W | F7 | map-corridor | no | [x] |
| 10 | `map-corridor` | frontend | M | W | F1 | contract-update | sí | [x] |
| 11 | `segment-detail` | frontend | M | W | F4, F6 | contract-update | sí | [x] |
| 12 | `closure-whatif` | frontend | M | V | F5 | segment-ranking | sí | [x] |
| 13 | `road-graph` | pipeline | M | I | P3 | area-config | sí | [x] |
| 14 | `impact-scoring` | pipeline | M | I | P5, E5 | closure-units, population-data | sí | [x] |
| 15 | `pipeline-run` | pipeline | M | R | P7, P8 | todos los del pipeline | sí | [x] |
| 16 | `population-data` | pipeline | M | W | E4 | road-graph | sí | [x] |
| 17 | `rain-context` | pipeline | M | I | E1 | area-config | no | [x] |
| 18 | `closure-units` | pipeline | L | I | P9 | road-graph | sí | [x] |

`graph.ts` (S8) pasa y no tiene delta propio; el 15 nov se cruzó con el grafo real: el cálculo del navegador coincide con el del pipeline en las 115 unidades (87 170 comprobaciones, 0 diferencias; 8,6 ms por simulación como máximo).

**Carga por persona** (reparto de la fase 3; se rebalancea si alguien se atrasa):

| Quién | Deltas | Total |
|---|---|---|
| **I Ian** (pipeline) | `area-config` S · `road-graph` M · `closure-units` L · `impact-scoring` M · `rain-context` M | 5 |
| **W Wilberth** (mapa y población) | `map-corridor` M · `segment-detail` M · `mobile-layout` M · `population-data` M (hizo S7) | 4 |
| **V Iván** (lista, simulación y confianza) | `segment-ranking` S · `trust-signals` S · `zone-picker` S · `closure-whatif` M (hizo `graph.ts`) · `time-crosscheck` S · `rank-sensitivity` S | 6 |
| **R Ron** (pocas, tras haber hecho fases 1 y 2) | `contract-update` S · `pipeline-run` M (con el primer despliegue, P8) · `manual-review` S; además README y entrega (X3, X5) | 3 |

**Quién empieza por dónde** _(plan del sáb 14 nov, ya ejecutado)_

1. **Ian:** `area-config` (no depende de nada) → `road-graph` (ya existe en `origin/feat/road-graph`; se porta a zonas) → `closure-units` (el más riesgoso: empezar temprano) → `impact-scoring` (ídem, en `origin/feat/impact-scoring`) → `rain-context`.
2. **R:** `contract-update` primero, porque los mocks y el validador por zona desbloquean a Wilberth y Iván; luego `pipeline-run` cuando haya etapas.
3. **Wilberth e Iván:** `map-corridor` y `segment-ranking` contra el mock 0.3 en cuanto `contract-update` lo tenga; hasta entonces, trabajar con el mock actual.

### Pipeline

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| P3 | Grafo vial de OSM para el área configurada: tramos, hospitales, comunidades → `graph.json` (spec: `projects/pipeline/deltas/road-graph.spec.md`) | I | [x] | Valida; los ids se cruzan. Hecho: portado a zonas (PR #31) y corrido sobre el extracto real de OSM del 15 nov: 7 136 nodos, 8 715 aristas, 758 comunidades y 3 hospitales de referencia (D9), ajustados a la mayor componente fuertemente conexa; hospitales y velocidades son parámetros de la zona. |
| E4 | Población WorldPop sobre las comunidades (para que la criticidad deje de dar 0) | W | [x] | `population` poblada donde hay dato (ACC-01: ≥ 90 % de comunidades con valor; ACC-02: total asignado dentro de ±5 % del ráster). Hecho (15 nov, PR #34): 758 de 758 comunidades con población; 2 899 678 asignados frente a 2 957 560 del ráster en el bbox (−1,96 %). |
| E5 | Decidir la métrica de impacto (hospital de referencia vs. más cercano; con el más cercano el parque da 0 comunidades afectadas) y revisar a mano la 1 aislada hasta Limón | R | [x] | Una sola cifra por tramo y la decisión anotada. Hecho (15 nov): métrica R2 (D8) y conjunto de referencia medido (D9). Limón queda sin ruta a un hospital de San José en 22 unidades, todas al este de Siquirres, el único tramo sin alternativa: explicado con los datos (D11). |
| P5 | Impacto: quitar un tramo a la vez → tiempo extra, población, aisladas, ranking → `scenarios.json` (clave `candidates`, `source: "network_consequence"`; spec: `projects/pipeline/deltas/impact-scoring.spec.md`) | I | [x] | Valida; un caso revisado a mano; sin aislamientos falsos. Cerrado con salvedad (15 nov): valida (PR #32), con revisión manual (P12) y las unidades de `closure-units`; los aislamientos falsos no desaparecen: se señalan (208 de 965 pares, 21,6 %) y se midió que excluirlos o reenganchar deja el top 10 igual (`planning.md`, D4). |
| E1 | IMERG: `rain.csv` y lluvia acumulada por tramo (`exposure.rain_mm_12d`) | I | [x] | Valida; las fechas cubren el periodo; no afirmar relación con los cierres. Hecho (15 nov, PR #35): `rain.csv` con 317 días (1 ene–13 nov), `exposure.rain_mm_12d` en las 115 unidades y 8 de 8 celdas iguales al granulo original de NASA (ACC-02). |
| E3 | Zona como parámetro (nombre o bbox en config → `meta.area`) | I | [x] | Cambiar el bbox cambia la salida sin tocar código. Hecho (PR #18). |
| P7 | `meta.json` y `make all` de punta a punta | R | [x] | `make all` regenera todo y `make validate` pasa. Hecho (15 nov, PR #33): `make all AREA=ruta-32` y `make publish validate` salen con 0, la salida es idéntica entre corridas y `meta.json` nombra la Ruta 32. |
| P8 | **Primer despliegue con datos reales** | R, W | [~] | El sitio publicado muestra datos reales (meta: sáb 21:00). 15 nov: `output/` real commiteado, `deploy.yml` corre `make publish`; desde un clon limpio pasan CI y los pasos del despliegue, y el build servido en local no muestra «MOCK» y sí aviso, banner de zona no validada y atribuciones. PR abierto. **Hecho (15 nov):** fusionado; el despliegue de `main` (`656051d`) termina bien y `graph.json`, `meta.json` y `scenarios.json` publicados en `wguillendev.github.io/vantage/storage/ruta-32/` tienen el mismo SHA-256 que `output/`. La vista en ventana privada queda en X2. |
| E2 | S2c (SME2), solo si sobra tiempo | R | [x] | FALLA (ver S2c); sin humedad en la exposición |
| P9 | Unidad de cierre fina: ambas calzadas, cortada en cada unión del grafo, más de 19 cierres (`RELIABILITY.md` paso 5; el tope de ~5 km se descartó, ver spec) | I | [x] | Spec aprobado; unidades por uniones, no por cadenado. Hecho (PR #36): 115 unidades sobre la red real, de 15 m a 34,5 km. |
| P10 | Sensibilidad: velocidad ×0,8/×1,2 y quitar cada hospital de referencia (paso 1; el ajuste a la red no se varía, ver spec) | V | [x] | Top 5 comparte ≥ 4 tramos en las dos de velocidad; quitar hospital se reporta, no se juzga. Hecho (15 nov): `make sensitivity AREA=ruta-32` (el comando faltaba), veredicto `pass`, top 5 y top 10 iguales en ×0,8, ×1,2 y al quitar cada hospital. También se midió la distancia de ajuste (1 500 y 5 000 m): top 20 igual (D13). Reservas: el factor de velocidad es uniforme y los tres hospitales están juntos (D9). |
| P11 | Contraste de tiempos con fuente externa (paso 3) | V | [x] | 15–20 pares y 3–5 referencias citadas; mediana del error relativo ≤ 25 %. Hecho (15 nov): 20 pares contra OSRM, error mediano 15,3 % (`pass`, sesgo −15,2 %: el modelo es más rápido) y 4 referencias citadas (errores de 12 %, 33 %, 34 % y 10 %). |
| P12 | Revisión manual de 3 cierres: mayor criticidad, mediano y el más largo (paso 2) | R | [x] | ≥ 80 % de las aisladas reales; artefactos corregidos y vuelto a medir. Hecho con veredicto `fail` (15 nov): 4 comunidades aisladas de 3 unidades, clasificadas por R con `reports/ruta-32/review_maps.html`: 0 reales, 4 `snapping_artifact`. Corregir los sospechosos no cambia el top 10 (D10), así que no se toca el modelo. |

Descartadas `[-]`: **P1** (obtener pasadas GCOV) y **P2** (detección de cambio como generador de candidatos): la detección no genera tramos (G1). **P4** (tramos candidatos por zona de cambio) se fundió en P5: los tramos salen de la red.

### Frontend

Las nueve tareas F están `[x]`: código y pruebas en `main` (PRs #19–#21, #25–#27, #30), verificadas con los datos reales de la Ruta 32 (189 pruebas, `tsc` estricto, lint y build limpios, `bun audit` sin hallazgos). Solo falta la prueba en un celular físico (X2).

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| F1 | Mapa con tramos críticos, hospitales y comunidades (sin capa de radar: nada la produce) | W | [x] | Se dibuja desde el contrato. Hecho en `main` (PR #26) |
| F3 | Lista de tramos críticos por criticidad; solo impacto > 0 y contador «N tramos sin impacto» | V | [x] | Coincide con el `rank` |
| F4 | Detalle del tramo: tiempo extra, población, comunidades, alternas, bloque «Exposición» (solo lluvia como contexto; sin humedad ni radar por tramo) | W | [x] | Todos los campos manejan `null` |
| F5 | Simulación de cierre (varios tramos, chips, restablecer, «sin ruta al hospital de referencia» solo si no hay camino) | V | [x] | Recálculo instantáneo en el navegador |
| F6 | Panel «¿Por qué?»: exposición con gráfico IMERG, siempre como hipótesis | W | [x] | La etiqueta siempre visible |
| F7 | Responsivo (panel lateral en escritorio; hoja inferior en móvil) | W | [x] | Usable en celular **Hecho (15 nov):** probado en un viewport móvil de 390×844 con Playwright sobre el build de producción: mapa, hoja inferior plegable, pestañas Tramos/Simulación/¿Por qué?, detalle y simulación funcionan. Pendiente en X2: probarlo en un celular real. |
| F8 | Atribuciones y aviso «tramos críticos por consecuencia; no son derrumbes confirmados» | V | [x] | Se muestran NASA/JPL, IMERG y OSM |
| F11 | Selector de zona: carga `areas.json` y los archivos de `storage/<id>/`; las zonas con `validated: false` salen etiquetadas «no validada» | V | [x] | Cambiar de zona recentra el mapa; solo la Ruta 32 es obligatoria |
| F10 | Marcas de confianza: aislamientos sospechosos señalados, tiempo como orden de magnitud o rango (`RELIABILITY.md` paso 6) | V | [x] | «Aislada» se dice «sin ruta al hospital de referencia»; aislamientos sospechosos señalados y tiempo como orden de magnitud. Hecho; el 15 nov se cableó la marca de sospechoso en la tarjeta de detalle (no se usaba). |

### Contrato

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| C1 | Decidir y aplicar la actualización del contrato (¿0.3?): unidad fina, marcas de sospechoso, `meta.area` | R | [x] | Esquemas y mocks validan; `make validate` pasa; decisión anotada. Hecho en 0.3 (`context/contracts.md` §14): `areas.json` y carpeta por zona, `length_m`, `suspect_isolated_community_ids`, sin `soil_moisture_pctl` ni `radar_evidence`; 43 tests del validador pasan |

Cortadas `[-]`: **F2** (mostrar pasadas) y **F9** (alternar antes/después): dependen de una capa de radar que no tenemos.

## Fase 4 · Polish (dom 14:00 → cierre)

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| X1 | G2 (dom 14:00): cortar lo que no esté listo y anotarlo en decisiones | todos | [x] | Lista de cortes **15 nov:** G2 adopta la D11: no se corta ninguna funcionalidad y los no hechos y límites quedan listados ahí. |
| X2 | G3 (dom 18:00): solo errores; probar el sitio en ventana privada y en celular | todos | [x] | El flujo principal funciona **15 nov:** el sitio responde (200) y sirve los datos reales (mismo SHA-256 que `output/`). Abierto en Chrome sin sesión ni datos previos del sitio (el sitio no tiene cuentas): carga el mapa con la Ruta 32, el ranking, el detalle de T-20 (#1), «Simular cierre de este tramo» y la pestaña Simulación (≈3 h 35 min, 377 447 personas estimadas), sin errores en la consola. El móvil está probado con viewport emulado (F7); la prueba en celular físico queda como límite declarado (D11 c). |
| X3 | README final (cómo correrlo, `make all`, atribuciones, límites) y etiqueta `v1.0` | R, W | [x] | Alguien nuevo puede correrlo **15 nov:** README final escrito (estado, resultados con datos reales, comandos del pipeline, límites, atribuciones). Etiqueta `v1.0` subida sobre `0d7c334` (el `main` publicado, con el cambio del icono); el despliegue terminó bien. |
| X4 | Presentación: el resultado negativo de detectabilidad como hallazgo con su número; texto cauto | todos | [x] | Ensayada una vez **15 nov:** guion en `presentation.md` con los hallazgos y sus números; cifras de S2c, S5, contraste de tiempos y las 115 unidades contrastadas con `SPIKING.md`, `RELIABILITY.md` y `scenarios.json`, sin discrepancias. El guion se redujo a 30 s (unas 70 palabras); el resto pasó a respaldo para preguntas. Ensayado en voz alta una vez por el equipo (15 nov). |
| X5 | Entrega a Space Apps con los enlaces finales | R | [x] | Enviada antes del cierre **15 nov:** entrega hecha con los enlaces finales (sitio publicado y etiqueta `v1.0`). |

---

## Resultados y decisiones

### Registro de decisiones

| Fecha | Decisión | Por qué |
|---|---|---|
| 13 nov | Repo único `vantage` (`projects/` con `contract`, `frontend`, `pipeline`); MIT con atribución a NASA y OSM; Python con `uv`; Bun con TypeScript estricto; GitHub Pages | Simple y estático |
| 13–14 nov | Métrica titular: tiempo extra a hospital + población que depende; `extra_time_s` = máximo de `extra_s` de las afectadas no aisladas; `criticality` = Σ población × `extra_s` (aislada: el mayor `extra_s` finito; población `null` suma 0; sin población, ordena por `extra_time_s`) | Simple, reproducible, degrada sin WorldPop |
| 14 nov | `time_s` con una velocidad constante por clase de vía OSM (`meta.speed_model_kmh`); lluvia = promedio de celdas IMERG (`area_mean`); leyenda de cambio en `overlays[].range_db` | Navegador y pipeline dan los mismos números |
| 14 nov | Datos reales en `projects/pipeline/output/` (commiteado, livianos); `public/storage/` va en `.gitignore` y se llena con `make mock` o `make publish` | Despliegue reproducible |
| 14 nov | WorldPop pasa (S7); el respaldo `population: null` sigue soportado | — |
| 14 nov ~16:35 | **D1.** G1 = NO-GO para generar tramos detectando cicatrices con GCOV. Con GCOV a 10 m y este flujo no se ven derrumbes pequeños; GUNW, offsets y series por píxel siguen sin probar y no se afirma que NISAR no pueda | Resultado negativo con número (`SPIKING.md` S2) |
| 14 nov ~16:35 | **D2.** Producto = riesgo = consecuencia × exposición. Consecuencia: red vial + hospitales + población. Exposición: IMERG y, si S2c pasa, SME2. Capa de radar opcional _(reemplazada en parte por D7 y D8)_ | La detección no genera tramos |
| 14 nov ~16:35 | **D3.** Sin datos fijos como semilla (sitios de Lanamme, km del MOPT, coordenadas de prensa). Las fechas de prensa son solo etiquetas de validación | Los tramos salen de la red |
| 14 nov ~16:35 | **D4.** La zona es un parámetro (config). Ruta 32 es el caso de demostración; «diseñado para generalizarse a corredores con red vial en OSM», nunca «funciona en cualquier lugar». Límites: calidad de OSM, hospitales mal registrados (SME2 ya no entra, D7) | No se probó fuera de Ruta 32 |
| 14 nov ~16:35 | **D5.** S2c (SME2) es opcional y de 40 min máx. | Si falla, exposición solo con IMERG |
| 14 nov ~16:35 | **D6.** Texto al usuario: «tramo crítico». `candidates` sigue como clave de archivo. Nunca «confirmado» ni «causado por» | No romper el esquema |
| 14 nov | **D7.** S2c = FALLA: la humedad SME2 no sube antes de los cierres (2 de 6 en v2; 1 de 4 en v1). Exposición = solo IMERG; F4 sin humedad. SME2 no se descarta como dato, solo como señal previa | Resultado negativo con número (`SPIKING.md` S2c) |
| 14 nov | **D8.** Redirección tras los spikes (S2, S2c, S4′, S5). (a) El producto es la **consecuencia (criticidad)**: qué tramos de un corredor vial (demostrado en la Ruta 32), si se cortan, dejan a comunidades sin ruta a un hospital de referencia, con tiempo extra y población. «Riesgo = consecuencia × exposición» deja de usarse porque la exposición no está validada. (b) **Métrica R2:** hospital de referencia más cercano, con el conjunto de referencia como **parámetro de la zona** (en la Ruta 32: Calderón Guardia, México y San Juan de Dios); «aislada» pasa a significar «sin ruta al hospital de referencia» y la interfaz lo dice así. (c) **Un cierre incluye ambas calzadas** de Ruta 32. (d) Comunidades y hospitales se ajustan a la mayor componente fuertemente conexa. (e) **Exposición = lluvia IMERG como contexto**, «hipótesis»; sin SME2 y sin radar como señal. (f) Los tres negativos (S2, S2c, S5) se presentan como hallazgos con su número. (g) **El método es para cualquier corredor con red vial en OSM; la Ruta 32 es el caso de demostración y el único probado.** Son parámetros de la zona, no código: el bbox, los hospitales de referencia, la velocidad por clase de vía (hoy medianas de OSM de Costa Rica) y el ráster de población (WorldPop CRI 2020 es un archivo por país). Nunca se afirma «funciona en cualquier lugar». | R2 fue la única métrica que pasó los criterios de S4′ (12,7 % de aislamientos sospechosos frente a 54,3 % de N y R), con límites: cierres de hasta 61 km, hospitales provisionales, sin población, sin revisión manual. Las tres señales fallaron con criterios escritos antes (`SPIKING.md`). Cambia semántica, no el esquema 0.2 |
| 14 nov (cierre del día 1) | **Fase 3 repartida entre los cuatro** (ver «Carga por persona»): R queda con 3 deltas más README y entrega; Ian empieza por el pipeline. Specs de los 18 deltas redactados en la rama `docs/delta-specs` y purgados de redundancias (se quitaron `granularity`, `meta.area.referral_hospitals`, `exposure.radar_evidence`, la capa de radar del mapa y las perturbaciones de ajuste de la sensibilidad) | Un delta por rebanada, de lo más fácil a lo más difícil |
| 15 nov | **D9.** Hospitales de referencia de la Ruta 32 = los tres nacionales de San José (Calderón Guardia, México, San Juan de Dios). Medido contra una variante con Tony Facio y Guápiles añadidos: la mediana del tiempo base baja de 86,6 a 43,1 min, los pares aislados de 965 a 103 y el top 5, 10 y 20 no coinciden en ninguno (Spearman 0,53). El ranking depende casi por completo de este conjunto: se presenta como acceso a los hospitales nacionales, no como criticidad general | Es un supuesto de modelo, no un dato; se dice sin matices (`planning.md` D5) |
| 15 nov | **D10.** Revisión manual (P12): 0 de 4 aislamientos reales; todas `snapping_artifact` (enganchadas a un nodo dentro del tramo cerrado). `validated` queda en `false` (solo se revisaron 4 comunidades de 3 unidades). Excluir o reenganchar los 208 aislamientos sospechosos (21,6 % del total) deja el top 10 igual (10 de 10), por eso el modelo no cambia; la cola sí (8 unidades pierden todo su impacto) | Resultado negativo con número, como S2, S2c y S5. Límite conocido que se dice en la presentación |
| 15 nov | **D11. Propuesta para G2 (14:00).** No se corta ninguna funcionalidad. Se declaran no hechos o con límite: (a) F2 y F9 (sin capa de radar, ya cortadas); (b) segunda zona; (c) prueba en celular físico (solo viewport emulado); (d) `unclassified` con 22 vías etiquetadas; (e) el 21,6 % de aislamientos sospechosos (medido: no cambia el top 10); (f) los tiempos salen de límites publicados, no de velocidades de viaje (sesgo −15 % frente al router); (g) leyenda del mapa que se cruza con la atribución en móvil. Cerrados con datos el 15 nov: Limón aislada en 22 unidades (explicado: todas al este de Siquirres, el único tramo sin alternativa; con la Ruta 32 cerrada Limón no llega a ningún hospital), los pares c497 y c520 (el modelo usa la Ruta 32, 61–66 km y ~1 h, y el router público da ~120 km por otro camino; la referencia de Guápiles, ~1 h, coincide con el modelo) y ACC-02 de `rain-context` (8 de 8 celdas iguales al granulo original) | Para que la presentación y el README digan lo mismo que el código |
| 15 nov | **D12. Endurecimiento.** `maplibre-gl` sube a 6.18 (vulnerabilidad crítica del sanitizador, parchada en 6.4.1; necesita import por espacio de nombres y `setWorkerUrl` bajo Vite, o los tramos no se dibujan); los nombres y la clase de vía de las aristas fusionadas se eligen con una regla fija (antes cambiaban entre corridas); se quita código muerto; `scenarios.json` se escribe compacto (1 línea en lugar de 109 727, mismo contenido) y `output/` se marca como generado en `.gitattributes` | El PR de 111 mil líneas era ilegible; el repositorio ya pesaba poco (~0,6 MB comprimidos de `output/`). `bun audit` y `pip-audit` sin hallazgos |
| 15 nov | **D13. Distancia de ajuste y trazabilidad.** El ranking no depende de la distancia máxima de ajuste: con 1 500, 3 000 y 5 000 m el top 5, 10 y 20 coinciden (Spearman ≥ 0,999), aunque las comunidades pasan de 643 a 799. Se añade `make inputs` y `make inputs-check` (SHA-256 de entradas y salidas de `reports/ruta-32/inputs.json`); regenerar reproduce las salidas exactas. `RELIABILITY.md` pasa a v2 con sus dos desviaciones (sin tope de ~5 km; el ajuste se mide fuera de la etapa) | Que el proyecto sea determinista y verificable: se puede comprobar de qué entradas sale cada salida (`planning.md`, `RELIABILITY.md`) |
| 14 nov | **C1.** El contrato pasa a 0.3: `storage/areas.json` + `storage/<id>/` por zona; `candidates[].length_m` y `suspect_isolated_community_ids` requeridos; `exposure` solo con `rain_mm_12d`; ids únicos en las listas de comunidades; el validador valida cada zona y reporta archivos no UTF-8 como error. Decidido: sin motivo de la sospecha hasta que `trust-signals` lo pida; las carpetas sin listar en `storage/` se ignoran; no se cruza el bbox de `areas.json` con `meta.area` | Los deltas de pipeline y frontend construyen contra esta forma. `App.tsx` y `graph.ts` leen la primera zona de `areas.json` y `graph.test.ts` apunta a `mock-validated/`; el selector y el mapa completo siguen en `zone-picker` y `map-corridor` |
| 14 nov | Modo solo (hasta el cierre del día 1): sin turnos ni relevos; F2 y F9 cortadas; contrato 0.2 adoptado en el árbol (sin la regla de revisión de ambos lados) | Menos coordinación, más velocidad |

### Preguntas abiertas

- **Revisión de código con CODEOWNERS:** `.github/CODEOWNERS` y la protección de `main` exigen revisión de un dueño de código; el PR de `docs/close-phase-three` necesita que lo apruebe un code owner (o usar bypass). No se tocó.
- **SME2:** descartado como señal (S2c, D7). Sin respuesta sobre su fiabilidad en bosque: ningún píxel de la franja tiene retrieval «recomendado» (producto provisional).
- Hora exacta de cierre de la ventana, y texto oficial del reto sin localizar.

**Resueltas el 15 nov:** métrica y unidad de cierre (D8, `closure-units`); hospitales de referencia (D9, medido contra la variante de cinco); insumos de la corrida real (OSM, WorldPop e IMERG descargados, `output/` generado); periodo de lluvia (1 ene–13 nov de 2026, fijado en `ruta-32.toml`); velocidades por clase de vía (medianas de `maxspeed` de OSM, con `unclassified` como límite conocido, D11).

### Contradicciones por resolver

Ninguna abierta. La aparente contradicción de S4 (0 comunidades afectadas en el parque frente a 1 aislada) se explica: son redes distintas (bordes este -83.40 y -82.95). El caso de Limón se explicó con la red real (D11). El plan B de S4 («reducir al corredor») empeora el resultado: crea aislamientos falsos.
