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
| 2 | **Spiking** | Sáb 11:00–15:00 | Probar los supuestos riesgosos y decidir en la **Puerta 1** | [~] G1 decidida (NO-GO de detección); falta S2c (opcional) |
| 3 | **Building** | Sáb ~17:00 → dom 14:00 | Datos reales por el pipeline y UI completa sobre el contrato | [ ] |
| 4 | **Polish** | Dom 14:00 → cierre | Congelar, corregir errores, probar, desplegar, presentar | [ ] |

**G1 decidida (sáb 14 nov ~16:35): NO-GO** para detectar derrumbes con GCOV de NISAR (mínimo detectable ≈10×10 px ≈ 1 ha a −5 dB; detalle en `SPIKING.md` S2 y `context/approach.md` §5). El producto es **riesgo = consecuencia × exposición**: red vial + hospitales + población (calculada) y lluvia IMERG (+ SME2 si pasa). La capa de radar es opcional y puede ir vacía.

Prioridad ahora: la mitad de datos reales (grafo → población → impacto → lluvia) y la UI sobre ellos.

## Progreso

**13 / 39 tareas · 33 %** `███████░░░░░░░░░░░░░` _(solo cuentan las `[x]`; las `[~]` aún no suman; las `[-]` descartadas no cuentan)_

| Fase | Hechas | % |
|---|---|---|
| 1 · Bootstrap | 9 / 9 | 100 % |
| 2 · Spiking | 4 / 9 | 44 % |
| 3 · Building | 0 / 16 | 0 % |
| 4 · Polish | 0 / 5 | 0 % |

_Actualizá este bloque cada vez que marques una tarea `[x]`._

## Puertas

| Puerta | Cuándo | Pregunta | Decisión |
|---|---|---|---|
| G1 | Sáb 15:00 (decidida ~16:35) | ¿Hay pasadas compatibles de NISAR y se nota el cambio? | **NO-GO** en detección; el producto pasa a consecuencia × exposición (D1–D6) |
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
| S2c | SME2: ¿sube antes de los cierres? | R | [ ] | Opcional, máx. 40 min, criterios escritos antes. Si falla, exposición solo con IMERG |
| S3 | Eventos de validación | R | [~] | PARCIAL: prensa que cita al MOPT; falta comunicado primario |
| S4 | Red vial y métrica | I | [~] | PARCIAL: el grafo funciona; «hospital más cercano» da cero en el 43 % de los tramos |
| S5 | IMERG | I | [ ] | Sin avanzar (se absorbe en E1) |
| S6 | Humo del frontend | W, V | [x] | PASA |
| S7 | WorldPop | W | [x] | PASA |
| S8 | `graph.ts` | V | [~] | PASA en rama, no está en `main` |

## Fase 3 · Building (sáb ~17:00 → dom 14:00)

### Pipeline

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| P3 | Grafo vial de OSM para el área configurada: tramos, hospitales, comunidades → `graph.json` | I | [ ] | Valida; los ids se cruzan |
| E4 | Población WorldPop sobre las comunidades (para que la criticidad deje de dar 0) | I | [ ] | `population` poblada donde hay dato |
| E5 | Decidir la métrica de impacto (hospital de referencia vs. más cercano) y resolver la contradicción de S4 | I | [ ] | Una sola cifra por tramo y la decisión anotada abajo |
| P5 | Impacto: quitar un tramo a la vez → tiempo extra, población, aisladas, ranking → `scenarios.json` (clave `candidates`, `source: "network_consequence"`) | I | [ ] | Valida; un caso revisado a mano |
| E1 | IMERG: `rain.csv` y lluvia acumulada por tramo (`exposure.rain_mm_12d`) | I | [ ] | Valida; las fechas cubren el periodo |
| E3 | Zona como parámetro (nombre o bbox en config → `meta.area`) | I | [ ] | Cambiar el bbox cambia la salida sin tocar código |
| P7 | `meta.json` y `make all` de punta a punta | R | [ ] | `make all` regenera todo y `make validate` pasa |
| P8 | **Primer despliegue con datos reales** | R, W | [ ] | El sitio publicado muestra datos reales (meta: sáb 21:00) |
| E2 | S2c (SME2), solo si sobra tiempo | R | [ ] | Veredicto con criterios previos |

Descartadas `[-]`: **P1** (obtener pasadas GCOV) y **P2** (detección de cambio como generador de candidatos): la detección no genera tramos (G1). **P4** (tramos candidatos por zona de cambio) se fundió en P5: los tramos salen de la red.

### Frontend

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| F1 | Mapa con tramos críticos, hospitales y comunidades; capa de cambio solo si existe | W | [ ] | Se dibuja desde el contrato, con o sin capa de cambio |
| F3 | Lista de tramos críticos por criticidad; solo impacto > 0 y contador «N tramos sin impacto» | V | [ ] | Coincide con el `rank` |
| F4 | Detalle del tramo: tiempo extra, población, comunidades, alternas, bloque «Exposición» (lluvia, humedad si existe, «evidencia de radar: no detectable a esta escala») | V | [ ] | Todos los campos manejan `null` |
| F5 | Simulación de cierre (varios tramos, chips, restablecer, aisladas solo si no hay camino) | V | [ ] | Recálculo instantáneo en el navegador |
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
| 14 nov ~16:35 | **D2.** Producto = riesgo = consecuencia × exposición. Consecuencia: red vial + hospitales + población. Exposición: IMERG y, si S2c pasa, SME2. Capa de radar opcional | La detección no genera tramos |
| 14 nov ~16:35 | **D3.** Sin datos fijos como semilla (sitios de Lanamme, km del MOPT, coordenadas de prensa). Las fechas de prensa son solo etiquetas de validación | Los tramos salen de la red |
| 14 nov ~16:35 | **D4.** La zona es un parámetro (config). Ruta 32 es el caso de demostración; «diseñado para generalizarse a corredores con red vial en OSM», nunca «funciona en cualquier lugar». Límites: calidad de OSM, hospitales mal registrados, SME2 en bosque denso | No se probó fuera de Ruta 32 |
| 14 nov ~16:35 | **D5.** S2c (SME2) es opcional y de 40 min máx. | Si falla, exposición solo con IMERG |
| 14 nov ~16:35 | **D6.** Texto al usuario: «tramo crítico». `candidates` sigue como clave de archivo. Nunca «confirmado» ni «causado por» | No romper el esquema |
| 14 nov | Modo solo: sin turnos ni relevos; F2 y F9 cortadas; contrato 0.2 adoptado en el árbol (sin la regla de revisión de ambos lados) | Menos coordinación, más velocidad |

### Preguntas abiertas

- **Hospital de referencia vs. más cercano** (E5): ¿qué métrica evita que el 43 % de los tramos quede en cero?
- **Revisión de código con CODEOWNERS:** `.github/CODEOWNERS` y la protección de `main` exigen revisión de un dueño de código; trabajando solo hay que decidir si se desactiva o se usa bypass. No se tocó.
- **SME2 en bosque denso:** ¿es fiable? (S2c)
- **`rain.start/end` sin pasadas:** sigue siendo obligatorio en `meta.json`; ¿qué periodo se usa?
- Hora exacta de cierre de la ventana, y texto oficial del reto sin localizar.

### Contradicciones por resolver

- **S4, comunidades aisladas:** una medición da 0 afectadas en el parque (áreas de corredor y regional) y otra 1 aislada en la red hasta Limón.
- **Plan B de S4 («reducir al corredor»):** el informe de situación dice que empeora el resultado (18 aisladas sospechosas).
