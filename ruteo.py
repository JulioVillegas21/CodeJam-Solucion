"""
ruteo.py — ALGORITMO BASE (SIN PREMIUM)
Implementa:
1. División de pedidos en franjas angulares según la cantidad de autos (k),
   descartando zonas vacías sin pedidos.
2. Metaheurística GRASP + Búsqueda Local 2-Opt (Iriarte, UBA 2018) enfocada
   en minimizar la distancia total en cuadras y el makespan.
3. Cálculo del array de costos base (distancia, vehículos, tiempo, fallas).
"""
import random
from geometria import distancia_manhattan


def dividir_en_franjas_por_angulo(pedidos_ordenados: list, cantidad_autos: int) -> list:
    """
    Divide los pedidos según su 'angulo_util' (con zonas vacías ya descartadas)
    en 'cantidad_autos' franjas de igual amplitud angular útil.
    """
    if not pedidos_ordenados or cantidad_autos <= 0:
        return []
    if cantidad_autos == 1:
        return [list(pedidos_ordenados)]

    min_ang = pedidos_ordenados[0]["angulo_util"]
    max_ang = pedidos_ordenados[-1]["angulo_util"]
    amplitud_total = max_ang - min_ang

    if amplitud_total <= 1e-6:
        return dividir_en_franjas_balanceadas(pedidos_ordenados, cantidad_autos)

    ancho_franja = amplitud_total / cantidad_autos
    franjas = [[] for _ in range(cantidad_autos)]

    for p in pedidos_ordenados:
        indice = int((p["angulo_util"] - min_ang) / ancho_franja)
        if indice >= cantidad_autos:
            indice = cantidad_autos - 1
        franjas[indice].append(p)

    return [f for f in franjas if len(f) > 0]


def dividir_en_franjas_balanceadas(pedidos_ordenados: list, cantidad_autos: int) -> list:
    """Divide los pedidos ya ordenados por ángulo en 'cantidad_autos' franjas parejas."""
    if not pedidos_ordenados or cantidad_autos <= 0:
        return []
    n = len(pedidos_ordenados)
    k = min(cantidad_autos, n)
    franjas = []
    base = n // k
    resto = n % k
    inicio = 0
    for i in range(k):
        fin = inicio + base + (1 if i < resto else 0)
        franjas.append(pedidos_ordenados[inicio:fin])
        inicio = fin
    return franjas


def costo_distancia_ruta(paradas: list, dep_x: int, dep_y: int) -> int:
    """Calcula las cuadras totales: Depósito -> Parada 1 -> ... -> Parada N -> Depósito."""
    if not paradas:
        return 0
    dist = distancia_manhattan(dep_x, dep_y, paradas[0]["x"], paradas[0]["y"])
    for i in range(len(paradas) - 1):
        dist += distancia_manhattan(
            paradas[i]["x"], paradas[i]["y"],
            paradas[i + 1]["x"], paradas[i + 1]["y"]
        )
    dist += distancia_manhattan(paradas[-1]["x"], paradas[-1]["y"], dep_x, dep_y)
    return dist


def construir_grasp(pedidos_franja: list, dep_x: int, dep_y: int, alpha: float, rng: random.Random) -> list:
    """Fase constructiva GRASP estándar por cercanía Manhattan."""
    pendientes = list(pedidos_franja)
    ruta = []
    actual_x, actual_y = dep_x, dep_y

    while pendientes:
        distancias = [
            (distancia_manhattan(actual_x, actual_y, p["x"], p["y"]), p)
            for p in pendientes
        ]
        d_min = min(d for d, _ in distancias)
        d_max = max(d for d, _ in distancias)
        umbral = d_min + alpha * (d_max - d_min)

        rcl = [p for d, p in distancias if d <= umbral]
        elegido = rng.choice(rcl)

        ruta.append(elegido)
        pendientes.remove(elegido)
        actual_x, actual_y = elegido["x"], elegido["y"]

    return ruta


def busqueda_local_2opt(ruta: list, dep_x: int, dep_y: int) -> list:
    """Fase de mejora local 2-Opt para eliminar cruces de trayectoria."""
    n = len(ruta)
    if n <= 2:
        return list(ruta)

    mejor = list(ruta)
    mejor_dist = costo_distancia_ruta(mejor, dep_x, dep_y)
    mejoro = True

    while mejoro:
        mejoro = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                candidata = mejor[:i] + mejor[i:j + 1][::-1] + mejor[j + 1:]
                nueva_dist = costo_distancia_ruta(candidata, dep_x, dep_y)
                if nueva_dist < mejor_dist:
                    mejor = candidata
                    mejor_dist = nueva_dist
                    mejoro = True
    return mejor


def optimizar_ruta_grasp_2opt(
    pedidos_franja: list,
    dep_x: int,
    dep_y: int,
    iteraciones: int = 35,
    semilla: int = 42,
) -> list:
    """Ejecuta múltiples iteraciones de GRASP + 2-Opt para minimizar cuadras."""
    if not pedidos_franja:
        return []
    if len(pedidos_franja) == 1:
        return list(pedidos_franja)

    rng = random.Random(semilla)
    mejor_ruta = None
    menor_distancia = float("inf")
    alphas = [0.0, 0.15, 0.25, 0.35]

    for it in range(iteraciones):
        alpha = 0.0 if it == 0 else alphas[it % len(alphas)]
        ruta_inicial = construir_grasp(pedidos_franja, dep_x, dep_y, alpha, rng)
        ruta_optimizada = busqueda_local_2opt(ruta_inicial, dep_x, dep_y)

        dist_actual = costo_distancia_ruta(ruta_optimizada, dep_x, dep_y)
        if dist_actual < menor_distancia:
            menor_distancia = dist_actual
            mejor_ruta = ruta_optimizada

    return mejor_ruta


def extraer_parametros(parametros_costo) -> dict:
    if isinstance(parametros_costo, (list, tuple)):
        return {
            "deposito_x": int(parametros_costo[0]),
            "deposito_y": int(parametros_costo[1]),
            "min_por_cuadra": int(parametros_costo[2]),
            "tiempo_servicio": int(parametros_costo[3]),
            "tiempo_carga": int(parametros_costo[4]),
            "costo_por_cuadra": float(parametros_costo[5]),
            "costo_por_vehiculo": float(parametros_costo[6]),
            "costo_por_minuto_total": float(parametros_costo[7]),
            "costo_por_falla": float(parametros_costo[8]),
        }
    return {
        "deposito_x": int(parametros_costo.get("deposito_x", 0)),
        "deposito_y": int(parametros_costo.get("deposito_y", 0)),
        "min_por_cuadra": int(parametros_costo.get("min_por_cuadra", 3)),
        "tiempo_servicio": int(parametros_costo.get("tiempo_servicio", 5)),
        "tiempo_carga": int(parametros_costo.get("tiempo_carga", 10)),
        "costo_por_cuadra": float(parametros_costo.get("costo_por_cuadra", 3)),
        "costo_por_vehiculo": float(parametros_costo.get("costo_por_vehiculo", 60)),
        "costo_por_minuto_total": float(parametros_costo.get("costo_por_minuto_total", 1)),
        "costo_por_falla": float(parametros_costo.get("costo_por_falla", 200)),
    }


def evaluar_costo_flota(franjas_optimizadas: list, total_pedidos: int, params: dict) -> dict:
    dep_x = params["deposito_x"]
    dep_y = params["deposito_y"]
    min_cuadra = params["min_por_cuadra"]
    t_servicio = params["tiempo_servicio"]

    distancia_total = 0
    makespan = 0
    entregados = 0
    vehiculos_usados = 0

    for ruta in franjas_optimizadas:
        if not ruta:
            continue
        vehiculos_usados += 1
        d_ruta = costo_distancia_ruta(ruta, dep_x, dep_y)
        t_ruta = (d_ruta * min_cuadra) + (len(ruta) * t_servicio)

        distancia_total += d_ruta
        entregados += len(ruta)
        if t_ruta > makespan:
            makespan = t_ruta

    fallas = max(0, total_pedidos - entregados)

    costo_dist = distancia_total * params["costo_por_cuadra"]
    costo_veh = vehiculos_usados * params["costo_por_vehiculo"]
    costo_tiempo = makespan * params["costo_por_minuto_total"]
    costo_fallas = fallas * params["costo_por_falla"]
    costo_total = costo_dist + costo_veh + costo_tiempo + costo_fallas

    array_costos = [
        costo_total,
        costo_dist,
        costo_veh,
        costo_tiempo,
        costo_fallas,
        distancia_total,
        makespan,
        vehiculos_usados,
    ]

    return {
        "array_costos": array_costos,
        "costo_total": costo_total,
        "distancia_total": distancia_total,
        "makespan": makespan,
        "vehiculos_usados": vehiculos_usados,
        "desglose": {
            "distancia": costo_dist,
            "vehiculos": costo_veh,
            "tiempo": costo_tiempo,
            "fallas": costo_fallas,
            "total": costo_total,
        },
    }


def calcular_rutas_para_k_autos(
    pedidos_ordenados: list,
    cantidad_autos: int,
    ids_vehiculos: list,
    parametros_costo,
) -> dict:
    params = extraer_parametros(parametros_costo)
    dep_x, dep_y = params["deposito_x"], params["deposito_y"]
    total_pedidos = len(pedidos_ordenados)

    candidatos_particion = [
        dividir_en_franjas_por_angulo(pedidos_ordenados, cantidad_autos),
        dividir_en_franjas_balanceadas(pedidos_ordenados, cantidad_autos),
    ]

    rango_real = pedidos_ordenados[-1]["angulo"] - pedidos_ordenados[0]["angulo"] if pedidos_ordenados else 0
    if rango_real > 120.0 and len(pedidos_ordenados) >= cantidad_autos:
        paso = max(1, len(pedidos_ordenados) // 8)
        for offset in range(paso, len(pedidos_ordenados), paso):
            rotados = pedidos_ordenados[offset:] + pedidos_ordenados[:offset]
            candidatos_particion.append(dividir_en_franjas_balanceadas(rotados, cantidad_autos))

    mejor_resultado = None
    menor_costo = float("inf")

    for franjas in candidatos_particion:
        franjas_optimizadas = [
            optimizar_ruta_grasp_2opt(franja, dep_x, dep_y)
            for franja in franjas
        ]
        evaluacion = evaluar_costo_flota(franjas_optimizadas, total_pedidos, params)

        if evaluacion["costo_total"] < menor_costo:
            menor_costo = evaluacion["costo_total"]
            rutas_formateadas = []
            for idx, ruta_opt in enumerate(franjas_optimizadas):
                vid = ids_vehiculos[idx]
                paradas_ids = [p["id"] for p in ruta_opt]
                rutas_formateadas.append({
                    "vehiculo": vid,
                    "paradas": paradas_ids,
                })
            mejor_resultado = {
                "k": cantidad_autos,
                "rutas": rutas_formateadas,
                "array_costos": evaluacion["array_costos"],
                "costo_total": evaluacion["costo_total"],
                "desglose": evaluacion["desglose"],
                "distancia_total": evaluacion["distancia_total"],
                "makespan": evaluacion["makespan"],
            }

    return mejor_resultado
