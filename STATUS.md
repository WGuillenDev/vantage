# VANTAGE — STATUS

> Tablero vivo del equipo. Mantenelo corto y verdadero. Actualizalo **antes de cada relevo** y cada vez que una tarea cambie de estado.
> Contexto: `approach.md` (el porqué), `structure.md` (arquitectura), `contracts.md` (archivos de datos), `functions.md` (funcionalidades).
> Horas de Costa Rica (UTC−6). Ventana: **sáb 14 nov, 09:00 → dom 15 nov, 23:59** (hora de cierre aún por confirmar).

## Cómo usar este archivo

- Leyenda de estado: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[!]` bloqueada (explicá por qué en la tabla de Bloqueos).
- Los dueños son **propuestos** (el reparto final sigue pendiente): `R` Ron · `I` Ian (pipeline) · `W` Wilberth · `V` Iván (frontend).
- Un dueño por tarea. Si alguien la toma, cambia el dueño y agrega una línea en el registro de relevos.
- No borrés tareas terminadas. Este archivo también sirve de registro para la presentación final.
- Agentes: lean este archivo primero, trabajen solo en las tareas asignadas a su usuario y no marquen una tarea `[x]` hasta que se cumpla su "Terminada cuando".

## Resumen de fases

| # | Fase | Cuándo | Objetivo | Estado |
|---|---|---|---|---|
| 1 | **Bootstrap** | Sáb 09:00–11:00 | Repo, herramientas, contrato congelado y mocks, esqueleto desplegado | [~] |
| 2 | **Spiking** | Sáb 11:00–15:00 | Probar los supuestos riesgosos. Decidir seguir o plan B en la **Puerta 1** | [ ] |
| 3 | **Building** | Sáb 15:00 → dom 14:00 | Datos reales por el pipeline, UI completa sobre el contrato | [ ] |
| 4 | **Polish** | Dom 14:00 → cierre | Congelar, corregir errores, probar, desplegar, presentar | [ ] |

Prioridad ahora: **contratos congelados** (desbloquea al frontend) y **spikes** (deciden el plan). Todo lo demás espera detrás de esas dos cosas.

## Progreso

**2 / 41 tareas · 5 %** `█░░░░░░░░░░░░░░░░░░░` _(solo cuentan las `[x]`; las `[~]` aún no suman)_

| Fase | Hechas | % |
|---|---|---|
| 1 · Bootstrap | 2 / 9 | 22 % |
| 2 · Spiking | 0 / 8 | 0 % |
| 3 · Building | 0 / 17 | 0 % |
| 4 · Polish | 0 / 7 | 0 % |

_Actualizá este bloque cada vez que marques una tarea `[x]`._

## Puertas

| Puerta | Cuándo | Pregunta | Decisión |
|---|---|---|---|
| G1 | Sáb 15:00 | ¿Hay pasadas compatibles de NISAR y se nota el cambio? | _pendiente_ — seguir / plan B |
| G2 | Dom 14:00 | Congelar funcionalidades: lo que no esté listo se corta | _pendiente_ |
| G3 | Dom 18:00 | Congelar código: solo corrección de errores | _pendiente_ |

---

## Fase 1 · Bootstrap (sáb 09:00–11:00)

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| B1 | Repo público `vantage` en GitHub, licencia MIT, README, `Makefile` base en la raíz, `.github/` | R | [x] | Repo público; estructura igual a `structure.md` — _Hecho: repo público (verificado), LICENSE MIT, README, `Makefile` (`mock` real; `validate` y `all` fallan a propósito hasta B5/P7), `.github/workflows/ci.yml` (frontend + `uv sync`)._ |
| B2 | Herramientas: `uv` para el pipeline, Bun + TypeScript estricto para el frontend | R | [x] | `uv sync` y `bun install` funcionan en todas las máquinas — _Hecho: `bun install/lint/build` y `uv sync --locked` + `uv run pipeline` verificados en esta máquina; `projects/pipeline/` con `pyproject.toml`, `uv.lock` y `jsonschema`. Falta solo probarlo en las máquinas de los demás._ |
| B3 | Cerrar las 6 decisiones abiertas de `contracts.md` §11 | R | [ ] | Decisiones anotadas en el Registro de decisiones |
| B4 | Escribir los JSON Schemas en `project/contract/schemas/` y **congelarlos** | R | [ ] | Los 5 archivos de datos cubiertos, cada uno con `schema_version` |
| B5 | Mocks en `project/contract/examples/`; `make mock` y `make validate` funcionando | R | [ ] | Los mocks pasan la validación; incluye revisiones de referencias cruzadas |
| B6 | `CODEOWNERS` (una persona de backend y una de frontend sobre `contract/`) | R | [ ] | Un PR que toque `contract/` exige ambas revisiones |
| B7 | Esqueleto del frontend (React + Vite + MapLibre) cargando un mock | R | [~] | El mapa se ve en local con datos mock — _Hecho: scaffold React + Vite. Falta: MapLibre y carga de un mock._ |
| B8 | Workflow de GitHub Pages: `make validate` → `bun run build` → publicar `dist` | R | [ ] | El esqueleto tiene URL pública; `base` de Vite y `BASE_URL` correctos (sin 404) |
| B9 | Agregar los archivos de contexto (`approach`, `structure`, `functions`, `contracts`) y el `AGENTS.md` raíz | R | [~] | Archivos en el repo; AGENTS.md apunta a ellos — _Hecho: `context/*` y `CLAUDE.md`. Falta: `AGENTS.md` raíz._ |

**Salida de la fase:** contrato congelado, mocks listos, el frontend ya puede trabajar con `make mock`.

## Fase 2 · Spiking (sáb 11:00–15:00)

Cada spike termina con un resultado de una línea en la tabla y luego una decisión. Si un spike falla, se pasa a su plan B.

| ID | Spike | Dueño | Cuándo | Estado | Terminado cuando | Plan B | Resultado |
|---|---|---|---|---|---|---|---|
| S1 | Cobertura de NISAR sobre la Ruta 32 | R | 11:00–12:00 | [ ] | Dos fechas con el mismo track, dirección y CRID que encierran un cierre real, fuera del hueco del 27 jul–10 ago | Otro evento u otra zona dentro de Costa Rica | _—_ |
| S2 | Resolución y detectabilidad | R | 12:00–13:30 | [ ] | Una mancha coherente de varios píxeles sobre un derrumbe conocido | Zonas de perturbación a escala de ladera | _—_ |
| S3 | Evento de validación | I | 12:00–13:30 | [ ] | Una fuente oficial (MOPT, CONAVI, CNE) respalda la fecha del cierre | Presentar todo como «candidatos» | _—_ |
| S4 | Red vial y métrica de impacto | I | 13:30–15:00 | [ ] | El grafo conecta; quitar un tramo da números razonables | Reducir al área del corredor | _—_ |
| S5 | IMERG | I | 13:30–15:00 | [ ] | Un día de lluvia descargado y graficado | Lluvia solo como texto | _—_ |
| S6 | Prueba de humo del frontend | W, V | 13:30–15:00 | [ ] | MapLibre carga un mock del contrato, en local y desplegado | Resolver antes de seguir | _—_ |

También durante el spiking (frontend contra mocks, sin depender de los spikes):

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| S7 | Comprobar acceso a población (WorldPop) | I | [ ] | Funciona, o se elige el respaldo (solo tiempo extra y conteo de comunidades) |
| S8 | Empezar `graph.ts` (camino más corto al hospital más cercano, con conjunto de tramos cerrados) | V | [ ] | Coincide con el `scenarios.json` mock en la línea base |

## Fase 3 · Building (sáb 15:00 → dom 14:00)

Se empieza solo después de G1. Si G1 eligió el plan B, ajustá las tareas y anotalo en el Registro de decisiones.

### Pipeline

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| P1 | Obtener dos pasadas GCOV de NISAR compatibles, en streaming y recortadas al corredor | R | [ ] | Arreglos guardados en local (sin commitear); pasadas registradas para `meta.json` |
| P2 | Detección de cambio: ΔdB, filtro de speckle, máscara de agua/sombra, área mínima → polígonos | R | [ ] | `change.geojson` + PNG(s) de overlay validan |
| P3 | Grafo vial desde OSM: tramos, hospitales, comunidades → `graph.json` | I | [ ] | Valida; los ids se cruzan bien |
| P4 | Tramos candidatos (los que tocan zonas de cambio, con margen) | I | [ ] | Candidatos listados con ids de aristas |
| P5 | Impacto: quitar un candidato a la vez → tiempo extra, población que depende, aisladas, ranking → `scenarios.json` | I | [ ] | Valida; números revisados a mano en un caso |
| P6 | Contexto de lluvia → `rain.csv` | I | [ ] | Valida; las fechas cubren el periodo |
| P7 | `meta.json` (pasadas, fuentes, atribuciones, límites de overlays) y `make all` de punta a punta | R | [ ] | `make all` regenera todos los archivos y `make validate` pasa |
| P8 | **Primer despliegue con datos reales** | R, W | [ ] | El sitio publicado muestra datos reales (meta: sáb 21:00) |

### Frontend

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| F1 | Mapa con capa de cambio, control de opacidad, hospitales y comunidades | W | [ ] | Se dibuja desde datos del contrato |
| F2 | Mostrar las pasadas (fechas antes/después desde `meta.json`) | W | [ ] | Lee `meta.json` |
| F3 | Lista de candidatos por criticidad; clic selecciona en el mapa | V | [ ] | Coincide con el `rank` de `scenarios.json` |
| F4 | Panel de detalle del tramo (tiempo extra, población, comunidades, alternas, ΔdB, etiqueta de candidato) | V | [ ] | Todos los campos manejan `null` |
| F5 | Simulación de cierre (varios tramos, chips, restablecer, comunidades aisladas, recalcula en el navegador) | V | [ ] | Recálculo instantáneo; «aislada» solo si no hay camino |
| F6 | Panel «¿Por qué?»: gráfico IMERG + lista de hipótesis, rotulada como hipótesis | W | [ ] | Lee `rain.csv`; la etiqueta siempre visible |
| F7 | Diseño responsivo (panel lateral en escritorio; hoja inferior en móvil) | W | [ ] | Usable en celular; objetivos de 44 px |
| F8 | Pie de atribuciones, aviso de candidatos, revisión de accesibilidad | V | [ ] | Se muestran NASA/JPL, IMERG y OSM |
| F9 | Alternar antes/después (se corta en G2 si hay atraso) | W | [ ] | Se oculta sin romper si no hay overlays |

## Fase 4 · Polish (dom 14:00 → cierre)

| ID | Tarea | Dueño | Estado | Terminada cuando |
|---|---|---|---|---|
| X1 | Congelar funcionalidades (G2): cortar lo que no esté listo; anotar los cortes en el Registro de decisiones | todos | [ ] | Lista de cortes registrada |
| X2 | Congelar código (G3): solo corrección de errores | todos | [ ] | Sin merges de funcionalidades después de las 18:00 |
| X3 | Probar el sitio publicado en ventana privada y en un celular | W, V | [ ] | El flujo principal funciona en ambos |
| X4 | Etiquetar `v1.0` y adjuntar el zip de `dist/` para uso sin conexión | W | [ ] | El zip abre sin conexión |
| X5 | README final: cómo correrlo, `make all`, atribuciones, limitaciones | R | [ ] | Alguien nuevo puede correrlo |
| X6 | Presentación y guion de demo; el texto se mantiene cauto («candidato», «hipótesis») | todos | [ ] | Ensayada al menos una vez |
| X7 | Entrega a Space Apps con los enlaces finales | R | [ ] | Enviada antes del cierre |

---

## Resultados de spikes y decisiones

### Registro de decisiones

| Fecha/hora | Decisión | Por qué | Quién |
|---|---|---|---|
| 13 nov | Un solo repo `vantage` (`project/` con `contract`, `frontend`, `pipeline`) | Más simple para 4 personas y 2 días | R |
| 13 nov | Licencia MIT; atribución a NASA y OpenStreetMap | — | R |
| 13 nov | Python con `uv`; Bun con TypeScript estricto | — | R |
| 13 nov | GitHub Pages con GitHub Actions | Sitio estático, sin servidor | R |
| 13 nov | Control de opacidad propio para antes/después | — | R |
| 13 nov | Métrica titular: tiempo extra al hospital + población que depende del tramo | El aislamiento es poco frecuente; esta métrica es robusta | R |
| 13 nov | Ramas cortas con squash a `main`; revisión de ambos lados solo para cambios al contrato | — | R |

### Preguntas abiertas

- Hora exacta de cierre de la ventana del proyecto.
- Reparto final de tareas por persona.
- Nombre exacto del repo (fija el `base` de Vite).
- Fuente de población si WorldPop no es accesible.
- Cuántas pasadas compatibles de NISAR hay sobre el corredor (S1).

## Bloqueos

| Desde | Tarea | Bloqueo | Necesita | Estado |
|---|---|---|---|---|
| — | — | — | — | — |

## Registro de relevos

Escribí una línea al salir de tu turno. Quien entra lo lee primero.

| Hora | Sale → Entra | Hecho | Sigue | Roto / ojo con |
|---|---|---|---|---|
| — | — | — | — | — |

## Plan de turnos (propuesto)

| Franja | Pipeline | Frontend |
|---|---|---|
| Sáb 09:00–15:00 | R + I, todos en bootstrap y luego spikes | W + V, esqueleto y luego prueba de humo |
| Sáb 15:00–21:00 | Al volante: R, apoyo: I | Al volante: W, apoyo: V |
| Sáb 21:00–03:00 | Al volante: I; R descansa | Al volante: V; W descansa |
| Dom 03:00–08:00 | Entra R; duerme I | Entra W; duerme V |
| Dom 08:00–14:00 | Ambos, cierran tareas P | Ambos, cierran tareas F |
| Dom 14:00–cierre | Todos: polish, pruebas y presentación | Todos |

Ajustalo como quieras. La idea es que cada lado siempre tenga a alguien con contexto despierto y que cada cuenta de Claude Code descanse.