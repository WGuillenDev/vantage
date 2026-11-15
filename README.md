# VANTAGE

> VANTAGE muestra qué tramos de un corredor vial, si se cortan, dejan a comunidades sin ruta a un hospital de referencia y cuánto tiempo extra implica; la lluvia reciente se muestra como contexto, no como predicción. La Ruta 32 (Costa Rica) es el caso de demostración.

VANTAGE responde, para un corredor vial con red en OpenStreetMap: **¿quién pierde la ruta al hospital de referencia si se corta este tramo?** (consecuencia, calculada con la red vial de OSM, hospitales y población) y muestra la **lluvia reciente** (IMERG) como contexto. Nuestro caso de demostración es la Ruta 32 (Costa Rica); el método no se ha probado en otro lugar. Es nuestra propuesta para el reto **"Dancing with the SARs"** de NASA Space Apps 2026.

**Resultados negativos.** Probamos tres señales con criterios escritos antes de calcular y ninguna separa los cierres de los días normales: (1) NISAR GCOV a 10 m no detecta cambio a escala de derrumbe pequeño (mínimo detectable ≈10×10 píxeles, ≈1 ha, a −5 dB); (2) la humedad del suelo SME2 supera su línea base antes de solo 2 de 6 cierres; (3) la lluvia IMERG de los 12 días previos la supera antes de solo 3 de 8. No afirmamos que NISAR no pueda con otros productos (GUNW, offsets, series por píxel); quedan sin probar. Detalle en [`context/approach.md`](context/approach.md).

Los resultados son **tramos críticos por consecuencia**, no derrumbes confirmados; la exposición es una **hipótesis**, nunca una causa. Está diseñado para generalizarse a corredores con red vial en OSM, pero solo se demuestra en la Ruta 32.

## Cómo funciona

El proyecto tiene dos partes conectadas solo por archivos de datos:

1. **Pipeline (Python, sin conexión):** red vial de OpenStreetMap → impacto en el acceso a hospitales (consecuencia) → contexto de lluvia (IMERG). La zona de análisis es un parámetro (un archivo en `projects/pipeline/configs/`). La detección de cambio por radar no forma parte del producto: probada y descartada (ver resultados negativos).
2. **Aplicación web (estática):** muestra los resultados en un mapa y permite simular el cierre de un tramo, recalculado en el navegador y sin servidor.

## Estado

Proyecto del hackathon (14–15 de noviembre de 2026). El pipeline y la aplicación web funcionan con **datos reales de la Ruta 32 (San José–Limón)**; el contrato de datos está en la versión 0.3. La zona se publica como **«no validada»**: la revisión manual de sus aislamientos no pasó el criterio (ver Resultados). Decisiones y estado de cada tarea en [`STATUS.md`](STATUS.md); plan de cierre en [`planning.md`](planning.md).

## Resultados con datos reales (Ruta 32)

| Qué | Resultado |
|---|---|
| Red y zona | Extracto OSM del 15 nov 2026; 7 136 nodos, 8 715 aristas, 758 comunidades (WorldPop 2020, estimada; 2 899 678 hab. frente a 2 957 560 del ráster, −2 %) |
| Hospitales de referencia | Calderón Guardia, México y San Juan de Dios (San José). **El orden de los tramos depende de este conjunto:** con Tony Facio y Guápiles añadidos, el top 20 no coincide en ninguno (`planning.md`, D5) |
| Unidades de cierre | 115, cortadas en cada unión de la red, con las dos calzadas; 100 con impacto. Los cinco primeros son tramos de un mismo cuello de botella (~311 comunidades afectadas) |
| Estabilidad del ranking | Top 5 y top 10 iguales al variar ×0,8 y ×1,2 todas las velocidades y al quitar cada hospital (`pass`). El factor de velocidad es uniforme, así que casi no puede cambiar el orden |
| Tiempos | 20 pares contra el router público OSRM: error relativo mediano 15,3 % (umbral 25 %, `pass`), el modelo es 15 % más rápido. Las velocidades son los límites publicados de OSM por clase de vía, no velocidades de viaje; 4 tiempos de referencia citados (errores de 10 % a 34 %) |
| Revisión manual | 4 comunidades aisladas de 3 unidades: **0 reales**, las 4 son artefactos de enganche (veredicto `fail`, se exigía ≥ 80 %). 208 de 965 aislamientos (21,6 %) están marcados como sospechosos; excluirlos o reenganchar las comunidades deja el top 10 igual |
| Lluvia | IMERG Late diario, 317 días (1 ene–13 nov 2026), acumulado de 12 días por tramo, como contexto |

Los informes están en `projects/pipeline/reports/ruta-32/` y las mediciones en `projects/pipeline/spikes/`.

## Límites

- Se demuestra solo en la Ruta 32; no se probó en otra zona ni país. La idea de «hospital de referencia» puede no trasladarse.
- Los aislamientos («sin ruta al hospital de referencia») incluyen artefactos del modelo; la aplicación los marca. La red solo trae vías hasta la clase `unclassified`: no incluye caminos locales.
- Los tiempos salen de límites de velocidad publicados, no de mediciones de viaje; `unclassified` se apoya en 22 vías etiquetadas.
- Limón queda sin ruta a un hospital de referencia en 22 unidades: todas al este de Siquirres, el único tramo sin alternativa. Limón tiene su propio hospital, que no cuenta como referencia.
- La aplicación se probó en un viewport móvil emulado, no en un celular físico.

## Estructura

```
vantage/
├── context/            # documentación de orientación
├── projects/
│   ├── contract/       # esquemas JSON y datos de ejemplo
│   ├── pipeline/       # Python (uv)
│   └── frontend/       # Bun + TypeScript + React + Vite
└── .claude/            # reglas, skills y permisos de Claude Code
```

## Requisitos

| Herramienta | Para qué |
|---|---|
| Git | Control de versiones |
| Bun | Frontend (TypeScript, React, Vite) |
| uv | Pipeline (Python y dependencias) |
| make | Comandos del repositorio (`Makefile` en la raíz) |

Los comandos de abajo son para Windows con [Scoop](https://scoop.sh).

### 1. Instalar Scoop

En PowerShell (sin permisos de administrador):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

### 2. Instalar las herramientas

```powershell
scoop install git bun uv make
```

Opcional, para trabajar con GitHub desde la terminal:

```powershell
scoop install gh
```

### 3. Verificar

```powershell
git --version
bun --version
uv --version
make --version
```

## Puesta en marcha

Clonar el repositorio e instalar las dependencias del frontend:

```powershell
git clone <url-del-repositorio> vantage
cd vantage/projects/frontend
bun install
```

### Frontend

Desde `projects/frontend/`:

| Comando | Qué hace |
|---|---|
| `bun run dev` | Servidor de desarrollo |
| `bun run build` | Compila la aplicación en `dist/` |
| `bun run lint` | Revisa el código con oxlint |
| `bun run preview` | Sirve localmente la compilación |

### Pipeline

Se gestiona con `uv`. Pruebas, desde la raíz: `uv run --project projects/pipeline pytest`. La zona se define en `projects/pipeline/configs/<zona>.toml` (bbox, hospitales de referencia, velocidades por clase de vía, ráster de población, periodo de lluvia).

Corrida completa de la Ruta 32, desde la raíz:

```powershell
make osm AREA=ruta-32        # descarga la red de OSM (Overpass, red)
make worldpop AREA=ruta-32   # descarga el ráster WorldPop (31,5 MB, red)
make imerg AREA=ruta-32      # descarga IMERG (red y credenciales de Earthdata)
make all AREA=ruta-32        # genera projects/pipeline/output/ruta-32/ (sin red)
make publish validate        # copia al sitio y valida contra los esquemas
```

Las descargas van a `projects/pipeline/work/`, que no se commitea (salvo las celdas IMERG). `make imerg` necesita una cuenta de Earthdata con la aplicación «NASA GESDISC DATA ARCHIVE» autorizada y las variables `EARTHDATA_USERNAME` y `EARTHDATA_PASSWORD` (o una entrada en `~/.netrc`).

Informes de confiabilidad, cada uno escribe en `projects/pipeline/reports/<zona>/`:

| Comando | Qué mide |
|---|---|
| `make sensitivity AREA=ruta-32` | Cuánto cambia el ranking al variar las velocidades y quitar cada hospital |
| `make timecheck AREA=ruta-32` | Tiempos del modelo contra el router OSRM público y contra referencias citadas (`reference_times.json`) |
| `make review-prepare AREA=ruta-32` y `make review-summary AREA=ruta-32` | Hoja para clasificar a mano los aislamientos, y su veredicto |

### Datos (desde la raíz)

| Comando | Qué hace |
|---|---|
| `make mock` | Reemplaza `projects/frontend/public/storage/` con los datos de ejemplo del contrato |
| `make publish` | Reemplaza esa carpeta con la salida del pipeline (`projects/pipeline/output/`, sí se commitea) |
| `make validate` | Valida esa carpeta contra los esquemas de `projects/contract/schemas/` |
| `make all AREA=<zona>` | Corre las etapas del pipeline para una zona y escribe `projects/pipeline/output/` |

`public/storage/` no se commitea: hay que generarlo con `make publish` (datos reales) o `make mock` (datos de ejemplo) antes de `bun run dev`. El despliegue en GitHub Pages corre `make publish`.

### Pruebas en el navegador (opcional)

El repositorio incluye el servidor MCP de Playwright (`.mcp.json`) para que Claude Code pruebe el frontend. Si pide un navegador la primera vez, se instala con:

```powershell
bunx playwright install chromium
```

## Método de trabajo

Las funcionalidades se describen como especificaciones vivas en la carpeta `deltas/` de cada proyecto, y se trabajan con tres skills de Claude Code:

| Skill | Qué hace |
|---|---|
| `/drafter <slice>` | Entrevista y escribe la especificación |
| `/builder <slice>` | Propone un plan y construye con pruebas primero |
| `/breaker <slice>` | Intenta romper lo que ya está construido y probado |

## Documentación

- [`context/approach.md`](context/approach.md): qué es el proyecto, el método y el alcance.
- [`context/functions.md`](context/functions.md): qué hace cada función.
- [`context/structure.md`](context/structure.md): arquitectura, estructura y despliegue.
- [`context/contracts.md`](context/contracts.md): referencia de los archivos de datos.

## Licencia y atribuciones

Código bajo licencia MIT. Los datos provienen de:

- NISAR (NASA/JPL): GCOV y SME2, solo para los resultados negativos de detectabilidad y de humedad del suelo; la aplicación no muestra datos de NISAR
- IMERG Late (NASA GPM)
- WorldPop (población)
- © colaboradores de OpenStreetMap (ODbL)
