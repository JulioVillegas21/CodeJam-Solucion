# QuickDrop — Especificación del mundo y de los formatos

Versión 1.0 (calibrada para la jam).

Este documento es la referencia común para todos los niveles. El simulador oficial
implementa exactamente lo que dice acá; si hay diferencia entre este documento y el
simulador, es un error y se corrige antes de la jam.

---

## 1. El mundo

- La ciudad es una **grilla de 20 × 20** cuadras. Las coordenadas son enteros:
  `x` e `y` van de `0` a `19`.
- La distancia entre dos puntos es **Manhattan**: `|x1 - x2| + |y1 - y2|`, medida en cuadras.
- Todos los vehículos salen del **depósito** a la **hora de salida** y deben terminar
  en el depósito (la vuelta final es implícita; no hace falta escribirla en el plan).
- Todos los tiempos se manejan en **minutos enteros**. Las horas se escriben `"HH:MM"`.

## 2. Archivos de entrada

Cada dataset es una carpeta con tres archivos, disponibles en **ambos formatos**
(los campos son exactamente los mismos en CSV y en JSON):

```
datos/<nombre>/
  mundo.json      mundo.csv
  pedidos.json    pedidos.csv
  vehiculos.json  vehiculos.csv
```

### 2.1 Mundo

| Campo | Tipo | Defecto | Significado |
|---|---|---|---|
| `grilla_ancho` | entero | 20 | Cantidad de columnas (x va de 0 a ancho-1) |
| `grilla_alto` | entero | 20 | Cantidad de filas (y va de 0 a alto-1) |
| `deposito_x`, `deposito_y` | entero | 0, 0 | Ubicación del depósito |
| `hora_salida` | hora | `"08:00"` | Hora a la que salen todos los vehículos |
| `tiempo_servicio` | entero | 5 | Minutos que lleva cada entrega |
| `tiempo_carga` | entero | 10 | Minutos que lleva volver a cargar en el depósito entre viajes |
| `min_por_cuadra` | entero | 3 | Minutos por cuadra de los vehículos |
| `costo_por_cuadra` | número | 3 | Peso de la distancia en el costo |
| `costo_por_vehiculo` | número | 60 | Costo fijo de usar un vehículo |
| `costo_por_minuto_total` | número | 1 | Peso del tiempo total (makespan) |
| `costo_por_falla` | número | 200 | Penalización por cada pedido que falla |
| `costo_por_minuto_premium` | número | 1 | Peso de la demora de los pedidos premium |

JSON: un objeto plano con esos campos.

```json
{ "grilla_ancho": 20, "grilla_alto": 20, "deposito_x": 0, "deposito_y": 0,
  "hora_salida": "08:00", "tiempo_servicio": 5, "tiempo_carga": 10, "min_por_cuadra": 3,
  "costo_por_cuadra": 3, "costo_por_vehiculo": 60, "costo_por_minuto_total": 1,
  "costo_por_falla": 200 }
```

CSV: dos columnas, `clave,valor`, una fila por campo.

### 2.2 Pedidos

| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `id` | entero | sí | Identificador único |
| `x`, `y` | entero | sí | Ubicación del cliente |
| `peso` | entero | sí | Peso del paquete (kg) |
| `premium` | booleano | no (falso) | Cliente premium: cuenta cuánto tarda en recibir (§6) |

```json
[
  { "id": 1, "x": 15, "y": 8, "peso": 12 },
  { "id": 2, "x": 6, "y": 14, "peso": 4 }
]
```

```csv
id,x,y,peso
1,15,8,12
2,6,14,4
```

Pedido premium: `{ "id": 2, "x": 6, "y": 14, "peso": 4, "premium": true }`; en CSV, la columna
`premium` con `1` o `0`.

### 2.3 Vehículos

| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `id` | texto | sí | Identificador único |

Todos los vehículos salen del depósito, tardan `min_por_cuadra` minutos por cuadra y cuestan
`costo_por_vehiculo` si se usan.

```json
[ { "id": "V1" }, { "id": "V2" } ]
```

```csv
id
V1
V2
```

### 2.4 Convenciones comunes

- Un campo opcional puede **faltar**, valer `null` (JSON) o estar **vacío** (CSV): las tres
  formas significan lo mismo.
- Booleanos en CSV: `1`/`0` (también se aceptan `true`/`false`, `si`/`no`).
- CSV: separador `,` (se acepta `;`), codificación UTF-8, primera fila con encabezados.
- Si un archivo tiene campos que tu programa no conoce, ignoralos.

## 3. Archivo de salida: el plan

El programa de cada equipo produce un plan. Para cada vehículo, una lista ordenada de
**paradas**: un `id` de pedido o la palabra `DEPOSITO` (volver al depósito e iniciar un nuevo
viaje).

JSON:

```json
{
  "rutas": [
    { "vehiculo": "V1", "paradas": [2, 1, 10, "DEPOSITO", 8, 3] },
    { "vehiculo": "V2", "paradas": [4, 9, 7] }
  ]
}
```

CSV: una fila por parada, en orden. Las filas de un mismo vehículo forman su ruta en el
orden en que aparecen.

```csv
vehiculo,parada
V1,2
V1,1
V1,10
V1,DEPOSITO
V1,8
V1,3
V2,4
V2,9
V2,7
```

Los vehículos que no aparecen en el plan no se usan.

## 4. Cómo simula el simulador

Para cada vehículo, empezando en el depósito a la `hora_salida`:

1. **Viaje a la parada.** Tarda `cuadras × min_por_cuadra` del vehículo.
2. **Parada en un pedido:** la entrega se realiza al llegar y el vehículo queda ocupado
   `tiempo_servicio` minutos.
3. **Parada `DEPOSITO`:** vuelve al depósito y tarda `tiempo_carga` minutos. Ahí empieza un
   nuevo viaje.
4. Al terminar las paradas, **vuelve al depósito** (sin tiempo de carga).

El simulador **calcula todas las horas**. Si el plan trae horas propias, se ignoran.

## 5. Validez del plan

Un plan es **inválido** (no recibe puntaje en ese dataset) si:

- usa un vehículo que no existe, o un mismo vehículo en más de una ruta (JSON);
- incluye un pedido que no existe;
- incluye un mismo pedido más de una vez.

Un pedido que **no aparece** en el plan no invalida el plan: **falla**.

## 6. Costo (menor es mejor)

```
costo = costo_por_cuadra         × distancia total (cuadras, todos los vehículos)
      + costo fijo               de cada vehículo usado (con al menos un pedido)
      + costo_por_minuto_total   × makespan (minutos desde la salida hasta que vuelve el último vehículo)
      + costo_por_falla          × pedidos que fallan (§5)
      + costo_por_minuto_premium × Σ minutos desde la salida hasta la entrega de cada premium entregado
```

Puntaje por dataset para el ranking, dentro de cada nivel:

```
puntaje = 100 × (menor costo válido del nivel) / (costo del equipo)
```

