# VANTAGE

> VANTAGE muestra qué tramos de un corredor vial, si se cortan, dejan a comunidades sin ruta a un hospital de referencia y cuánto tiempo extra implica; la lluvia reciente se muestra como contexto, no como predicción. La Ruta 32 (Costa Rica) es el caso de demostración.

VANTAGE responde, para un corredor vial con red en OpenStreetMap: **¿quién pierde la ruta al hospital de referencia si se corta este tramo?** (consecuencia, calculada con la red vial de OSM, hospitales y población) y muestra la **lluvia reciente** (IMERG) como contexto. Nuestro caso de demostración es la Ruta 32 (Costa Rica); el método no se ha probado en otro lugar. Es nuestra propuesta para el reto **"Dancing with the SARs"** de NASA Space Apps 2026.

**Resultados negativos.** Probamos tres señales con criterios escritos antes de calcular y ninguna separa los cierres de los días normales: (1) NISAR GCOV a 10 m no detecta cambio a escala de derrumbe pequeño (mínimo detectable ≈10×10 píxeles, ≈1 ha, a −5 dB); (2) la humedad del suelo SME2 supera su línea base antes de solo 2 de 6 cierres; (3) la lluvia IMERG de los 12 días previos la supera antes de solo 3 de 8. No afirmamos que NISAR no pueda con otros productos (GUNW, offsets, series por píxel); quedan sin probar. Detalle en [`context/approach.md`](context/approach.md).

Los resultados son **tramos críticos por consecuencia**, no derrumbes confirmados; la exposición es una **hipótesis**, nunca una causa. Está diseñado para generalizarse a corredores con red vial en OSM, pero solo se demuestra en la Ruta 32.

## Cómo funciona

El proyecto tiene dos partes conectadas solo por archivos de datos:

1. **Pipeline (Python, sin conexión):** red vial de OpenStreetMap → impacto en el acceso a hospitales (consecuencia) → contexto de lluvia (IMERG). La detección de cambio por radar es opcional y experimental, y la zona de análisis es un parámetro.
2. **Aplicación web (estática):** muestra los resultados en un mapa y permite simular el cierre de un tramo, recalculado en el navegador y sin servidor.

## Estado

Proyecto en construcción durante el hackathon (14–15 de noviembre de 2026). Hoy existen el esqueleto del frontend y del pipeline, y el contrato de datos (esquemas, mocks y validador). Tras la puerta G1 (sáb 14 nov, ~16:35: NO-GO para detectar cicatrices con GCOV) y tras los demás spikes el producto es la consecuencia (criticidad) de cada tramo, con la lluvia como contexto (decisión D8); ver `STATUS.md`. El contrato está en 0.2.

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

Se gestiona con `uv`. Desde `projects/pipeline/`: `uv sync` instala, `uv run pytest` corre las pruebas y `uv run pipeline` ejecuta (por ahora solo imprime un saludo).

### Datos (desde la raíz)

| Comando | Qué hace |
|---|---|
| `make mock` | Reemplaza `projects/frontend/public/storage/` con los datos de ejemplo del contrato |
| `make publish` | Reemplaza esa carpeta con la salida del pipeline (`projects/pipeline/output/`, sí se commitea) |
| `make validate` | Valida esa carpeta contra los esquemas de `projects/contract/schemas/` |

`public/storage/` no se commitea: hay que generarlo con `make mock` (o `make publish`) antes de `bun run dev`.

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

- NISAR (NASA/JPL): GCOV y SME2, para los resultados negativos de detectabilidad y de humedad del suelo
- IMERG Late (NASA GPM)
- WorldPop (población)
- © colaboradores de OpenStreetMap (ODbL)
