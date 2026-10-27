# QuickDrop — Simulador oficial

Evalúa un plan de reparto sobre un dataset y calcula su costo según
[ESPECIFICACION.md](ESPECIFICACION.md). Requiere Python 3.9 o superior y no tiene dependencias.

## Uso

```bash
# Evaluar un plan (acepta plan .json o .csv)
python -m quickdrop simular datos/ejemplo datos/ejemplo/plan_ejemplo.json

# Ver cada parada con sus horarios, esperas y fallas
python -m quickdrop simular datos/ejemplo datos/ejemplo/plan_ejemplo.csv --detalle

# Salida en JSON (para scripts o para el ranking)
python -m quickdrop simular datos/ejemplo datos/ejemplo/plan_ejemplo.json --json

# Leer los datos en CSV en lugar de JSON
python -m quickdrop simular datos/ejemplo plan.csv --formato csv

# Generar la versión CSV (o JSON) de un dataset a partir de la otra
python -m quickdrop convertir datos/mi_dataset

# Correr los tests
python -m unittest discover -s tests -t .
```

Códigos de salida: `0` plan válido, `1` error en los datos, `2` plan inválido.

## Lo que tenés que saber para competir

- **Eventos por nivel:** durante la jornada los requisitos cambian. En el Nivel 3 los cambios son
  obligatorios; en el Nivel 2, opcionales (no incorporarlos no invalida tu plan, pero lo hace
  más caro); el Nivel 1 trabaja todo el día sobre el problema base. Un equipo del Nivel 1 puede
  anotarse en el Nivel 2, o en el 3 si usa JSON y Git/GitHub, que ahí son obligatorios.
- **Cierres de entrega:** al anunciarse cada evento (15:50, 16:50 y 17:50) y en el corte final
  de las 18:45. La calidad del plan se mide con la entrega del corte final.
- **Tu puntaje en cada dataset** es `100 × (menor costo del nivel) / (tu costo)`; un plan
  inválido o no entregado vale 0. La calidad del plan se mide en el último cierre; la
  adaptación, el diseño y la defensa los evalúa el jurado.
- **Se evalúa con datasets ocultos**, distintos de los de práctica: 2 o 3 por etapa. Una
  solución ajustada a mano al dataset de práctica no sirve.
- **Leé todo del archivo `mundo`.** El depósito, los costos, la velocidad, los tiempos de
  servicio y de carga pueden cambiar de un dataset a otro, **incluida la ubicación del depósito**.
  Un programa que suponga el depósito en (0,0) va a perder puntos.
- **Las entregas son por la web del simulador.** Al cierre de cada etapa se publica el dataset
  de evaluación; lo descargás, corrés tu programa y subís el plan con el código de tu equipo.
  Hay **unos minutos** para hacerlo: tu programa tiene que generar el plan sin pasos a mano.
- **El costo que te muestra el simulador es exactamente el que se usa para evaluarte.** La web y
  este comando usan el mismo código.
- **Tamaño aproximado de los datasets:** unos 25 pedidos y 3 vehículos en el Nivel 1, y unos
  40 pedidos y 5 vehículos en los Niveles 2 y 3. Hay más vehículos de los estrictamente
  necesarios: **no hace falta usarlos todos**, y decidir cuántos usar es parte del problema.
- **No entregar un pedido no invalida el plan**, pero cuesta `costo_por_falla` (200 por
  defecto).


## Estructura

```
quickdrop/
  modelo.py      entidades (Mundo, Pedido, Vehiculo, Plan); la distancia se define en un solo lugar
  horas.py       "HH:MM" <-> minutos
  cargar.py      lectura y escritura CSV/JSON con los mismos campos
  simulador.py   validación y simulación minuto a minuto
  reporte.py     salida en texto y JSON
  cli.py         línea de comandos
datos/ejemplo/   dataset de ejemplo en ambos formatos + plan de ejemplo
tests/           tests unitarios
```
