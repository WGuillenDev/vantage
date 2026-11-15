# VANTAGE — Plan para cerrar la fase 3

> Plan de trabajo, no tablero: el estado vivo está en `STATUS.md`. Se escribió el dom 15 nov tras auditar `main` (código, pruebas, configuración y specs). Horas de Costa Rica. Puertas: **G2 dom 14:00** (congelar funcionalidades), **G3 dom 18:00** (congelar código). La hora de cierre de la ventana sigue por confirmar.

## 1. Meta y definición de «fase 3 cerrada»

La fase 3 se cierra cuando **el sitio publicado muestra datos reales de la Ruta 32 y no el mock**. Eso es P8. Todo lo demás en esta fase existe para llegar ahí o para decir cuánto confiar en el resultado.

Cerrada cuando se cumplan las cuatro:

1. `make all AREA=ruta-32`, `make publish` y `make validate` salen con 0, y `output/ruta-32/meta.json` nombra el área real (ACC-01 de `pipeline-run`).
2. `output/` está commiteado con datos reales y `deploy.yml` corre `make publish`. El sitio abierto en ventana privada no dice «MOCK» (ACC-02).
3. Los informes de confiabilidad existen en `projects/pipeline/reports/ruta-32/`: sensibilidad, contraste de tiempos y revisión manual. Cada uno con su veredicto, sea cual sea.
4. Las filas de `STATUS.md` coinciden con lo que se hizo.

## 2. Qué encontró la auditoría

**Hecho y verificado** (en `main`; 992 pruebas de pipeline y 187 de frontend pasan; `bun run lint` y `bun run build` limpios): los 18 deltas, con la interfaz completa leyendo el contrato.

**No existe todavía:**

| Qué | Evidencia |
|---|---|
| `projects/pipeline/output/` | No existe; `make publish` falla con `test -d` |
| Extracto OSM y ráster WorldPop | `work/ruta-32/` solo tiene `imerg/` (33 285 filas de celdas, 1 ene–13 nov) |
| Despliegue real | `deploy.yml` corre `make mock` con un comentario `shortcut:` |
| Comando para P10 | `rank_sensitivity.py` tiene `execute(...)` pero **no `main`, ni script en `pyproject.toml`, ni `make sensitivity`**, aunque el spec lo promete (§Deferred) |

**Valores de `configs/ruta-32.toml` que no pueden ir así a la corrida real:**

| Valor | Problema | Consecuencia |
|---|---|---|
| `[speed_model_kmh]` solo tiene `trunk = 60` | `road-graph` exige una velocidad para **cada** clase de vía del extracto (`No speed for road class …`) | La corrida real se detiene hasta completar las clases, incluida `unclassified`. Cada velocidad necesita fuente citada |
| `hospitals.referral` marcado `PENDING (Ian)` | Lista de tres ids buscados en OSM el 15 nov, no confirmada | Cambia toda la criticidad y la sensibilidad por hospital |
| `closure.alternates = []` | Sin fuente citada para las alternas | El detalle del tramo no tendrá alternas (F4 lo maneja con `null`/vacío) |
| `validated = true` | Nadie ha revisado resultados a mano | **Sobreafirma**: la interfaz lo muestra como zona validada. Debe ser `false` hasta que P12 pase |
| `rain.end = "2026-11-13"` | Fijado a mano | Aceptable; avanzarlo solo si se re-descargan celdas (ver §5) |

**Pista:** el spec de `road-graph` cita una corrida real previa (7 136 nodos, 8 715 aristas, 758 comunidades, 73 descartadas, 2,29 MB). Alguien, probablemente Ian, ya bajó el extracto en su máquina; `work/` no se versiona. Preguntarle antes de volver a descargar.

## 3. Camino crítico

```
Ian: hospitales + velocidades ──┐
OSM (make osm) ─────────────────┼─► make all ─► validar ─► commit output/ ─► deploy con make publish ─► P8
WorldPop (make worldpop) ───────┤
IMERG (ya está) ────────────────┘
                                 └─► informes: sensibilidad · tiempos · revisión manual
```

Lo que no está en el camino crítico (los tres informes, F7 en celular) no puede retrasar P8. Si no cabe, se corta en G2 y se anota.

## 4. Pasos, en orden

Dueños según `STATUS.md`. Cada paso termina con un criterio comprobable.

### Bloque A — Desbloquear la corrida (primero; sin esto nada avanza)

| # | Paso | Dueño | Terminado cuando |
|---|---|---|---|
| A1 | Confirmar la lista de hospitales de referencia (Calderón Guardia, México, San Juan de Dios; decidir Tony Facio y Guápiles) y quitar `PENDING` del toml | I, R | La lista queda escrita con el criterio en una línea; ids verificados en OSM |
| A2 | Si Ian tiene el extracto local, compartirlo o confirmar la fecha; si no, `make osm AREA=ruta-32` | I, R | Existen `work/ruta-32/osm/roads.osm`, `features.osm` y `extract_date.txt` |
| A3 | Completar `speed_model_kmh` con todas las clases del extracto (el error de `road-graph` las lista) y una fuente por valor, incluida `unclassified` | I, R | La etapa `road-graph` ya no se detiene por velocidad faltante; las fuentes quedan citadas en el toml |
| A4 | `make worldpop AREA=ruta-32` (archivo de 31,5 MB, no se commitea) | W, R | Existe `work/worldpop/cri_ppp_2020.tif` |
| A5 | Poner `validated = false` hasta que P12 apruebe | R | El toml lo dice; la interfaz etiqueta la zona «no validada» |

**Estado del bloque A (15 nov):**

| # | Estado | Detalle |
|---|---|---|
| A1 | Pendiente de Ian | Los 5 ids existen en OSM como `amenity=hospital` (Calderón Guardia, México, San Juan de Dios, Tony Facio, Guápiles). La lista provisional sigue con los tres primeros; la decisión es de Ian |
| A2 | Hecho | Extracto OSM del 2026-11-15 en `work/ruta-32/osm/` (`roads.osm` 14,8 MB). Overpass dio 502 dos veces; funcionó al reintentar. `road-graph` corre con el extracto real y descarta comunidades a más de 3 km de la red (visto: Peje, Bayeiñak, Playa Hermosa…) |
| A3 | Hecho, con una reserva | `speed_model_kmh` completo con las medianas de `maxspeed` de OSM en el extracto: trunk 60; primary, secondary, tertiary y unclassified 40. Fuente anotada en el toml. `unclassified` se apoya en solo 22 vías etiquetadas; Ian debe confirmarla. Son límites publicados, no velocidades de viaje: los tiempos salen optimistas y D2 mide cuánto |
| A4 | Hecho | `work/worldpop/cri_ppp_2020.tif`, 31,5 MB |
| A5 | Hecho | `validated = false` en `ruta-32.toml`; ACC-01 de `area-config` y su prueba actualizados |

### Bloque B — Primera corrida real (P7)

| # | Paso | Dueño | Terminado cuando |
|---|---|---|---|
| B1 | `make all AREA=ruta-32` | R | Sale con 0 y genera `output/ruta-32/{meta,graph,scenarios}.json` y `rain.csv` más `output/areas.json` |
| B2 | `make publish validate` | R | Ambos con 0; `meta.json` nombra «Ruta 32», sin «MOCK» |
| B3 | **Leer los números antes de publicarlos** (ver «Revisión de sentido» abajo) | R, I | Anotado en `STATUS.md` si algo choca con S4′ |
| B4 | Verificar ACC de `population-data`: ≥ 90 % de comunidades con valor y total dentro de ±5 % del ráster, o la diferencia explicada | W, R | E4 pasa a `[x]` o queda anotado por qué no |
| B5 | Verificar E1: `rain.csv` cubre del 1 ene al 13 nov y `exposure.rain_mm_12d` aparece por tramo | I, R | E1 pasa a `[x]` |

**Revisión de sentido (B3)**, comparar con lo que ya se midió en S4′ y en la corrida previa de Ian:
- Nº de unidades de cierre: ¿pasan de 19 y vienen de cortar por uniones?
- Comunidades aisladas y `suspect_isolated_community_ids`: S4′ midió 12,7 % de sospechosas con «hospital de referencia». Un número muy distinto se explica o se investiga.
- Tiempo extra de los primeros 5 tramos: ¿tiene sentido para quien conoce la ruta?
- Población total frente al ráster.

**Estado del bloque B (15 nov):**

| # | Estado | Detalle |
|---|---|---|
| B1 | Hecho | `make all AREA=ruta-32` con exit 0: `graph.json` 2,29 MB (7 136 nodos, 8 715 aristas, 758 comunidades), `scenarios.json` con 115 unidades de cierre, `rain.csv`, `meta.json`, `areas.json` |
| B2 | Hecho | `make publish validate` con exit 0; `meta.json` sin «MOCK», con las tres atribuciones (OSM del 2026-11-15, IMERG Late, WorldPop) |
| B3 | Hecho, con tres notas | Ver abajo. La app local con datos reales abre sin errores de consola y muestra el aviso, el banner «Zona no validada», la lista, el mapa y el pie |
| B4 | Hecho | 758 de 758 comunidades con población (≥ 90 %); asignado 2 899 678 frente a 2 957 560 del ráster en el bbox: −1,96 % (±5 %) |
| B5 | Hecho | `rain.csv` con 317 días, del 2026-01-01 al 2026-11-13; `exposure.rain_mm_12d` presente en las unidades |

Notas de la revisión de sentido (B3):
- **Unidades:** 115 (antes 19 en S4′); mediana 497 m, mínima 15 m, máxima 34,5 km; solo 6 pasan de 5 km. 100 tienen impacto y 15 no.
- **Aislamientos:** 965 pares comunidad-unidad aislados, 208 marcados como sospechosos (21,6 %). S4′ midió 12,7 % con otra unidad de cierre, así que no es comparable uno a uno. En 22 de las 39 unidades con aislados, todos son sospechosos. Esas 22 son las que más hay que revisar a mano en D3.
- **Ranking:** los cinco primeros son tramos cortos de un mismo cuello de botella (168 m, 497 m, 332 m, 1,5 km y uno de 34,5 km con 35 aristas), con criticidad casi igual y unas 311 comunidades afectadas. Los tiempos extra de 2 h 20 min a 3 h 35 min salen de límites publicados (A3), así que son optimistas; D2 mide el desvío.
- **Cobertura:** `road-graph` descarta comunidades a más de 3 km de la red (Talamanca, sur de Limón); está aceptado en el spec.

### Bloque C — Despliegue real (P8)

| # | Paso | Dueño | Terminado cuando |
|---|---|---|---|
| C1 | Commitear `projects/pipeline/output/` (liviano, decisión del 14 nov) | R | `git ls-files projects/pipeline/output` lista los archivos |
| C2 | En `deploy.yml`: `make mock` → `make publish`; quitar el comentario `shortcut:` | R | El workflow pasa en una rama |
| C3 | Tras fusionar, abrir el sitio en ventana privada | R, W | Datos reales, sin «MOCK», aviso «no son derrumbes confirmados» y pie con OSM, IMERG y WorldPop (ACC-02) |
| C4 | Si C3 falla, volver a `make mock` en el workflow y arreglar en rama; no dejar el sitio roto | R | El sitio publicado siempre abre |

Meta: P8 antes del cierre del bloque de datos, no esperar a G2.

**Estado del bloque C (15 nov):**

| # | Estado | Detalle |
|---|---|---|
| C1 | Hecho | `projects/pipeline/output/` commiteado (4,7 MB: `areas.json` y `ruta-32/` con grafo, escenarios, lluvia y `meta.json`) |
| C2 | Hecho | `deploy.yml` corre `make publish` en lugar de `make mock`; se quitó el comentario `shortcut:` |
| C3 | Parcial | Probado en local con los pasos exactos del workflow (`make publish validate`, `bun install --frozen-lockfile`, `bun run build`) y el build servido en `/vantage/`: sin «MOCK», con aviso, banner de zona no validada y las tres atribuciones; abrir un tramo, el panel «Cómo leer» y la nota de referencia funcionan. **Falta** empujar y fusionar (denegado para Claude) y abrir el sitio publicado en ventana privada |
| C4 | Sin uso | No hubo que volver al mock |

Hallazgos del bloque C: en la comprobación vi que el detalle del tramo no marcaba los aislamientos sospechosos, aunque el spec de `trust-signals` lo exige (`suspectLabel` existía pero nada lo usaba). Corregido y con prueba; F10 sí queda `[x]` ahora, y en la auditoría anterior lo di por hecho sin comprobar ese cableado.

### Bloque D — Informes de confiabilidad (después de P8; no bloquean el despliegue)

| # | Paso | Dueño | Terminado cuando |
|---|---|---|---|
| D1 | **Añadir `main`, el script `rank-sensitivity` y `make sensitivity AREA=<id>`** (hoy falta) y correrlo | V, R | Existe `reports/ruta-32/sensitivity.json` con veredicto; las pruebas siguen pasando |
| D2 | Escribir `reports/ruta-32/reference_times.json` (3–5 tiempos con fuente citada y fecha; nunca inventados) y correr `make timecheck AREA=ruta-32` | V, R | `time_crosscheck.json` con veredicto; si hay menos de 15 pares, queda `insufficient_pairs` y se dice |
| D3 | `make review-prepare AREA=ruta-32`, **una persona que conozca la zona** clasifica las comunidades aisladas de las 3 unidades, luego `make review-summary` | R | `manual_review.json` con revisor, fecha y veredicto |
| D4 | Si D3 pasa (≥ 80 % reales), `validated = true`; si no, queda `false` y se corrigen los artefactos y se vuelve a medir | R | El toml refleja el resultado de D3 |
| D5 | Variante con los 5 hospitales (añadir Tony Facio y Guápiles) para medir cuánto depende el ranking de qué hospitales cuentan como referencia | R | **Hecho (15 nov):** ver «Resultado de D5». No se publica |

Los tres veredictos se reportan tal cual. Un `fail` es un hallazgo con su número (principio del proyecto), no un motivo para ocultarlo ni para ajustar el modelo a última hora.

**Resultado de D5 (15 nov).** Método: copia aislada del pipeline con la misma red, población y lluvia, y `hospitals.referral` con los cinco ids (los tres de San José más `way/1451665976` Tony Facio y `way/326924912` Guápiles). Mismas 115 unidades de cierre.

| Medida | 3 hospitales (San José) | 5 hospitales |
|---|---|---|
| Mediana del tiempo base al hospital | 86,6 min | 43,1 min |
| Comunidades a más de 2 h en el estado base | 139 | 20 |
| Unidades con impacto | 100 | 97 |
| Pares comunidad-unidad aislados | 965 | 103 |
| Coincidencia del top 5 / top 10 / top 20 | 0 / 0 / 0 | |
| Correlación de rangos (Spearman, 89 unidades en común) | 0,53 | |

El ranking depende casi por completo del conjunto de referencia. Con tres hospitales mide el acceso a los hospitales nacionales de San José (el cuello de botella es la zona de Braulio Carrillo, unas 311 comunidades afectadas por unidad). Con cinco mide el acceso local, y el primer lugar pasa a ser una unidad de 107 m junto a Limón con una sola comunidad aislada (la ciudad de Limón, 34 253 habitantes) que además está marcada como sospechosa, o sea un posible artefacto de la red.

Decisión (R, 15 nov): **se mantienen los tres hospitales de San José**, porque la pregunta del producto es el acceso a un hospital nacional de referencia. Se dice sin matices en la presentación y en la interfaz: «referencia = hospitales nacionales de San José»; el ranking no es válido para otro conjunto, y la variante de cinco queda como hallazgo (X4). La interfaz no debe presentar el ranking como estable ante este supuesto.

### Bloque E — Cierre

| # | Paso | Dueño | Terminado cuando |
|---|---|---|---|
| E1 | F7: probar en un celular real (hoja inferior, tocar un tramo, simular un cierre) | W, R | F7 pasa a `[x]` o se anota qué falla |
| E2 | Cerrar la marca de `rain-context` (las afirmaciones del spec siguen en `none`; las pruebas ya existen, `builder` cambia las etiquetas) | I, R | Spec en `[x]` |
| E3 | Actualizar `STATUS.md`: filas, progreso, decisiones (qué quedó con qué veredicto) | R | Coincide con la realidad |
| E4 | G2: lista de cortes anotada en el registro de decisiones | todos | Lista escrita |

## 5. Decisiones que hacen falta (del equipo, no mías)

1. **Velocidades por clase de vía y su fuente** (A3). Sin eso no hay corrida. ¿Medianas de OSM de Costa Rica (lo que dice D8) o valores de otra fuente?
2. **Hospitales de referencia** (A1): decidido el 15 nov tras medirlo (D5): se mantienen los tres de San José; con cinco el top 20 no coincide en ninguno.
3. **Alternas** (`closure.alternates`): ¿se cita una fuente o se publica sin alternas? Recomendado: sin alternas, dicho en la interfaz, antes que alternas sin fuente.
4. **Periodo de lluvia** (pregunta abierta de `STATUS.md`): hoy 1 ene–13 nov 2026 por configuración. Si no se re-descarga, se queda; si se re-descarga, se mueve la fecha fin a mano.
5. **Si algún informe no llega a G2:** se publica sin él y la interfaz no afirma lo que no se midió.

## 6. Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Overpass o WorldPop caídos o lentos | A2/A4 se atrasan | Pedir a Ian el extracto local; el ráster es un solo archivo HTTPS |
| Faltan clases de vía en `speed_model_kmh` | `road-graph` se detiene | A3 al principio, no al final |
| La corrida real da cifras raras (aislamientos falsos, 0 comunidades) | El sitio engaña | B3 antes de C1; si no se explica, se publica con la marca de sospechosos y se dice |
| `make all` con varias zonas falla por una zona sin preparar | Corrida rota | Usar siempre `AREA=ruta-32` |
| El deploy rompe el sitio | Sitio sin datos | C4: volver al mock y arreglar en rama |
| Nadie revisa D3 a mano | `validated` queda en `false` | Es un resultado válido: se publica «no validada» y se explica |
| Credenciales de Earthdata o datos pesados al repositorio | Fuga o repo inflado | `work/` ya se ignora salvo `imerg/`; no commitear el ráster ni credenciales |

## 7. Qué se corta si no hay tiempo (orden de corte, de primero a último)

1. D2 (tiempos), si no hay referencias citables.
2. D1 (sensibilidad) si el comando no queda a tiempo.
3. E1 (celular), se anota como no probado.
4. D3/D4 se hacen aunque sea con una sola unidad y se dice así; sin esto la zona va como «no validada».

No se corta nunca: A1–A3, B1–B3, C1–C3. Son el producto.

## 8. Convenciones de esta rama

Todo el trabajo de cierre de la fase 3 va en una sola rama, `docs/close-phase-three`, que sale de `main` (decisión de R, 15 nov). Lleva el plan, `STATUS.md`, la configuración de la zona, los datos de `output/`, los informes y el cambio de `deploy.yml`. R figura como co-dueño de todos los pasos pendientes y los ejecuta o los revisa con quien los haya hecho. Commits con Conventional Commits en inglés, uno por bloque de trabajo; empujar y fusionar es de las personas.
