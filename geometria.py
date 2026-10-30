"""
Archivo 1: geometria.py (Rama solucion-2-premium)
Módulo encargado del cálculo de ángulos polares (0° a 360°), distancias Manhattan
al depósito, identificación de pedidos PREMIUM y recorte dinámico de zonas vacías.
"""
import math


def distancia_manhattan(x1: int, y1: int, x2: int, y2: int) -> int:
    """Calcula la distancia en cuadras (Manhattan) entre dos puntos."""
    return abs(x1 - x2) + abs(y1 - y2)


def _es_premium(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor).strip().lower() in ("1", "true", "si", "sí", "verdadero")


def calcular_angulos_y_distancias(
    pedidos: list,
    dep_x: int,
    dep_y: int,
    umbral_hueco_grados: float = 12.0,
) -> list:
    """
    Recibe la lista de pedidos y las coordenadas del depósito.
    Retorna un array ordenado por ángulo (0° a 360°) y distancia al depósito,
    incluyendo el campo 'premium' y el 'angulo_util' que descarta zonas vacías.
    """
    if not pedidos:
        return []

    resultado = []
    for p in pedidos:
        px = int(p["x"])
        py = int(p["y"])
        pid = int(p["id"])
        peso = int(p.get("peso", 0))
        premium = _es_premium(p.get("premium", False))

        dx = px - dep_x
        dy = py - dep_y
        dist_dep = distancia_manhattan(px, py, dep_x, dep_y)

        if dx == 0 and dy == 0:
            angulo = 0.0
        else:
            # atan2 devuelve (-180, 180]; con % 360 lo llevamos siempre a [0°, 360°)
            angulo = math.degrees(math.atan2(dy, dx)) % 360.0

        resultado.append({
            "id": pid,
            "x": px,
            "y": py,
            "peso": peso,
            "premium": premium,
            "angulo": round(angulo, 4),
            "angulo_util": 0.0,
            "distancia_deposito": dist_dep,
        })

    # Ordenamos por ángulo (0° a 360°), priorizando premium en caso de empate y menor distancia al depósito
    resultado.sort(key=lambda item: (item["angulo"], not item["premium"], item["distancia_deposito"]))

    # Recorte de zonas vacías (> umbral_hueco_grados sin ningún pedido)
    angulo_acumulado = 0.0
    resultado[0]["angulo_util"] = 0.0

    for i in range(1, len(resultado)):
        salto = resultado[i]["angulo"] - resultado[i - 1]["angulo"]
        if salto > umbral_hueco_grados:
            salto = 0.001
        angulo_acumulado += salto
        resultado[i]["angulo_util"] = round(angulo_acumulado, 4)

    return resultado
