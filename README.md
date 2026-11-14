# VANTAGE

> NISAR ve dónde se movió la montaña; VANTAGE dice a quién deja sin salida.

VANTAGE usa datos de radar de NISAR para mostrar **dónde se movió una ladera cerca de la Ruta 32 (Costa Rica)** y **qué comunidades pierden una buena ruta hacia un hospital** por ese movimiento. Es nuestra propuesta para el reto **"Dancing with the SARs"** de NASA Space Apps 2026.

Un cambio de radar es una **señal, no una confirmación**: los resultados son *tramos candidatos* que hay que verificar en campo.

## Cómo funciona

El proyecto tiene dos partes conectadas solo por archivos de datos:

1. **Pipeline (Python, sin conexión):** detecta cambios en la superficie con NISAR, los cruza con la red vial de OpenStreetMap y calcula el efecto en el acceso a hospitales.
2. **Aplicación web (estática):** muestra los resultados en un mapa y permite simular el cierre de un tramo, recalculado en el navegador y sin servidor.

## Estado

Proyecto en construcción durante el hackathon (14–15 de noviembre de 2026). Hoy existen el esqueleto del frontend y del pipeline, y el contrato de datos (esquemas, mocks y validador).

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
| `make validate` | Valida esa carpeta contra los esquemas de `projects/contract/schemas/` |

`public/storage/` no se commitea: hay que generarlo con `make mock` antes de `bun run dev`.

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

- NISAR GCOV (NASA/JPL)
- IMERG Late (NASA GPM)
- © colaboradores de OpenStreetMap (ODbL)
