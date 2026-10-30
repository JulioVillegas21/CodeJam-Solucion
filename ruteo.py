"""
Archivo 2: ruteo.py (Rama solucion-2-premium)
Módulo que resuelve el Evento 2 (Pedidos Premium con penalización por minuto de espera):
1. División en franjas por ángulo útil, balanceada y modalidad con vehículo dedicado a Premium.
2. Metaheurística GRASP + 2-Opt Sensible a Latencia (Minimum Latency VRP) +
   Operador Or-Opt (Relocate) que adelanta pedidos Premium en la ruta cuando
   el ahorro en minutos supera el costo de cuadras adicionales.
3. Cálculo exacto del array de costos incluyendo 'costo_por_minuto_premium'.
"""
import random
from geometria import distancia_manhattan


# ---------------------------------------------------------------------------
# 1. ESTRATEGIAS DE PARTICIÓN EN FRANJAS (INCLUYENDO REPARTO DE PREMIUMS)
# ---------------------------------------------------------------------------

def dividir_en_franjas_por_angulo(pedidos_ordenados: list, cantidad_autos: int) -> list:
    """Divide según 'angulo_util' (con zonas vacías ya descartadas)."""
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
    """Divide los pedidos ordenados por ángulo en 'cantidad_autos' franjas parejas."""
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


def dividir_con_vehiculo_express_premium(pedidos_ordenados: list, cantidad_autos: int) -> list:
    """
    Estrategia alternativa para cuando hay al menos 2 vehículos y pedidos premium:
    Dedica 1 vehículo rápido exclusivamente a los pedidos premium (o a los más urgentes)
    y reparte el resto de los pedidos normales por franjas angulares en los otros k-1 autos.
    """
    if cantidad_autos < 2:
        return [list(pedidos_ordenados)]
    premiums = [p for p in pedidos_ordenados if p.get("premium", False)]
    normales = [p for p in pedidos_ordenados if not p.get("premium", False)]
    if not premiums or not normales:
        return dividir_en_franjas_balanceadas(pedidos_ordenados, cantidad_autos)

    franjas_normales = dividir_en_franjas_balanceadas(normales, cantidad_autos - 1)
    return [premiums] + franjas_normales


def dividir_equilibrando_premiums(pedidos_ordenados: list, cantidad_autos: int) -> list:
    """
    Corta la lista ordenada por ángulo de modo que cada vehículo reciba una cantidad
    equilibrada de pedidos PREMIUM sin cruzar sectores geográficos. Así todos los
    vehículos salen a las 08:00 atendiendo pedidos premium en paralelo.
    """
    if not pedidos_ordenados or cantidad_autos <= 1:
        return [list(pedidos_ordenados)] if pedidos_ordenados else []

    indices_premium = [i for i, p in enumerate(pedidos_ordenados) if p.get("premium", False)]
    if len(indices_premium) < cantidad_autos:
        return dividir_en_franjas_balanceadas(pedidos_ordenados, cantidad_autos)

    franjas = []
    inicio = 0
    total_prem = len(indices_premium)
    for v in range(1, cantidad_autos):
        # Punto de corte entre el último premium del auto v y el primer premium del auto v+1
        idx_prem_corte = (v * total_prem) // cantidad_autos
        pos_corte = (indices_premium[idx_prem_corte - 1] + indices_premium[idx_prem_corte]) // 2 + 1
        if pos_corte > inicio:
            franjas.append(pedidos_ordenados[inicio:pos_corte])
            inicio = pos_corte
    if inicio < len(pedidos_ordenados):
        franjas.append(pedidos_ordenados[inicio:])
    return [f for f in franjas if f]


# ---------------------------------------------------------------------------
# 2. FUNCIÓN DE COSTO DE RUTA SENSIBLE A LATENCIA PREMIUM
# ---------------------------------------------------------------------------

def evaluar_metricas_ruta(paradas: list, params: dict) -> tuple:
    """
    Simula una ruta de un vehículo minuto a minuto desde el depósito.
    Retorna:
      (distancia_cuadras, duracion_total_min, minutos_premium, costo_compuesto_ruta)
    donde costo_compuesto_ruta = distancia * costo_cuadra + minutos_premium * costo_premium.
    """
    if not paradas:
        return 0, 0, 0, 0.0

    dep_x = params["deposito_x"]
    dep_y = params["deposito_y"]
    min_cuadra = params["min_por_cuadra"]
    t_servicio = params["tiempo_servicio"]
    c_cuadra = params["costo_por_cuadra"]
    c_premium = params["costo_por_minuto_premium"]

    pos_x, pos_y = dep_x, dep_y
    tiempo_transcurrido = 0
    distancia_total = 0
    minutos_premium = 0

    for p in paradas:
        d = distancia_manhattan(pos_x, pos_y, p["x"], p["y"])
        tiempo_transcurrido += d * min_cuadra
        distancia_total += d
        pos_x, pos_y = p["x"], p["y"]

        # En el instante en que llega, inicia la entrega (cuenta para premium)
        if p.get("premium", False):
            minutos_premium += tiempo_transcurrido

        tiempo_transcurrido += t_servicio

    # Regreso final al depósito
    d_regreso = distancia_manhattan(pos_x, pos_y, dep_x, dep_y)
    tiempo_transcurrido += d_regreso * min_cuadra
    distancia_total += d_regreso

    costo_compuesto = (distancia_total * c_cuadra) + (minutos_premium * c_premium)
    return distancia_total, tiempo_transcurrido, minutos_premium, costo_compuesto


# ---------------------------------------------------------------------------
# 3. TESIS UBA ADAPTADA A PREMIUM: GRASP PONDERADO + 2-OPT + OR-OPT (RELOCATE)
# ---------------------------------------------------------------------------

def construir_grasp_premium(
    pedidos_franja: list,
    params: dict,
    alpha: float,
    peso_prioridad_premium: float,
    rng: random.Random,
) -> list:
    """
    Fase constructiva GRASP con prioridad para pedidos Premium:
    - 'peso_prioridad_premium' (entre 0.0 y 1.0) reduce la distancia aparente
      de los pedidos premium para que el vehículo los visite al principio del recorrido.
      Si peso_prioridad_premium == 0.0, visita estrictamente TODOS los premium primero.
    """
    dep_x, dep_y = params["deposito_x"], params["deposito_y"]
    pendientes = list(pedidos_franja)
    ruta = []
    actual_x, actual_y = dep_x, dep_y

    while pendientes:
        # Si modo estricto (peso == 0.0) y quedan premiums en la franja, filtramos solo premiums
        hay_premiums = any(p.get("premium", False) for p in pendientes)
        if peso_prioridad_premium == 0.0 and hay_premiums:
            candidatos_base = [p for p in pendientes if p.get("premium", False)]
        else:
            candidatos_base = pendientes

        puntajes = []
        for p in candidatos_base:
            d_real = distancia_manhattan(actual_x, actual_y, p["x"], p["y"])
            factor = peso_prioridad_premium if p.get("premium", False) else 1.0
            d_ponderada = d_real * factor
            puntajes.append((d_ponderada, p))

        d_min = min(val for val, _ in puntajes)
        d_max = max(val for val, _ in puntajes)
        umbral = d_min + alpha * (d_max - d_min)

        rcl = [p for val, p in puntajes if val <= umbral + 1e-9]
        elegido = rng.choice(rcl)

        ruta.append(elegido)
        pendientes.remove(elegido)
        actual_x, actual_y = elegido["x"], elegido["y"]

    return ruta


def busqueda_local_2opt_y_relocate(ruta: list, params: dict) -> list:
    """
    Búsqueda local híbrida que minimiza directamente:
      (distancia * costo_por_cuadra) + (minutos_premium * costo_por_minuto_premium)
    Combina:
      1. Inversión de ruta completa (un giro en sentido inverso mantiene igual
         la distancia pero pone los últimos nodos al principio).
      2. Operador 2-Opt (desenreda cruces cuidando no atrasar los premium).
      3. Operador Or-Opt / Relocate (prueba adelantar un pedido a cualquier posición
         anterior si el ahorro en espera premium supera las cuadras extra).
    """
    n = len(ruta)
    if n <= 1:
        return list(ruta)

    mejor = list(ruta)
    _, _, _, mejor_costo = evaluar_metricas_ruta(mejor, params)

    # 1. Probar la ruta invertida completa
    invertida = mejor[::-1]
    _, _, _, costo_inv = evaluar_metricas_ruta(invertida, params)
    if costo_inv < mejor_costo:
        mejor = invertida
        mejor_costo = costo_inv

    mejoro = True
    while mejoro:
        mejoro = False

        # 2. Movimiento 2-Opt guiado por costo compuesto (distancia + premium)
        for i in range(n - 1):
            for j in range(i + 1, n):
                candidata = mejor[:i] + mejor[i:j + 1][::-1] + mejor[j + 1:]
                _, _, _, nuevo_costo = evaluar_metricas_ruta(candidata, params)
                if nuevo_costo < mejor_costo - 1e-6:
                    mejor = candidata
                    mejor_costo = nuevo_costo
                    mejoro = True

        # 3. Movimiento Or-Opt / Relocate (reubicar un pedido en otra posición)
        for i in range(n):
            nodo = mejor[i]
            resto = mejor[:i] + mejor[i + 1:]
            for j in range(n):
                if i == j:
                    continue
                candidata = resto[:j] + [nodo] + resto[j:]
                _, _, _, nuevo_costo = evaluar_metricas_ruta(candidata, params)
                if nuevo_costo < mejor_costo - 1e-6:
                    mejor = candidata
                    mejor_costo = nuevo_costo
                    mejoro = True
                    break
            if mejoro:
                break

    return mejor


def optimizar_ruta_grasp_2opt(
    pedidos_franja: list,
    params: dict,
    iteraciones: int = 32,
    semilla: int = 42,
) -> list:
    """
    Ejecuta GRASP + 2-Opt + Relocate probando distintos pesos de prioridad para
    pedidos premium (estricto al inicio, ponderado fuerte, ponderado suave y libre)
    y retorna la secuencia de menor costo total.
    """
    if not pedidos_franja:
        return []
    if len(pedidos_franja) == 1:
        return list(pedidos_franja)

    rng = random.Random(semilla)
    mejor_ruta = None
    menor_costo = float("inf")

    alphas = [0.0, 0.15, 0.25, 0.35]
    # 0.0 = Premiums estrictamente primero; 0.35 = alta prioridad; 0.6 = prioridad media; 1.0 = distancia pura
    pesos_premium = [0.0, 0.35, 0.6, 1.0]

    for it in range(iteraciones):
        alpha = 0.0 if it < 4 else alphas[it % len(alphas)]
        peso_prem = pesos_premium[it % len(pesos_premium)]

        ruta_inicial = construir_grasp_premium(pedidos_franja, params, alpha, peso_prem, rng)
        ruta_optimizada = busqueda_local_2opt_y_relocate(ruta_inicial, params)

        _, _, _, costo_actual = evaluar_metricas_ruta(ruta_optimizada, params)
        if costo_actual < menor_costo:
            menor_costo = costo_actual
            mejor_ruta = ruta_optimizada

    return mejor_ruta


# ---------------------------------------------------------------------------
# 4. EVALUACIÓN DE COSTOS GLOBALES DE LA FLOTA PARA K AUTOS
# ---------------------------------------------------------------------------

def extraer_parametros(parametros_costo) -> dict:
    """
    Permite pasar los parámetros como un array/lista:
      [dep_x, dep_y, min_por_cuadra, tiempo_servicio, tiempo_carga,
       costo_por_cuadra, costo_por_vehiculo, costo_por_minuto_total,
       costo_por_falla, costo_por_minuto_premium]
    o directamente como diccionario.
    """
    if isinstance(parametros_costo, (list, tuple)):
        c_prem = float(parametros_costo[9]) if len(parametros_costo) > 9 else 1.0
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
            "costo_por_minuto_premium": c_prem,
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
        "costo_por_minuto_premium": float(parametros_costo.get("costo_por_minuto_premium", 1)),
    }


def evaluar_costo_flota(franjas_optimizadas: list, total_pedidos: int, params: dict) -> dict:
    """
    Calcula el costo total exacto de la flota incluyendo el nuevo componente 'premium':
      costo = distancia + vehiculos + tiempo (makespan) + fallas + premium
    """
    distancia_total = 0
    makespan = 0
    minutos_premium_total = 0
    entregados = 0
    vehiculos_usados = 0

    for ruta in franjas_optimizadas:
        if not ruta:
            continue
        vehiculos_usados += 1
        d_ruta, t_ruta, min_prem, _ = evaluar_metricas_ruta(ruta, params)

        distancia_total += d_ruta
        minutos_premium_total += min_prem
        entregados += len(ruta)
        if t_ruta > makespan:
            makespan = t_ruta

    fallas = max(0, total_pedidos - entregados)

    costo_dist = distancia_total * params["costo_por_cuadra"]
    costo_veh = vehiculos_usados * params["costo_por_vehiculo"]
    costo_tiempo = makespan * params["costo_por_minuto_total"]
    costo_fallas = fallas * params["costo_por_falla"]
    costo_premium = minutos_premium_total * params["costo_por_minuto_premium"]
    costo_total = costo_dist + costo_veh + costo_tiempo + costo_fallas + costo_premium

    # Array de costos:
    # [costo_total, costo_dist, costo_veh, costo_tiempo, costo_premium, costo_fallas, distancia_total, makespan, minutos_premium_total, vehiculos_usados]
    array_costos = [
        costo_total,
        costo_dist,
        costo_veh,
        costo_tiempo,
        costo_premium,
        costo_fallas,
        distancia_total,
        makespan,
        minutos_premium_total,
        vehiculos_usados,
    ]

    return {
        "array_costos": array_costos,
        "costo_total": costo_total,
        "distancia_total": distancia_total,
        "makespan": makespan,
        "minutos_premium": minutos_premium_total,
        "vehiculos_usados": vehiculos_usados,
        "desglose": {
            "distancia": costo_dist,
            "vehiculos": costo_veh,
            "tiempo": costo_tiempo,
            "premium": costo_premium,
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
    """
    Evalúa para 'cantidad_autos' las estrategias de partición:
      1. Por ángulo útil (con recorte de huecos).
      2. Balanceada por sectores angulares.
      3. Con un vehículo dedicado a los pedidos Premium y el resto por sectores.
    Optimiza cada ruta con GRASP + 2-Opt + Or-Opt sensible a latencia Premium
    y devuelve la configuración de menor costo total.
    """
    params = extraer_parametros(parametros_costo)
    total_pedidos = len(pedidos_ordenados)

    candidatos_particion = [
        dividir_en_franjas_por_angulo(pedidos_ordenados, cantidad_autos),
        dividir_en_franjas_balanceadas(pedidos_ordenados, cantidad_autos),
    ]

    if any(p.get("premium", False) for p in pedidos_ordenados) and cantidad_autos >= 2:
        candidatos_particion.append(
            dividir_con_vehiculo_express_premium(pedidos_ordenados, cantidad_autos)
        )
        candidatos_particion.append(
            dividir_equilibrando_premiums(pedidos_ordenados, cantidad_autos)
        )

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
            optimizar_ruta_grasp_2opt(franja, params)
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
                "minutos_premium": evaluacion["minutos_premium"],
            }

    return mejor_resultado
