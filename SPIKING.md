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
| ¿La red vial da números razonables? | S4 | Reducir al área del corredor |

S5, S6, S7 y S8 no deciden G1 por sí solos: si fallan, se aplica su plan B y se sigue.

## Resumen de resultados

Se llena al terminar cada spike. Una línea por spike.

| Spike | Veredicto | Resultado en una línea | Hora | Quién |
|---|---|---|---|---|
| S1 | pendiente | — | — | — |
| S2 | pendiente | — | — | — |
| S3 | pendiente | — | — | — |
| S4 | pendiente | — | — | — |
| S5 | pendiente | — | — | — |
| S6 | pendiente | — | — | — |
| S7 | pendiente | — | — | — |
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
- **Plan B:** reducir al área del corredor.
- **Depende de:** nada. **Desbloquea:** P3, P4, P5.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Área y fuente (OSM, fecha de descarga) | pendiente |
| Nodos / aristas / componentes conexas | pendiente |
| Hospitales y comunidades encontrados | pendiente |
| Caso de prueba: tramo quitado → tiempo extra / aislamiento | pendiente |
| ¿Los números son razonables? (revisado a mano) | pendiente |
| Notas / riesgos | pendiente |

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
| Veredicto | pendiente |
| Local (`bun run dev`) | pendiente |
| Desplegado (URL de Pages) | pendiente |
| Errores de consola | pendiente |
| Notas / riesgos | pendiente |

### S7 · Acceso a población (WorldPop)

- **Objetivo:** funciona, o se elige el respaldo (solo tiempo extra y conteo de comunidades, con `population: null`).
- **Depende de:** nada. **Desbloquea:** P5 (población), F4.

| Campo | Valor |
|---|---|
| Veredicto | pendiente |
| Producto y resolución | pendiente |
| Forma de acceso (descarga, API, recorte al corredor) | pendiente |
| Población total del corredor (si se pudo) | pendiente |
| Decisión: usar WorldPop o respaldo | pendiente |
| Notas / riesgos | pendiente |

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
