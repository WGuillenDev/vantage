# CHANGES — estado del árbol de trabajo (sáb 14 nov 2026)

Todo está **sin commitear** (sin git add, commit, pull ni push). La carpeta de spikes la borraste vos: no queda `PROGRESS.md` ni scripts; los números están en `SPIKING.md`.

## Qué cambió

- **Dirección G1 (NO-GO en detección, riesgo = consecuencia × exposición):** `context/approach.md`, `structure.md`, `functions.md`, `contracts.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`.
- **Contrato 0.2:** `projects/contract/` (schemas, mocks, `shared/no-toggle`) y `validate.py` con sus tests. `passes` y `overlays` opcionales; nuevos opcionales `detection_limits`, `exposure_sources`, `candidates[].source`, `candidates[].exposure`. 12 tests pasan y `make validate` da OK.
- **Poda (modo solo):** `STATUS.md` pasó de 222 a ~110 líneas y `SPIKING.md` de 397 a ~100. Se quitaron turnos, relevos, bloqueos, dueños por persona, orden de trabajo, plantillas vacías de fichas, la barra de progreso y la regla de revisión de ambos lados. Se cortaron **F2** (mostrar pasadas) y **F9** (antes/después), que dependían de una capa de radar que no existe. P4 se fundió en P5. Quedan duplicadas a propósito solo las cifras de detectabilidad en `approach.md` §5 y `SPIKING.md` S2.
- **Contradicciones resueltas:** estado de S4/S5/S8 (se usó el informe y se marcó la fuente), eventos de S3 (lista única en `SPIKING.md`), agosto 17–18 (según `SPIKING.md`), `project/` vs `projects/`.

## Pendiente de tu decisión

- **Contradicciones que siguen:** S4 (0 comunidades afectadas en el parque vs 1 aislada) y el plan B de S4 («reducir al corredor» empeora el resultado). Están en `STATUS.md`.
- **CODEOWNERS:** la protección de `main` exige revisión de un dueño de código; trabajando solo hay que desactivarla o usar bypass. No se tocó.
- **Frontend sin tocar:** `App.tsx:89` dice «Señal de cambio candidata» y `App.tsx:34` hace `meta.overlays.find(...)` (falla si `overlays` falta). `pyproject.toml:4` aún dice «NISAR change detection».
- **`rain.start/end`** sigue obligatorio en `meta.json` aunque no haya pasadas.
- `sample.md` y `prompt.md` (sin trackear) conservan el planteamiento anterior.
