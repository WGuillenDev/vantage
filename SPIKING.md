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
| S2c | pendiente | SME2: ¿sube la humedad del suelo antes de los cierres? Máx. 40 min, criterios escritos antes. |
| S3 | PARCIAL | Cierres de 2026 con prensa que cita al MOPT; falta el comunicado primario. |
| S4 | PARCIAL | El grafo funciona, pero «hospital más cercano» da cero en el 43 % de los tramos. Mediciones contradictorias (ver `STATUS.md`). _Fuente: informe de situación; sin ficha propia._ |
| S5 | sin avanzar | IMERG sin probar. _Fuente: informe de situación._ |
| S6 | PASA | MapLibre carga el mock en dev, build y Pages (https://wguillendev.github.io/vantage/), sin errores de consola. |
| S7 | PASA | WorldPop CRI 2020 (100 m): 31,5 MB por HTTPS, sin streaming; se recorta con `rasterio`. 946 290 personas en el `bbox` provisional `[-84.20, 9.95, -83.70, 10.30]`. Es una estimación modelada, no un censo. |
| S8 | PASA en rama | `graph.ts` coincide con el mock; no está en `main`. _Fuente: informe de situación._ |

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

## S3 · Eventos de validación

**PARCIAL.** Cada evento tiene prensa que atribuye el dato al MOPT, pero falta el comunicado primario (el MOPT publicó por Facebook). La CNE no aparece en ningún cierre de 2026. Estas fechas son **etiquetas de validación**, no sirven para elegir dónde mirar.

| Evento | Fechas según la fuente | Tramo (prensa) | Fuente |
|---|---|---|---|
| A · feb | Cierre la noche del 5 feb; reabre el 6 a las 10:15 y cierra 14:20; sigue cerrada el 8 feb | km 27 y 28, Zurquí | MOPT, vía [El Observador](https://observador.cr/ruta-32-seguira-cerrada-mopt-no-tiene-fecha-de-apertura/) y [Tico Times](https://ticotimes.net/2026/02/09/costa-ricas-key-highway-to-caribbean-remains-blocked-by-slides). Sin datos NISAR (GCOV desde el 19 jun) |
| B · jul | Cierre el 2 jul; el 3 jul reabre 13:40 y cierra 6 h después; limpieza el 4 jul | Zurquí, sin km | MOPT y CONAVI, vía [La Nación](https://www.nacion.com/sucesos/ruta-32-vuelve-a-cerrar-por-caida-de-material/5A4NGHLQTFDGVNKRMWLSZ6YWAM/story/) |
| C · ago | Cierra el 17 ago; el 18 ago sigue cerrada | 8 puntos, km 20 a 37 | MOPT, vía [La Nación](https://www.nacion.com/el-pais/ruta-32-sigue-cerrada-este-martes-mopt-encuentra/7UPYSHM4KFERLHQ3JJWVRMCD4I/story/) y [CRHoy](https://crhoy.com/nacionales/ruta-32-sigue-cerrada-por-8-derrumbes/) |
| F · sep | 13 sep desde las 7:30 (reapertura no confirmada); 18 sep desde las 14:48 | km 26 (18 sep) | [CRHoy](https://crhoy.com/nacionales/cierran-ruta-32-por-lluvias-y-caida-de-material/), sin institución citada |
| D · oct | Cierre la noche del lun 5 oct | km 33, Zurquí | MOPT, vía [CRHoy](https://crhoy.com/nacionales/cierran-la-ruta-32-por-caida-de-material-7/) |

- La Nación (24 ago) cuenta al menos 27 días de cierre en 17 eventos entre el 1 ene y el 23 ago; algunos son preventivos.
- Descartados por no aparecer en ninguna nota: un cierre del 5 nov, y los de 21 jun, 17 jul y 20 jul.
- La lista de eventos anterior del proyecto («8–11, 9, 16–17, 20 de julio») queda como no verificada y descartada.
