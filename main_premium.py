"""
main_premium.py — EJECUTOR DEL ALGORITMO CON PREMIUM (EVENTO 2)
Lee los archivos de 'Datos/', ejecuta geometria.py + ruteo_premium.py (con premium)
y guarda la respuesta en 'respuestas/plan_premium.json' y 'respuestas/plan.json'.
"""
import sys
from pathlib import Path

from geometria import calcular_angulos_y_distancias
from ruteo_premium import calcular_rutas_para_k_autos_premium
from quickdrop.cargar import cargar_datos, guardar_plan, plan_desde_dict
from quickdrop.simulador import simular


def resolver_premium(carpeta_datos: str = "Datos") -> dict:
    carpeta_respuestas = Path(__file__).resolve().parent / "respuestas"
    carpeta_respuestas.mkdir(parents=True, exist_ok=True)

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
    print(f"[MODO PREMIUM - EVENTO 2] DATASET: {carpeta_datos}")
    print(
        f"Depósito: ({dep_x}, {dep_y}) | Pedidos: {len(lista_pedidos)} "
        f"(Premium: {cant_premium}) | Flota: {len(ids_vehiculos)}"
    )
    print("-" * 78)

    pedidos_con_angulo = calcular_angulos_y_distancias(lista_pedidos, dep_x, dep_y)

    mejor_solucion = None
    menor_costo = float("inf")

    print(
        f"{'Autos (k)':^9} | {'Distancia':^11} | {'Makespan':^10} | "
        f"{'Min.Prem':^10} | {'Costo Autos':^11} | {'COSTO TOTAL':^13}"
    )
    print("-" * 78)

    for k in range(1, len(ids_vehiculos) + 1):
        solucion_k = calcular_rutas_para_k_autos_premium(
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
    print(f"-> ÓPTIMO ELEGIDO: {mejor_solucion['k']} vehículo(s) | COSTO = {mejor_solucion['costo_total']}")

    plan_dict = {"rutas": mejor_solucion["rutas"]}
    plan_obj = plan_desde_dict(plan_dict)

    guardar_plan(carpeta_respuestas / "plan_premium.json", plan_obj)
    guardar_plan(carpeta_respuestas / "plan.json", plan_obj)

    res_oficial = simular(mundo, pedidos_dict, vehiculos_dict, plan_obj)
    if res_oficial.valido:
        print(f"-> Guardado en: respuestas/plan_premium.json y respuestas/plan.json")
    print("=" * 78)
    return plan_dict


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "Datos"
    resolver_premium(carpeta)
