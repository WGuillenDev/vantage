# VANTAGE — STATUS

> Tablero vivo. Corto y verdadero: actualizalo cuando una tarea cambie de estado.
> Contexto: `context/approach.md` (porqué y método), `structure.md`, `functions.md`, `contracts.md`. Resultados de spikes: `SPIKING.md`.
> Horas de Costa Rica (UTC−6). Ventana: **sáb 14 nov 09:00 → dom 15 nov 23:59** (hora de cierre por confirmar).
> **Modo solo (R) desde el sáb 14 nov por la tarde:** hoy todo lo hace R, por prioridad y sin relevos. La columna «Dueño» guarda el reparto original para cuando vuelva el equipo (R Ron · I Ian · W Wilberth · V Iván).

Leyenda: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[-]` descartada (con motivo).

## Resumen de fases

| # | Fase | Cuándo | Objetivo | Estado |
|---|---|---|---|---|
| 1 | **Bootstrap** | Sáb 09:00–11:00 | Repo, herramientas, contrato y mocks, esqueleto desplegado | [x] |
| 2 | **Spiking** | Sáb 11:00–15:00 | Probar los supuestos riesgosos y decidir en la **Puerta 1** | [x] Cerrada: G1 NO-GO de detección; S2c y S5 (señal) FALLAN; S4′ solo pasa «hospital de referencia»; S3 queda parcial (sin comunicado primario) |
| 3 | **Building** | Sáb ~17:00 → dom 14:00 | Datos reales por el pipeline y UI completa sobre el contrato | [ ] |
| 4 | **Polish** | Dom 14:00 → cierre | Congelar, corregir errores, probar, desplegar, presentar | [ ] |

**G1 decidida (sáb 14 nov ~16:35): NO-GO** para detectar derrumbes con GCOV de NISAR (mínimo detectable ≈10×10 px ≈ 1 ha a −5 dB; detalle en `SPIKING.md` S2 y `context/approach.md` §5). Tras los demás spikes (S2c, S4′, S5; ver `SPIKING.md`) ninguna señal de exposición anticipó los cierres, y el producto se redefine en la **D8**: es la **consecuencia (criticidad)** de cada tramo de la Ruta 32, con la lluvia IMERG como contexto etiquetado «hipótesis». «Riesgo = consecuencia × exposición» (D2) ya no se usa. La capa de radar es opcional y puede ir vacía.

Prioridad ahora: la mitad de datos reales (grafo con las dos calzadas y hospitales de referencia → población → impacto → lluvia como contexto) y la UI sobre ellos. P3 y P5 ya existen en ramas remotas: integrarlos, no rehacerlos.

## Progreso

**18 / 39 tareas · 46 %** `█████████░░░░░░░░░░░` _(solo cuentan las `[x]`; las `[~]` aún no suman; las `[-]` descartadas no cuentan)_

| Fase | Hechas | % |
|---|---|---|
| 1 · Bootstrap | 9 / 9 | 100 % |
| 2 · Spiking | 8 / 9 | 89 % |
| 3 · Building | 1 / 16 | 6 % |
| 4 · Polish | 0 / 5 | 0 % |

_Actualizá este bloque cada vez que marques una tarea `[x]`._

## Puertas

| Puerta | Cuándo | Pregunta | Decisión |
|---|---|---|---|
| G1 | Sáb 15:00 (decidida ~16:35) | ¿Hay pasadas compatibles de NISAR y se nota el cambio? | **NO-GO** en detección; el producto pasa a consecuencia × exposición (D1–D6), redefinido después en D8 |
| G2 | Dom 14:00 | Congelar funcionalidades: se corta lo que no esté listo | _pendiente_ |
| G3 | Dom 18:00 | Congelar código: solo corrección de errores | _pendiente_ |

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
| S2c | SME2: ¿sube antes de los cierres? | R | [x] | **FALLA**: 1 de 4 eventos sobre p75 (hacían falta 3); exposición solo con IMERG (D7). SME2 sí existe y cubre la ruta (S1′ PASA) |
| S3 | Eventos de validación | R | [~] | PARCIAL: prensa que cita al MOPT; sin comunicado primario en `mopt.go.cr` ni `conavi.go.cr`. Se corrigió la lista: el 17 jul sí hubo cierre; se añadieron el 8 oct y el 2.º episodio de feb |
| S4 | Red vial y métrica | R | [x] | PARCIAL: la red regional conecta (+77,6 min por alterna al cortar el parque); con «hospital más cercano» el parque afecta a 0 comunidades; recortar al corredor crea aislamientos falsos (ver `SPIKING.md`). **S4′ (red real, 191 tramos):** con una calzada por cierre todo falla; con las dos calzadas (19 cierres) pasa solo «hospital de referencia» (R2); ver `SPIKING.md` |
| S5 | IMERG | R | [x] | Lectura PASA (317 días); señal FALLA: 3 de 8 cierres sobre p75 de lluvia de 12 días (hacían falta 6), todos de ago–oct. La lluvia va como contexto, «hipótesis» (ver `SPIKING.md` S5) |
| S6 | Humo del frontend | W, V | [x] | PASA |
| S7 | WorldPop | W | [x] | PASA |
| S8 | `graph.ts` | V | [x] | PASA; ya está en `main` |

## Fase 3 · Building (sáb ~17:00 → dom 14:00)

### Pipeline

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| P3 | Grafo vial de OSM para el área configurada: tramos, hospitales, comunidades → `graph.json` (spec: `projects/pipeline/deltas/road-graph.spec.md`) | I | [ ] | Valida; los ids se cruzan. Existe en `origin/feat/road-graph`; falta que ajuste comunidades y hospitales a la mayor componente fuertemente conexa y que la lista de hospitales sea el conjunto de referencia de la zona, como parámetro (D8) |
| E4 | Población WorldPop sobre las comunidades (para que la criticidad deje de dar 0) | I | [ ] | `population` poblada donde hay dato |
| E5 | Decidir la métrica de impacto (hospital de referencia vs. más cercano; con el más cercano el parque da 0 comunidades afectadas) y revisar a mano la 1 aislada hasta Limón | I | [ ] | Una sola cifra por tramo y la decisión anotada abajo — **recomendación S4′: R2, con límites; decisión pendiente**. Métrica decidida en D8; queda la revisión manual de un caso y la lista de hospitales con Ian |
| P5 | Impacto: quitar un tramo a la vez → tiempo extra, población, aisladas, ranking → `scenarios.json` (clave `candidates`, `source: "network_consequence"`; spec: `projects/pipeline/deltas/impact-scoring.spec.md`) | I | [ ] | Valida; un caso revisado a mano; sin aislamientos falsos (comunidades ajustadas a la vía cortada, `oneway`). Existe en `origin/feat/impact-scoring`; falta que cierre **ambas calzadas** por tramo y que use el hospital de referencia (D8). Unidad de cierre más fina que 33–61 km: pendiente |
| E1 | IMERG: `rain.csv` y lluvia acumulada por tramo (`exposure.rain_mm_12d`) | I | [ ] | Valida; las fechas cubren el periodo. Lectura ya probada en S5; no afirmar relación con los cierres |
| E3 | Zona como parámetro (nombre o bbox en config → `meta.area`) | I | [ ] | Cambiar el bbox cambia la salida sin tocar código |
| P7 | `meta.json` y `make all` de punta a punta | R | [ ] | `make all` regenera todo y `make validate` pasa |
| P8 | **Primer despliegue con datos reales** | R, W | [ ] | El sitio publicado muestra datos reales (meta: sáb 21:00) |
| E2 | S2c (SME2), solo si sobra tiempo | R | [x] | FALLA (ver S2c); sin humedad en la exposición |

Descartadas `[-]`: **P1** (obtener pasadas GCOV) y **P2** (detección de cambio como generador de candidatos): la detección no genera tramos (G1). **P4** (tramos candidatos por zona de cambio) se fundió en P5: los tramos salen de la red.

### Frontend

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| F1 | Mapa con tramos críticos, hospitales y comunidades; capa de cambio solo si existe | W | [ ] | Se dibuja desde el contrato, con o sin capa de cambio |
| F3 | Lista de tramos críticos por criticidad; solo impacto > 0 y contador «N tramos sin impacto» | V | [ ] | Coincide con el `rank` |
| F4 | Detalle del tramo: tiempo extra, población, comunidades, alternas, bloque «Exposición» (lluvia como contexto, «evidencia de radar: no detectable a esta escala»; sin humedad) | V | [ ] | Todos los campos manejan `null` |
| F5 | Simulación de cierre (varios tramos, chips, restablecer, «sin ruta al hospital de referencia» solo si no hay camino) | V | [ ] | Recálculo instantáneo en el navegador |
| F6 | Panel «¿Por qué?»: exposición con gráfico IMERG, siempre como hipótesis | W | [ ] | La etiqueta siempre visible |
| F7 | Responsivo (panel lateral en escritorio; hoja inferior en móvil) | W | [ ] | Usable en celular |
| F8 | Atribuciones y aviso «tramos críticos por consecuencia; no son derrumbes confirmados» | V | [ ] | Se muestran NASA/JPL, IMERG y OSM |

Cortadas `[-]`: **F2** (mostrar pasadas) y **F9** (alternar antes/después): dependen de una capa de radar que no tenemos.

## Fase 4 · Polish (dom 14:00 → cierre)

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| X1 | G2 (dom 14:00): cortar lo que no esté listo y anotarlo en decisiones | todos | [ ] | Lista de cortes |
| X2 | G3 (dom 18:00): solo errores; probar el sitio en ventana privada y en celular | todos | [ ] | El flujo principal funciona |
| X3 | README final (cómo correrlo, `make all`, atribuciones, límites) y etiqueta `v1.0` | R, W | [ ] | Alguien nuevo puede correrlo |
| X4 | Presentación: el resultado negativo de detectabilidad como hallazgo con su número; texto cauto | todos | [ ] | Ensayada una vez |
| X5 | Entrega a Space Apps con los enlaces finales | R | [ ] | Enviada antes del cierre |

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
| 14 nov | **D7.** S2c = FALLA: la humedad SME2 no sube antes de los cierres (1 de 4). Exposición = solo IMERG; F4 sin humedad. SME2 no se descarta como dato, solo como señal previa | Resultado negativo con número (`SPIKING.md` S2c) |
| 14 nov | **D8.** Redirección tras los spikes (S2, S2c, S4′, S5). (a) El producto es la **consecuencia (criticidad)**: qué tramos de un corredor vial (demostrado en la Ruta 32), si se cortan, dejan a comunidades sin ruta a un hospital de referencia, con tiempo extra y población. «Riesgo = consecuencia × exposición» deja de usarse porque la exposición no está validada. (b) **Métrica R2:** hospital de referencia más cercano, con el conjunto de referencia como **parámetro de la zona** (en la Ruta 32: Calderón Guardia, México y San Juan de Dios); «aislada» pasa a significar «sin ruta al hospital de referencia» y la interfaz lo dice así. (c) **Un cierre incluye ambas calzadas** de Ruta 32. (d) Comunidades y hospitales se ajustan a la mayor componente fuertemente conexa. (e) **Exposición = lluvia IMERG como contexto**, «hipótesis»; sin SME2 y sin radar como señal. (f) Los tres negativos (S2, S2c, S5) se presentan como hallazgos con su número. (g) **El método es para cualquier corredor con red vial en OSM; la Ruta 32 es el caso de demostración y el único probado.** Son parámetros de la zona, no código: el bbox, los hospitales de referencia, la velocidad por clase de vía (hoy medianas de OSM de Costa Rica) y el ráster de población (WorldPop CRI 2020 es un archivo por país). Nunca se afirma «funciona en cualquier lugar». | R2 fue la única métrica que pasó los criterios de S4′ (12,7 % de aislamientos sospechosos frente a 54,3 % de N y R), con límites: cierres de hasta 61 km, hospitales provisionales, sin población, sin revisión manual. Las tres señales fallaron con criterios escritos antes (`SPIKING.md`). Cambia semántica, no el esquema 0.2 |
| 14 nov | Modo solo: sin turnos ni relevos; F2 y F9 cortadas; contrato 0.2 adoptado en el árbol (sin la regla de revisión de ambos lados) | Menos coordinación, más velocidad |

### Preguntas abiertas

- **Unidad de cierre y métrica (S4′, E5, P5):** sobre la red real, cortar una sola calzada produce aislamientos ficticios (87 % de Ruta 32 en OSM es de sentido único). Cerrando las dos calzadas, solo «hospital de referencia» (R2) pasó los criterios, con cierres de hasta 61 km, hospitales provisionales y sin población. Hay que decidir métrica y granularidad antes de P5; ver `SPIKING.md` S4′.
- **P3 y P5 ya existen en ramas remotas** (`origin/feat/road-graph`, `origin/feat/impact-scoring`, con pruebas) pero no en `main`, y este tablero los marca `[ ]`. Falta confirmar con quién los hizo y qué faltaría integrar.

- **Métrica y hospitales (D8, E5):** S4′ recomienda «hospital de referencia más cercano» con límites (cierres de hasta 61 km, hospitales provisionales, sin población, sin revisión manual). **Supuesto de D8 sin confirmar:** que `graph.json → hospitals` lleve solo los hospitales de referencia configurados para la zona (en la Ruta 32: Calderón Guardia, México y San Juan de Dios), para que pipeline y navegador calculen igual sin cambiar el contrato. Falta que Ian confirme la lista y que el criterio de «referencia» sea un parámetro de configuración, no una lista fija en el código. Además, el criterio de «referencia» puede no trasladarse tal cual a otro país: sin probar.
- **Revisión de código con CODEOWNERS:** `.github/CODEOWNERS` y la protección de `main` exigen revisión de un dueño de código; trabajando solo hay que decidir si se desactiva o se usa bypass. No se tocó.
- **SME2:** descartado como señal (S2c, D7). Sin respuesta sobre su fiabilidad en bosque: ningún píxel de la franja tiene retrieval «recomendado» (producto provisional).
- **`rain.start/end` sin pasadas:** sigue siendo obligatorio en `meta.json`; ¿qué periodo se usa?
- Hora exacta de cierre de la ventana, y texto oficial del reto sin localizar.

### Contradicciones por resolver

Ninguna abierta. La aparente contradicción de S4 (0 comunidades afectadas en el parque frente a 1 aislada) se explica: son redes distintas (bordes este -83.40 y -82.95); la de Limón sigue sin revisar a mano (E5). El plan B de S4 («reducir al corredor») empeora el resultado: crea aislamientos falsos.
