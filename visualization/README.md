# Visualizacion (Python)

Todos los scripts se corren desde la raiz del repo.

## Requisitos

```bash
pip install -r requirements.txt
```

---

## Scripts

### animate_vicsek.py

Anima las trayectorias de una simulacion. Muestra flechas coloreadas por angulo de velocidad, slider de frames y boton de pausa. Si hay lider, lo marca en negro.

```bash
python visualization/animate_vicsek.py --outputs-dir simulation/outputs --latest
python visualization/animate_vicsek.py --run-dir simulation/outputs/run_20260320_101530_123
python visualization/animate_vicsek.py --outputs-dir simulation/outputs --latest --save animacion.mp4 --fps 30
python visualization/animate_vicsek.py --outputs-dir simulation/outputs --latest --save animacion.gif
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--run-dir` | Carpeta de un run especifico | — |
| `--outputs-dir` | Carpeta que contiene los runs | — |
| `--latest` | Usar el run mas reciente | — |
| `--stride` | Saltar N frames entre cada cuadro | 1 |
| `--interval` | Milisegundos entre frames (modo interactivo) | 30 |
| `--fps` | FPS al guardar | 30 |
| `--save` | Ruta de salida (.mp4 o .gif) | — |
| `--dpi` | DPI al guardar | 120 |
| `--figsize W H` | Tamaño de figura en pulgadas | 8 8 |
| `--vector-length-scale` | Escala visual de las flechas | 20.0 |
| `--vector-width` | Ancho del eje de las flechas | 0.00525 |

---

### plot_va_time.py

Grafica Va(t) para uno o varios runs. Marca automaticamente el inicio del regimen estacionario.

```bash
python visualization/plot_va_time.py --outputs-dir simulation/outputs --latest-count 3
python visualization/plot_va_time.py --run-dir simulation/outputs/run_xyz
python visualization/plot_va_time.py --outputs-dir simulation/outputs --latest-count 5 --save va_time.png
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--run-dir` | Carpeta de un run (repetible) | — |
| `--outputs-dir` | Carpeta de runs | — |
| `--latest-count` | Cuantos runs recientes incluir | 0 (todos) |
| `--tail-fraction` | Fraccion final para calcular media estacionaria | 0.25 |
| `--tolerance` | Banda de tolerancia para detectar estacionariedad | 0.1 |
| `--stay-steps` | Pasos consecutivos dentro de la banda para confirmar estacionariedad | 100 |
| `--min-step` | No detectar estacionariedad antes de este paso | 100 |
| `--save` | Ruta de salida | — |
| `--dpi` | DPI al guardar | 140 |

---

### plot_va_time_all.py

Grafica Va(t) de todos los runs de una carpeta en un solo grafico, una linea por run.

```bash
python visualization/plot_va_time_all.py --outputs-dir simulation/outputs
python visualization/plot_va_time_all.py --outputs-dir simulation/outputs --latest-count 20
python visualization/plot_va_time_all.py --outputs-dir simulation/outputs --save va_time_all.png
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--outputs-dir` | Carpeta de runs | simulation/outputs |
| `--latest-count` | Incluir solo los N runs mas recientes | 0 (todos) |
| `--max-runs` | Limitar cantidad de runs graficados | 0 (sin limite) |
| `--vline-t` | Paso donde se dibuja la linea de referencia vertical | 300 |
| `--save` | Ruta de salida | — |
| `--dpi` | DPI al guardar | 140 |

---

### plot_va_vs_eta.py

Grafica Va vs eta con barras de error. Para cada eta promedia Va(t) en el regimen estacionario sobre todos los runs disponibles.

```bash
python visualization/plot_va_vs_eta.py --outputs-dir simulation/outputs
python visualization/plot_va_vs_eta.py --outputs-dir simulation/outputs --scenario fixed_leader --transient-step 300
python visualization/plot_va_vs_eta.py --outputs-dir simulation/outputs --save va_vs_eta.png --csv va_vs_eta.csv
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--run-dir` | Carpeta de un run (repetible) | — |
| `--outputs-dir` | Carpeta de runs | — |
| `--scenario` | Filtrar por escenario: `standard`, `fixed_leader`, `circular_leader` | standard |
| `--transient-step` | Descartar pasos anteriores a este valor | 300 |
| `--stationary-end` | Ultimo paso incluido en el promedio | 1000 |
| `--min-runs-per-eta` | Minimo de runs por eta para incluirlo | 1 |
| `--eta-list` | Filtrar por valores de eta especificos | — |
| `--eta-tol` | Tolerancia para el filtro de eta | 1e-9 |
| `--save` | Ruta de salida | — |
| `--csv` | Guardar tabla agregada como CSV | — |
| `--dpi` | DPI al guardar | 140 |

---

### plot_va_vs_eta_compare.py

Igual que `plot_va_vs_eta.py` pero compara los tres escenarios (`standard`, `fixed_leader`, `circular_leader`) en un mismo grafico.

```bash
python visualization/plot_va_vs_eta_compare.py --outputs-dir simulation/outputs
python visualization/plot_va_vs_eta_compare.py --outputs-dir simulation/outputs --transient-step 200 --save va_compare.png
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--run-dir` | Carpeta de un run (repetible) | — |
| `--outputs-dir` | Carpeta de runs | — |
| `--transient-step` | Descartar pasos anteriores a este valor | 200 |
| `--stationary-end` | Ultimo paso incluido en el promedio | 1000 |
| `--min-runs-per-eta` | Minimo de runs por eta para incluirlo | 1 |
| `--eta-list` | Filtrar por valores de eta | — |
| `--eta-tol` | Tolerancia para el filtro de eta | 1e-9 |
| `--save` | Ruta de salida | — |
| `--dpi` | DPI al guardar | 140 |

---

### plot_leader_correlation.py

Para un run con lider, grafica: la orientacion media colectiva theta_S(t) y la correlacion angular C(t) = cos(theta_L - theta_S).

```bash
python visualization/plot_leader_correlation.py --outputs-dir simulation/outputs --latest
python visualization/plot_leader_correlation.py --run-dir simulation/outputs/run_xyz
python visualization/plot_leader_correlation.py --outputs-dir simulation/outputs --latest --save leader_corr.png
```

| Parametro | Descripcion | Default |
|---|---|---|
| `--run-dir` | Carpeta de un run especifico | — |
| `--outputs-dir` | Carpeta de runs | — |
| `--latest` | Usar el run mas reciente | — |
| `--save` | Ruta de salida | — |
| `--dpi` | DPI al guardar | 140 |
