# VANTAGE — SPIKING

> Registro de resultados de los spikes (sáb 14 nov 2026). El tablero vivo es `STATUS.md`; aquí está el detalle y la evidencia que no cabe allí.
> **G1 ya se decidió (~16:35): NO-GO para detectar derrumbes con GCOV de NISAR.** El producto es riesgo = consecuencia × exposición. Ver `STATUS.md` (decisiones) y `context/approach.md`.

## Reglas

- Un spike termina con un **veredicto** (`PASA`, `FALLA`, `PARCIAL`) y su evidencia. Lo desconocido se escribe `pendiente` o `null`, nunca un número supuesto.
- Criterios escritos **antes** de calcular; si cambian, se registra una versión nueva, nunca en silencio. Se reportan todos los resultados, también los negativos.
- Lenguaje cauto: «señal», «hipótesis», «tramo crítico». Nunca «cierre confirmado» ni «causado por la lluvia».
- No se commitean datos crudos de NISAR, rásters grandes ni credenciales.
- Los scripts y salidas de S1/S2 (carpetas `s1` y `s2b`) nunca se versionaron y se retiraron del árbol. Lo que queda es esta ficha.

## Resumen

| Spike | Veredicto | Resultado en una línea |
|---|---|---|
| S1 | PASA con reservas | NISAR cubre la ruta desde el 19 jun 2026, pasada cada 12 días; los datos se leen sin bajar el archivo. Par principal: 069 D, 1→13 jul (`P05023`). |
| S2 | **FALLA** | 3 pruebas + paso A sintético: sin separar evento de control. Mínimo detectable ≈10×10 px (≈1 ha) a −5 dB. B exploratorio negativo; C (GUNW) sin correr. |
| S1′ | PASA con reserva | SME2: 55 granos desde el 19 jun; IMERG Late diario, 136 días. Ver ficha. |
| S2c | **FALLA** | SME2 no sube antes de los cierres: en v2 (lista corregida en S3) 2 de 6 eventos sobre p75 (hacían falta 5), y en v1 1 de 4 (hacían falta 3); la mediana de eventos (0,310) queda por debajo de la línea base (0,325). Ningún retrieval «recomendado» en la franja. |
| S3 | PARCIAL | Cierres de 2026 con prensa que cita al MOPT; sigue sin comunicado primario (se revisó `mopt.go.cr` y `conavi.go.cr`). Se reincorporó el cierre del 17 jul y se añadieron el 8 oct y el segundo episodio de feb. |
| S4′ | **R2 PASA; N y R FALLAN** | Sobre la red real (191 tramos de Ruta 32), con cierre de una calzada todo falla; cerrando las dos calzadas (19 cierres) pasa solo «hospital nacional» (R2), con límites. Ver ficha. |
| S4 | PARCIAL | Red regional conecta; un corte en el parque da +77,6 min San José→Guápiles por alterna. Con «hospital más cercano» el parque afecta a 0 comunidades; recortar al corredor crea aislamientos falsos (ver ficha). |
| S5 | **Lectura PASA; señal FALLA** | IMERG diario leído sin problema (317 días, 9 celdas). La lluvia de 12 días previa supera el p75 en 3 de 8 cierres (hacían falta 6); los tres son de ago–oct. Se muestra como contexto, no como señal. |
| S6 | PASA | MapLibre carga el mock en dev, build y Pages (https://wguillendev.github.io/vantage/), sin errores de consola. |
| S7 | PASA | WorldPop CRI 2020 (100 m): 31,5 MB por HTTPS, sin streaming; se recorta con `rasterio`. 946 290 personas en el `bbox` provisional `[-84.20, 9.95, -83.70, 10.30]`. Es una estimación modelada, no un censo. |
| S8 | PASA | `graph.ts` (ya en `main`) coincide con la línea base y con los 4 candidatos del mock, incluido el aislamiento de c4 en T-03. |

---

## S1 · Cobertura de NISAR

- **Veredicto:** PASA con reservas.
- **Par principal (frame 083, `P05023`):** 069 D, 1 jul → 13 jul 2026.
- **Compatibles:** track 069 D, 10 fechas (19 jun–17 oct); track 105 A, 10 fechas (21 jun–19 oct). 8 pares de 12 días y 1 de 24 días (cruza el hueco del 27 jul–10 ago) por track. GCOV no existe antes del 19 jun.
- **Cobertura del tramo de OSM:** 069 D frame 083 cubre 99–100 %; 105 A frame 007, 100 %; tracks 170 D y 004 A, 0 %. La pasada del 8 jul del track 170 es `SHSH`, distinta de `DHDH`: no se mezcla.
- **Lectura:** rutas `science/LSAR/GCOV/grids/frequencyA/HHHH` y `HVHV`; píxel de 10 m, EPSG 32617, bloques de 512×512; un recorte de 200×200 se lee en unos 4 s con `earthaccess` (login Earthdata). Horas de paso (CR): 069 D a las 18:00, 105 A a las 05:12.
- **Consulta:** CMR, `NISAR_L2_GCOV_PROVISIONAL_V1` (también `NISAR_L2_GCOV_V1`; `BETA` dio 0). `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L2_GCOV_PROVISIONAL_V1&bounding_box=-84.15,9.95,-83.75,10.25&page_size=200&sort_key=start_date`. 67 granos el 14 nov.
- **Granos del par:** `NISAR_L2_PR_GCOV_024_069_D_083_4005_DHDH_A_20260701T000051_20260701T000125_P05023_N_F_J_001` y `NISAR_L2_PR_GCOV_025_069_D_083_4005_DHDH_A_20260713T000050_20260713T000124_P05023_N_F_J_001`.
- **Reserva:** OSM solo tiene un poste kilométrico, así que no hay km oficial para ubicar el tramo.

## S2 · Detectabilidad

**Veredicto: FALLA.** G1 = NO-GO para generar tramos desde detección con GCOV.

**Criterios (14 nov, antes de calcular).** ΔdB = dB(después) − dB(antes), HH y HV, boxcar 5×5 con el `mask` del producto. Zona: franja de 500 m a cada lado del eje de la Ruta 32 en OSM. Umbral: percentil 99.5 del |ΔdB| del control (069 D, 30 ago→11 sep). Mancha: píxeles contiguos sobre el umbral, mínimo 20. PASA si el evento tiene al menos el doble de manchas que el control y se repite en un segundo par.

**Prueba 1 (contar manchas):** FALLA. B (1→13 jul): HH 10, HV 8. D (5→17 oct): HH 9, HV 9. Control: HH 14, HV 9. Para PASA hacían falta 28 y 18.

**Prueba 2 (persistencia, solo B):** PARCIAL. HV 5 de 8 (62 %) contra 4 de 9 (44 %) en el control; HH 6 de 10 contra 8 de 14. No separa. La medida premia fechas «antes» anómalas; una exploración posterior no fijada de antemano dio señales contradictorias y no sirve como prueba.

**Paso A (detección sintética; criterios escritos antes): FALLA.** Parches de cambio inyectados en la imagen «después» del par 069 D 1→13 jul (potencia lineal, antes del boxcar), 200 posiciones aleatorias en la franja (mitad cerca de la carretera, mitad en ladera), HV, umbral 3.5 dB, mancha mínima 9 px.

| Parche | −3 dB | −5 dB | −8 dB |
|---|---|---|---|
| 1×1 | 2.5 % | 2.5 % | 2.5 % |
| 3×3 | 2.5 % | 2.5 % | 4 % |
| 5×5 | 3.5 % | 13.5 % | 52 % |
| 10×10 | 47.5 % | 100 % | 100 % |

- Criterio: 5×5 a −5 dB en ≥70 % con ≤5 falsos/km². Resultado: 13.5 % con 1.1 falsos/km² (el límite es de sensibilidad, no de ruido). **Mínimo detectable: ≈10×10 px (≈1 ha) a −5 dB.** 1×1 y 3×3 son solape casual con el ruido.
- Sensibilidad (no cambia el veredicto, fijado en 9 px): con 3 px el 5×5 a −5 dB llega a 70 % con 3.1 falsos/km²; con 20 px, 2 %.
- Límites: un derrumbe real no es un parche uniforme; solo HV y solo el par 069 D.

**Paso B (exploratorio, sin valor de prueba): negativo.** Manchas de 069 D con una de 105 A a menos de 100 m (HV, 9 px) contra 500 desplazamientos circulares ≥2 km a lo largo de la franja (observadas; media y p95 del nulo): B 0 (3.8; 7), C (25 jul→18 ago) 3 (9.6; 17), D 5 (2.4; 7), F (11→23 sep) 2 (2.5; 5), control 8 (4.6; 9). Ningún evento supera el p95 (tampoco en HH ni con 20 px) y el control queda tan por encima del azar como D.

**Paso C (coherencia GUNW):** no se corrió porque A no pasó.

**Lectura honesta:** con GCOV a 10 m y este flujo no se ven derrumbes pequeños. No se afirma que NISAR no pueda con otros productos; **siguen sin probar** GUNW, offsets, series por píxel y SME2 (S2c). El `mask` del producto no enmascara sombra ni capa invertida del relieve, y no hay prueba de que no hubiera cierre entre el 30 ago y el 11 sep (solo que no aparece en prensa).

## S1′ · Cobertura de SME2 e IMERG (14 nov, tarde)

**PASA con reserva.** CMR, bbox `-84.15,9.95,-83.75,10.25`: `NISAR_L3_SME2_PROVISIONAL_V1` 55 granos desde el 19 jun (uno por pasada de GCOV, 4 tracks: 069 D, 105 A, 170 D, 004 A; una observación cada 2 a 6 días); `NISAR_L3_SME2_BETA_V1` 0. IMERG Late diario `GPM_3IMERGDL` V07: 136 días del 1 jul al 14 nov. Reserva: sin SME2 antes del 19 jun, así que el evento A (feb) queda fuera.

## S2c · SME2 antes de los cierres

**Criterios (14 nov, escritos antes de calcular).**

- Medida: humedad SME2 media en la franja de 500 m a cada lado del eje de la Ruta 32 en OSM, por fecha de paso; cada track y frame por separado.
- Eventos: B (2 jul), C (17 ago), F (13 sep), D (5 oct); A queda fuera por falta de datos. Para cada uno, la última pasada anterior al cierre.
- Línea base: la misma medida, por track, en las fechas sin cierre en prensa (ni los 3 días previos). Cada evento se compara con la línea base de su propio track.
- PASA: en al menos 3 de los 4 eventos, la medida previa supera el percentil 75 de su línea base, y la mediana de los 4 eventos supera la mediana de la línea base.
- FALLA: cualquier otro resultado; la exposición queda solo con IMERG (D5).
- Límites previstos: 4 eventos son pocos (señal, no prueba); SME2 en bosque denso puede ser poco fiable; las fechas de prensa son etiquetas, no verdad de terreno.

**Resultado (14 nov): FALLA.** Scripts y datos en `projects/pipeline/spikes/s2c/` (`measure.py`, `judge.py`, `sme2_strip.csv`). 53 pasadas únicas leídas por ventana (sin bajar los granos); franja de 65,7 km² (1 635 píxeles de 200 m, EASE-Grid 2.0).

| Evento | Pasada previa (069 D f083 · 105 A f007) | Humedad (m³/m³) | Sobre p75 de su línea base |
|---|---|---|---|
| B · 2 jul | 30 jun (1 d antes) · 21 jun (10 d) | 0,366 · 0,351 | sí · sí |
| C · 17 ago | 24 jul (23 d) · 27 jul (20 d) | 0,319 · 0,305 | no · no |
| F · 13 sep | 10 sep (2 d) · 13 sep 05:12, 2 h antes (0 d) | 0,302 · 0,307 | no · no |
| D · 5 oct | 4 oct (0 d) · 25 sep (10 d) | 0,312 · 0,303 | no · no |

- Línea base (pasadas sin cierre ni los 3 días previos): mediana 0,324 (069 D f083, 6 pasadas) y 0,325 (105 A f007, 8). Mediana de los 4 eventos 0,310, **por debajo** de la línea base. Cumplen 1 de 4 (B); hacían falta 3. Con las 5 series con datos: B 4/5, C 0/5, F 0/5, D 0/5.
- Lectura: el único evento que sube es B, justo cuando la humedad es más alta de toda la serie (19 jun–13 jul: 0,35–0,41) y luego baja; es compatible con la estacionalidad, no con una señal previa a los cierres.
- **Las series principales (069 D f083 y 105 A f007, con ≥80 % de la franja válida) se eligieron al ver la cobertura, no antes**; el resultado no depende de eso (ver las 5 series arriba). 004 A y 069 D f084/105 A f006 cubren poco (138 a 620 píxeles, y 105 A f006 pierde cobertura en la serie); 170 D no tiene píxeles válidos en la franja.
- Límites: **ningún píxel de la franja tiene retrieval «recomendado»** (`retrievalQualityFlag` LSB = 1 en todos; producto provisional), así que se promedió todo lo válido. Pasadas previas con 20 a 23 días de distancia en C por el hueco 27 jul–13 ago. Las horas de cierre de B, C y el final de D no están en la prensa (se usó inicio de día). 4 eventos; humedad a 200 m en bosque, no en el talud.
- Qué no se probó: humedad de otra fuente, series por píxel, anomalía respecto a la climatología (solo hay 5 meses de datos).

**S2c v2 (14 nov, criterios escritos antes de recalcular).** Motivo: la revisión de S3 encontró dos cierres que la lista v1 no tenía (17 jul y 8 oct, ver S3). Cambia solo la lista de eventos y el umbral proporcional; el resultado v1 se conserva arriba. Eventos v2: B (2 jul), **B2 (17 jul, 08:35 CR)**, C (17 ago), F (13 sep), D (5 oct, 18:00 CR), **D2 (8 oct, 17:40 CR)**. La línea base excluye las ventanas de los seis. Medida, series y regla de comparación iguales que en v1. PASA si al menos 5 de 6 eventos (≥75 %, como en v1) superan el p75 en todas las series principales y la mediana de los eventos supera la de la línea base; FALLA si no.

**Resultado v2 (14 nov): FALLA.** 2 de 6 eventos sobre p75 en las dos series principales (B y B2, ambos de principios de julio, cuando la humedad es máxima: 0,35–0,41); C, F, D y D2 en 0 de 2. Mediana de eventos 0,310 frente a 0,325 de la línea base. `judge.py sme2_strip.csv v2` lo reproduce. El veredicto no cambia; el 8 oct (D2) cae de nuevo bajo la línea base (0,292). Se asumió un fin de ventana de 2 días para D2 (la prensa no da la reapertura).

## S3 · Eventos de validación

**PARCIAL (revisión del 14 nov).** Cada evento tiene prensa que atribuye el dato al MOPT, pero sigue sin haber comunicado primario: se revisó `mopt.go.cr/noticias` (15 notas de 2026 sobre RN 32; ninguna sobre un cierre por derrumbe, solo obras, demarcación y, el 30 sep, estabilización en los km 28, 31 y 39) y `conavi.go.cr` (remite a redes sociales, sin notas fechadas). Los avisos de cierre salen por redes sociales, que no se consultaron. La CNE no aparece en ningún cierre de 2026. Estas fechas son **etiquetas de validación**, no sirven para elegir dónde mirar.

**Correcciones de esta revisión.** El 17 jul **sí hubo cierre** (había quedado descartado por error): 8:35 a 15:03 (hora CR), km 23 y 24, MOPT, vía [Tico Times](https://ticotimes.net/2026/07/17/costa-rica-route-32-reopens-landslide-july-17). El cierre D terminó poco después de las 10:00 del 6 oct y hubo otro el 8 oct a las 17:40 sin reapertura reportada al 9 oct, MOPT, vía [Tico Times](https://ticotimes.net/2026/10/09/costa-rica-route-32-closed-landslides-limon). El cierre A tuvo un segundo episodio la noche del sábado, ~20:00, km 28, MOPT (la nota es del 15 feb; el 14 feb como fecha es una inferencia), vía [Tico Times](https://ticotimes.net/2026/02/15/costa-ricas-route-32-shuts-down-again-after-landslide-near-zurqui). **Por verificar** (aparecen en búsquedas sin fecha confirmada): cierre del 31 may, cierre de junio en el km 32, y un cierre preventivo desde las 18:00 del 4 nov. Esto indica que la lista de eventos de S3 es incompleta, no cerrada.

| Evento | Fechas según la fuente | Tramo (prensa) | Fuente |
|---|---|---|---|
| A · feb | Cierre la noche del 5 feb; reabre el 6 a las 10:15 y cierra 14:20; sigue cerrada el 8 feb | km 27 y 28, Zurquí | MOPT, vía [El Observador](https://observador.cr/ruta-32-seguira-cerrada-mopt-no-tiene-fecha-de-apertura/) y [Tico Times](https://ticotimes.net/2026/02/09/costa-ricas-key-highway-to-caribbean-remains-blocked-by-slides). Sin datos NISAR (GCOV desde el 19 jun) |
| B · jul | Cierre el 2 jul; el 3 jul reabre 13:40 y cierra 6 h después; limpieza el 4 jul | Zurquí, sin km | MOPT y CONAVI, vía [La Nación](https://www.nacion.com/sucesos/ruta-32-vuelve-a-cerrar-por-caida-de-material/5A4NGHLQTFDGVNKRMWLSZ6YWAM/story/) |
| C · ago | Cierra el 17 ago; el 18 ago sigue cerrada | 8 puntos, km 20 a 37 | MOPT, vía [La Nación](https://www.nacion.com/el-pais/ruta-32-sigue-cerrada-este-martes-mopt-encuentra/7UPYSHM4KFERLHQ3JJWVRMCD4I/story/) y [CRHoy](https://crhoy.com/nacionales/ruta-32-sigue-cerrada-por-8-derrumbes/) |
| F · sep | 13 sep desde las 7:30 (reapertura no confirmada); 18 sep desde las 14:48 | km 26 (18 sep) | [CRHoy](https://crhoy.com/nacionales/cierran-ruta-32-por-lluvias-y-caida-de-material/), sin institución citada |
| D · oct | Cierre la noche del lun 5 oct | km 33, Zurquí | MOPT, vía [CRHoy](https://crhoy.com/nacionales/cierran-la-ruta-32-por-caida-de-material-7/) |

- La Nación (24 ago) cuenta al menos 27 días de cierre en 17 eventos entre el 1 ene y el 23 ago; algunos son preventivos.
- Descartados por no aparecer en ninguna nota: un cierre del 5 nov, y los de 21 jun y 20 jul (el del 17 jul se reincorporó, ver arriba).
- La lista de eventos anterior del proyecto («8–11, 9, 16–17, 20 de julio») queda como no verificada y descartada.

## S4 · Red vial y métrica de impacto

**PARCIAL.** El grafo y la métrica funcionan sobre un área regional; quedan aislamientos dudosos en los bordes. Scripts y comandos en `projects/pipeline/spikes/s4/` (README); las descargas no se commitean.

- **Fuente:** OSM vía Overpass (OSMnx 2.1.1), 14 nov 2026. Clases `motorway`…`unclassified` (+ `_link`), sin `residential`. Áreas: corredor `[-84.10, 9.90, -83.72, 10.25]` y regional `[-84.30, 9.80, -83.40, 10.45]` (con Ruta 126 y Ruta 10). Ruta 32: `ref=32`, 281 vías `trunk`.
- **Tamaño:** corredor 1 687 nodos, 2 216 aristas, 74 componentes (la mayor, 89,6 % de los nodos); regional 6 124 nodos, 7 068 aristas, 590 componentes (la mayor, 73,4 %). `graph.json` del corredor ~990 KB (~540 KB con geometría simplificada a ~10 m).
- **Hospitales y comunidades:** `amenity=hospital` 27 (corredor) / 63 (regional), con ruido (clínica dental, banco de sangre, psiquiátrico, privados); comunidades `place=city/town/village/hamlet` 124 / 718. Distancia al nodo más cercano p50 / p90 / máx = 462 / 2 047 / 7 018 m (corredor) y 783 / 2 896 / 10 089 m (regional). Hospital Guápiles = `way/326924912`.
- **Velocidades del spike:** mediana de `maxspeed` por clase (trunk 60; primary, secondary y tertiary 40; unclassified 30, con solo 20 de 2 319 aristas etiquetadas).
- **Corte 1, Ruta 32 dentro del parque** (una arista simplificada de 34,5 km): 0 comunidades afectadas en las dos áreas del spike (borde este -83.72 y -83.40). En la red hasta Limón (borde -82.95) la medición para G1 dio 1 comunidad aislada, sin revisar a mano. Hospital Calderón Guardia → Guápiles pasa de 68,8 a 146,4 min en el regional (+77,6 min por alterna) y queda sin camino en el corredor. Las cifras 0 y 1 son de redes distintas, no una contradicción.
- **Corte 2, Ruta 32 entre Guápiles y Siquirres** (20,3 km): 51 afectadas, 33 con tiempo extra (mediana 21,2 min, máx 72,8) y 18 aisladas. La revisión a mano (`review_isolated.py`) muestra que **ninguna de las 18 es real**: 3 quedan fuera del grafo (a más de 3 km de una vía), 2 dejan de estar aisladas, 6 están ajustadas a un nodo de la propia Ruta 32 cortada, y 7 no tienen ruta dirigida (probable artefacto de `oneway`).
- **Razonable:** sí la línea base San José→Guápiles (68,8 min) y el desvío (+77,6 min).
- **Riesgos para P3 y P5:** con «hospital más cercano» un corte en el parque no afecta a nadie (hospitales a ambos lados); recortar al corredor crea aislamientos falsos; ojo con comunidades ajustadas a un nodo de la vía cortada y con tramos de un solo sentido. Specs de las dos tareas: `projects/pipeline/deltas/road-graph.spec.md` y `impact-scoring.spec.md`.

## S4′ · Métrica de impacto sobre la red completa (E5)

**Criterios (14 nov, escritos antes de calcular).**

- **Red:** `road_graph.build` de `origin/feat/road-graph` (P3, ya escrito y probado en esa rama, aún no en `main`), extracto OSM nuevo del 14 nov, área `[-84.30, 9.80, -82.95, 10.45]`. Hospitales del spike: `amenity=hospital` con nombre que empieza por «Hospital» (la lista oficial sigue pendiente de Ian). `unclassified` = 30 km/h (supuesto de spike).
- **Tramos:** componentes de aristas de Ruta 32 cortadas en las uniones (grado no dirigido ≠ 2), como en `g1_measure.py`; un tramo por vez.
- **Métricas:** **N**, hospital más cercano (la de P5). **R**, hospital de referencia: el más cercano del conjunto {Calderón Guardia, Guápiles, Tony Facio}; si alguno no está en OSM con nombre, el spike es PARCIAL.
- **Q1, informativa:** al menos el 50 % de los tramos de Ruta 32 tiene comunidades afectadas, y el tramo del parque (punto medio con longitud en [-83,98, -83,92]) también.
- **Q2, sin aislamientos falsos:** una comunidad aislada es **sospechosa** si (i) su nodo es un extremo de una arista cortada, o (ii) tras el corte su componente no dirigido contiene un hospital (queda aislada solo por `oneway`). PASA si ≤ 20 % de los pares (tramo, comunidad aislada) son sospechosos.
- **Veredicto por métrica:** PASA si cumple Q1 y Q2. Se recomienda N si pasa (es la más simple y la del spec); R solo si N falla y R pasa. Si ninguna pasa, FALLA y la decisión queda abierta.
- Sin población (E4 pendiente): `criticality` = 0 para todos; se mide solo con afectadas y tiempo extra.

**Resultado v1 (14 nov): FALLA para N y R.** Red real: 7 136 nodos, 8 715 aristas, 25 hospitales con nombre «Hospital…» (incluye clínicas y psiquiátricos), 758 comunidades; 191 tramos de Ruta 32. Con N, el 60,2 % de los tramos tiene afectadas; con R, 62,8 %. Q1 cumple en el papel, pero **de forma hueca**: el tramo del parque (34,5 km) tiene 1 afectada y es un aislamiento falso (ajustada a un nodo del propio tramo, tiempo extra 0), de modo que el impacto real del parque sigue siendo cero con ambas métricas. Q2 falla: 103 de 103 pares (tramo, comunidad aislada) son sospechosos en las dos métricas (38 ajustadas a un nodo del tramo cortado, 65 aisladas solo por `oneway`; 56 comunidades distintas en 44 tramos). Las tres referencias (Calderón Guardia, Guápiles, Tony Facio) sí están en OSM con nombre. Script `projects/pipeline/spikes/s4/e5_metric.py`.

**Lectura.** El problema no es la elección de hospital sino el ajuste a la red: comunidades ajustadas a nodos de la propia Ruta 32 o a tramos de un solo sentido sin salida. Y el parque no afecta a ninguna comunidad por construcción (nadie vive dentro), con cualquier hospital «cercano».

**S4′ v2 (14 nov, criterios escritos antes de calcular).** Cambios: (a) comunidades y hospitales se re-ajustan al nodo más cercano de la **mayor componente fuertemente conexa** del grafo dirigido (distancia euclídea desde su nodo actual con la longitud escalada por cos 10°; aproximación, porque el grafo no guarda las coordenadas originales); (b) métrica nueva **R2**: tiempo al hospital nacional más cercano de {Calderón Guardia, México, San Juan de Dios}, que sí hace que el parque cuente porque las comunidades al este deben cruzarlo; (c) Q1 cuenta solo afectadas no sospechosas (afectadas menos aisladas sospechosas): ≥ 50 % de los tramos con al menos una, y el tramo del parque también. Q2 igual que en v1 (≤ 20 % sospechosos). PASA por métrica si cumple Q1 y Q2. Recomendación: N si pasa; si no, R2 si pasa; si ninguna, FALLA.

**Resultado v2 (14 nov): FALLA en las tres métricas.** El re-ajuste mueve 8 comunidades (mediana 503 m, máx. 3 100 m) y elimina las 7 sin camino en la línea base; la componente fuerte tiene 6 870 de 7 136 nodos. Pero Q2 sigue en 103 de 103 sospechosos para N y R (38 ajustadas al tramo, 65 por `oneway`). R2 (hospital nacional) sí hace que el parque cuente (310 afectadas no sospechosas) y sube a 70,2 % de tramos con afectadas, pero con 1 219 de 1 219 pares sospechosos (1 181 por `oneway`). Q1 de N y R cae a falso al contar solo afectadas limpias (49,2 % y 51,8 % con parque en 0; R cumple el 50 % pero no el parque).

**Diagnóstico (no era criterio).** En la red, 360 de 414 aristas de Ruta 32 (87 %; 228 de 271 km) son de sentido único: son calzadas separadas. Mi definición de tramo (cortar en uniones) agrupa aristas conectadas, así que un «tramo» es una sola calzada; cerrarla deja la otra abierta en sentido contrario y la comunidad «queda sin ruta» solo en una dirección. Es un defecto de la definición de tramo (de este spike y de lo que P5 haría), no un dato de la carretera.

**S4′ v3 (14 nov, criterios escritos antes de calcular).** Cambio único respecto a v2: cada tramo incluye también las aristas de Ruta 32 cuyo centro queda a menos de ~120 m de alguna arista del tramo (la calzada paralela), y los tramos que comparten aristas se fusionan en un solo cierre. Re-ajuste a la componente fuerte, métricas N, R y R2, Q1 (solo afectadas no sospechosas; ≥ 50 % de los cierres y el parque) y Q2 (≤ 20 % de pares sospechosos) iguales que en v2. Recomendación: N si pasa; si no, R2 si pasa, si no, R; si ninguna, FALLA.

**Resultado v3 (14 nov): R2 PASA; N y R FALLAN.** Cerrar las dos calzadas reduce 191 tramos a **19 cierres** que recorren Ruta 32 de oeste a este (1 a 61 km; el del parque, 60,7 km, `lon` −84,014 a −83,786).

| Métrica | Cierres con afectadas no sospechosas | Parque (afectadas no sospechosas) | Pares aislados | Sospechosos | Q1 | Q2 |
|---|---|---|---|---|---|---|
| N, hospital más cercano | 84,2 % | 133 | 129 | 70 (54,3 %) | sí | **no** |
| R, referencia {Calderón Guardia, Guápiles, Tony Facio} | 89,5 % | 185 | 129 | 70 (54,3 %) | sí | **no** |
| R2, hospital nacional {Calderón Guardia, México, San Juan de Dios} | 94,7 % | 305 | 498 | 63 (12,7 %) | sí | **sí** |

- **Lectura:** con las dos calzadas cerradas, el parque ya deja de dar cero con N y con R (133 y 185 afectadas no sospechosas), pero con N y R los aislamientos «sin ruta a ningún hospital» siguen siendo en su mayoría artefactos de ajuste (43 en un nodo del cierre, 27 por `oneway`). R2 pasa Q2 porque casi todos sus aislados son reales respecto del criterio: comunidades al este de un corte que pierden la ruta a San José (88 a 27 comunidades por cierre al este del km 33).
- **Recomendación (no decisión):** según la regla fijada de antemano, R2. Pero R2 cambia la pregunta: es «ruta al hospital nacional», no «al hospital más cercano», y un aislado en R2 puede tener un hospital regional cerca; la interfaz debe decir «sin ruta al hospital nacional», no «aislada». La decisión de E5 sigue siendo del equipo.
- **Límites.** (1) La fusión de calzadas es gruesa: hay cierres de 33 a 61 km porque las ventanas de 120 m encadenan tramos contiguos; falta una unidad de cierre más fina (por ejemplo, por chainage). (2) El re-ajuste a la componente fuerte usa una distancia aproximada desde el nodo actual, no desde las coordenadas originales (P3 no las guarda). (3) Los hospitales son la regla provisional del spike (nombre «Hospital…»; incluye clínicas y psiquiátricos); la lista oficial sigue pendiente de Ian. (4) Sin población: `criticality` = 0. (5) Sin revisión manual de un caso (la de la V1 sigue pendiente: 18 aislados de la red de Limón no eran reales). (6) 38 a 43 aislados «ajustados al cierre» siguen sin tratarse.
- **Implicación para P5 y P3.** La unidad de cierre debe incluir **ambas calzadas** (87 % de Ruta 32 en OSM es de sentido único) y las comunidades y hospitales deben ajustarse a la mayor componente fuertemente conexa; sin eso, el número de aislados queda dominado por artefactos. Estas dos cosas no están en los specs actuales.

## S5 · IMERG

**Lectura PASA; señal FALLA (14 nov).** Primero GES DISC rechazó la lectura (HTTP 401/403, «Pre authorization required»): hubo que autorizar la aplicación **NASA GESDISC DATA ARCHIVE** en Earthdata. Autorizada, se leyó sin problema. Scripts y datos en `projects/pipeline/spikes/s5/` (`measure.py`, `judge.py`, `imerg_daily.csv`).

- **Lectura:** 317 días completos (1 ene–13 nov; el 14 nov aún no estaba publicado), 9 celdas de 0,1° por día (el borde del bbox cae sobre centros de celda y el redondeo incluyó 3×3; los criterios decían «centro dentro del bbox» sin precisar los bordes), 36 bytes por día en el recorte. Sin días faltantes ni parciales.
- **Señal:** línea base de 258 sumas de 12 días (mediana 104,5 mm; p75 149,2 mm). Eventos sobre p75: **3 de 8** (hacían falta 6). Mediana de eventos 81,3 mm, **por debajo** de la línea base.

| Evento | Suma de 12 días previos | Percentil en la línea base | Sobre p75 |
|---|---|---|---|
| A · 5 feb | 52,5 mm | 26 | no |
| A2 · 14 feb | 37,3 mm | 16 | no |
| B · 2 jul | 36,9 mm | 16 | no |
| B2 · 17 jul | 59,1 mm | 33 | no |
| C · 17 ago | 199,3 mm | 93 | sí |
| F · 13 sep | 103,4 mm | 49 | no |
| D · 5 oct | 253,2 mm | 97 | sí |
| D2 · 8 oct | 245,4 mm | 96 | sí |

- **Lectura honesta:** los tres que superan el p75 (C, D, D2) son de ago–oct, con lluvia previa en el percentil 93–97; los de febrero y julio ocurrieron con poca lluvia en los 12 días previos. Así que la lluvia reciente no explica por sí sola los cierres, aunque los de ago–oct son compatibles con ella. Es una señal parcial, no una regla.
- **Límites:** media de ~1 000 km² a 0,1° sobre un corredor de ladera estrecha; IMERG Late (no el final); día UTC contra horas de cierre en hora CR; horas de inicio asumidas donde la prensa no las da (A al anochecer del 5 feb, A2 ~20:00); fin de ventana de D2 asumido; 8 eventos; no se probó otra duración de acumulación (3, 7 días) porque no estaba en los criterios y probarla ahora sería elegir la que salga mejor.
- **Consecuencia:** el bloque «Exposición» muestra la lluvia como **contexto con la etiqueta «hipótesis»**, sin afirmar relación con los cierres.

**Criterios (escritos antes de leer ningún valor).** Lectura de `GPM_3IMERGDL` V07 (precipitación diaria, día UTC) en las celdas con centro dentro de `[-84.15, 9.95, -83.75, 10.25]`, 1 ene–14 nov. PASA lectura si el recorte pesa menos de 1 MB por día y no faltan días. PASA señal si la lluvia acumulada en los 12 días anteriores al inicio del cierre (A feb 5, A2 feb 14, B, B2, C, F, D, D2) supera el p75 de la misma suma móvil en fechas sin cierre (ni los 3 días previos) en al menos el 75 % de los eventos y la mediana de eventos supera la mediana de la línea base. Si falla, el bloque «Exposición» queda con la lluvia como contexto y sin afirmar relación con los cierres.

## S8 · `graph.ts`

**PASA** (en `main`). `computeAccess(graph, [])` es idéntico al `baseline` de `scenarios.json`; los 4 candidatos del mock coinciden con su `per_community` (T-01 e2, T-02 e3, T-03 e9, T-04 e4; en T-03, c4 queda aislada); se probó una vía `oneway`. Rendimiento: ~0,03 ms por llamada en el mock (9 nodos); ~230 ms en un grafo sintético de 10 000 nodos y 50 comunidades (una medición con `bun`, no en navegador). Un Dijkstra por comunidad: si el grafo real es grande y el recálculo se nota, pasar a una sola búsqueda desde los hospitales. Falta cruzarlo con el grafo real de S4.
