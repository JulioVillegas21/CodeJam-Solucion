"""
Archivo 3: main.py (Rama solucion-2-premium)
Orquestador principal para el Evento 2 (Pedidos Premium):
1. Lee mundo (incluyendo costo_por_minuto_premium), pedidos (incluyendo campo premium) y vehículos.
2. Ejecuta Archivo 1 (geometria.py) para obtener el array de ángulos (0°-360°), distancias y estado premium.
3. Ejecuta Archivo 2 (ruteo.py) probando k = 1, 2, ..., N vehículos disponibles con GRASP + 2-Opt + Or-Opt sensible a latencia.
4. Compara el array de costos de cada k, elige el óptimo y guarda la respuesta en la carpeta 'respuestas/'.
"""
import sys
from pathlib import Path

from geometria import calcular_angulos_y_distancias
from ruteo import calcular_rutas_para_k_autos
from quickdrop.cargar import cargar_datos, guardar_plan, plan_desde_dict
from quickdrop.simulador import simular


def resolver_dataset(carpeta_datos: str, archivo_salida: str = None) -> dict:
    carpeta_respuestas = Path(__file__).resolve().parent / "respuestas"
    carpeta_respuestas.mkdir(parents=True, exist_ok=True)

    if archivo_salida is None:
        nombre_dataset = Path(carpeta_datos).name
        archivo_salida = str(carpeta_respuestas / f"plan_{nombre_dataset}.json")
    else:
        ruta_prov = Path(archivo_salida)
        if not ruta_prov.is_absolute() and ruta_prov.parent == Path("."):
            archivo_salida = str(carpeta_respuestas / ruta_prov.name)

    # 1. Cargar datos usando el cargador oficial (JSON o CSV)
    mundo, pedidos_dict, vehiculos_dict = cargar_datos(carpeta_datos)

    dep_x = mundo.deposito.x
    dep_y = mundo.deposito.y

    lista_pedidos = [
        {
            "id": p.id,
            "x": p.pos.x,
            "y": p.pos.y,
            "peso": p.peso,
            "premium": getattr(p, "premium", False),
        }
        for p in pedidos_dict.values()
    ]
    ids_vehiculos = list(vehiculos_dict.keys())
    cant_premium = sum(1 for p in lista_pedidos if p["premium"])

    # Array de parámetros de costo (incluyendo el 10° parámetro: costo_por_minuto_premium):
    # [dep_x, dep_y, min_por_cuadra, tiempo_servicio, tiempo_carga,
    #  costo_por_cuadra, costo_por_vehiculo, costo_por_minuto_total,
    #  costo_por_falla, costo_por_minuto_premium]
    costo_min_premium = getattr(mundo.costos, "por_minuto_premium", 1)
    parametros_costo = [
        dep_x,
        dep_y,
        mundo.min_por_cuadra,
        mundo.tiempo_servicio,
        mundo.tiempo_carga,
        mundo.costos.por_cuadra,
        mundo.costos.por_vehiculo,
        mundo.costos.por_minuto_total,
        mundo.costos.por_falla,
        costo_min_premium,
    ]

    print("=" * 78)
    print(f"DATASET: {carpeta_datos}")
    print(
        f"Depósito: ({dep_x}, {dep_y}) | Pedidos: {len(lista_pedidos)} "
        f"(Premium: {cant_premium}) | Flota: {len(ids_vehiculos)}"
    )
    print("=" * 78)

    # 2. Fase 1 (geometria.py)
    pedidos_con_angulo = calcular_angulos_y_distancias(lista_pedidos, dep_x, dep_y)

    if pedidos_con_angulo:
        ang_min = pedidos_con_angulo[0]["angulo"]
        ang_max = pedidos_con_angulo[-1]["angulo"]
        ang_util_max = pedidos_con_angulo[-1]["angulo_util"]
        print(
            f"[Fase 1 - Geometría] Rango real: {ang_min:.1f}° a {ang_max:.1f}° | "
            f"Rango útil (sin huecos): {ang_util_max:.1f}°"
        )
    print("-" * 78)

    # 3. Fase 2 (ruteo.py): Evaluar para k = 1 .. N
    mejor_solucion = None
    menor_costo = float("inf")

    print(
        f"{'Autos (k)':^9} | {'Distancia':^11} | {'Makespan':^10} | "
        f"{'Min.Prem':^10} | {'Costo Autos':^11} | {'COSTO TOTAL':^13}"
    )
    print("-" * 78)

    for k in range(1, len(ids_vehiculos) + 1):
        solucion_k = calcular_rutas_para_k_autos(
            pedidos_con_angulo,
            k,
            ids_vehiculos,
            parametros_costo,
        )

        c_total = solucion_k["costo_total"]
        dist = solucion_k["distancia_total"]
        mk = solucion_k["makespan"]
        m_prem = solucion_k["minutos_premium"]
        c_veh = solucion_k["desglose"]["vehiculos"]

        print(
            f"{k:^9} | {f'{dist} cuad':^11} | {f'{mk} min':^10} | "
            f"{f'{m_prem} min':^10} | {f'${c_veh:.0f}':^11} | {f'${c_total:.1f}':^13}"
        )

        if c_total < menor_costo:
            menor_costo = c_total
            mejor_solucion = solucion_k

    print("-" * 78)
    print(
        f"-> ÓPTIMO ELEGIDO: {mejor_solucion['k']} vehículo(s) con "
        f"COSTO TOTAL = {mejor_solucion['costo_total']}"
    )

    # 4. Guardar el plan ganador en la carpeta 'respuestas'
    plan_dict = {"rutas": mejor_solucion["rutas"]}
    plan_obj = plan_desde_dict(plan_dict)
    ruta_salida = Path(archivo_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    guardar_plan(ruta_salida, plan_obj)

    ruta_plan_general = Path(__file__).resolve().parent / "respuestas" / "plan.json"
    guardar_plan(ruta_plan_general, plan_obj)

    # 5. Validar con el simulador oficial
    res_oficial = simular(mundo, pedidos_dict, vehiculos_dict, plan_obj)
    if res_oficial.valido:
        print(f"-> VALIDACIÓN OFICIAL: PLAN VÁLIDO (Costo oficial verificado: {res_oficial.costo['total']})")
        print(f"-> Archivo generado en carpeta respuestas: {ruta_salida.resolve()}")
    else:
        print("-> ERROR EN VALIDACIÓN:", res_oficial.errores)

    print("=" * 78)
    return plan_dict


if __name__ == "__main__":
    if len(sys.argv) > 1:
        carpeta = sys.argv[1]
    elif (Path(__file__).resolve().parent / "Datos" / "mundo.json").exists():
        carpeta = "Datos"
    else:
        carpeta = "datos/ejemplo"
    salida = sys.argv[2] if len(sys.argv) > 2 else None
    resolver_dataset(carpeta, salida)
