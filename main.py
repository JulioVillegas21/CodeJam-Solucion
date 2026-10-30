"""
Archivo 3: main.py
Orquestador principal:
1. Lee mundo, pedidos y vehículos (soporta JSON y CSV).
2. Ejecuta Archivo 1 (geometria.py) para obtener el array de ángulos (0°-360°) y distancias.
3. Ejecuta Archivo 2 (ruteo.py) probando k = 1, 2, ..., N vehículos disponibles.
4. Compara el array de costos de cada k, elige el óptimo y guarda 'plan.json'.
5. Verifica el plan contra el simulador oficial de QuickDrop.

Uso:
  python main.py datos/ejemplo
  python main.py ruta/al/dataset plan_salida.json
"""
import json
import sys
from pathlib import Path

from geometria import calcular_angulos_y_distancias
from ruteo import calcular_rutas_para_k_autos
from quickdrop.cargar import cargar_datos, guardar_plan, plan_desde_dict
from quickdrop.simulador import simular


def resolver_dataset(carpeta_datos: str, archivo_salida: str = None) -> dict:
    # Asegurar que exista la carpeta 'respuestas'
    carpeta_respuestas = Path(__file__).resolve().parent / "respuestas"
    carpeta_respuestas.mkdir(parents=True, exist_ok=True)

    if archivo_salida is None:
        nombre_dataset = Path(carpeta_datos).name
        archivo_salida = str(carpeta_respuestas / f"plan_{nombre_dataset}.json")
    else:
        ruta_prov = Path(archivo_salida)
        if not ruta_prov.is_absolute() and ruta_prov.parent == Path("."):
            archivo_salida = str(carpeta_respuestas / ruta_prov.name)

    # 1. Cargar datos usando el cargador oficial (lee JSON o CSV indistintamente)
    mundo, pedidos_dict, vehiculos_dict = cargar_datos(carpeta_datos)

    dep_x = mundo.deposito.x
    dep_y = mundo.deposito.y

    lista_pedidos = [
        {"id": p.id, "x": p.pos.x, "y": p.pos.y, "peso": p.peso}
        for p in pedidos_dict.values()
    ]
    ids_vehiculos = list(vehiculos_dict.keys())

    # Armamos el array de parámetros de costo tal como definimos en el diseño:
    # [dep_x, dep_y, min_por_cuadra, tiempo_servicio, tiempo_carga,
    #  costo_por_cuadra, costo_por_vehiculo, costo_por_minuto_total, costo_por_falla]
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
    ]

    print("=" * 68)
    print(f"DATASET: {carpeta_datos}")
    print(f"Depósito en: ({dep_x}, {dep_y}) | Pedidos: {len(lista_pedidos)} | Flota disponible: {len(ids_vehiculos)} ({', '.join(ids_vehiculos)})")
    print("=" * 68)

    # 2. Fase 1 (geometria.py): Calcular ángulos (0° a 360°), distancias y recortar zonas vacías
    pedidos_con_angulo = calcular_angulos_y_distancias(lista_pedidos, dep_x, dep_y)

    if pedidos_con_angulo:
        ang_min = pedidos_con_angulo[0]["angulo"]
        ang_max = pedidos_con_angulo[-1]["angulo"]
        ang_util_max = pedidos_con_angulo[-1]["angulo_util"]
        print(f"[Fase 1 - Geometría] Rango angular real: {ang_min:.1f}° a {ang_max:.1f}° | Rango útil (sin huecos): {ang_util_max:.1f}°")
    print("-" * 68)

    # 3. Fase 2 (ruteo.py): Evaluar para cada cantidad posible de autos k = 1 .. N
    resultados_por_k = []
    mejor_solucion = None
    menor_costo = float("inf")

    print(f"{'Autos (k)':^10} | {'Distancia':^12} | {'Makespan':^12} | {'Costo Autos':^12} | {'COSTO TOTAL':^14}")
    print("-" * 68)

    for k in range(1, len(ids_vehiculos) + 1):
        solucion_k = calcular_rutas_para_k_autos(
            pedidos_con_angulo,
            k,
            ids_vehiculos,
            parametros_costo,
        )
        resultados_por_k.append(solucion_k)

        c_total = solucion_k["costo_total"]
        dist = solucion_k["distancia_total"]
        mk = solucion_k["makespan"]
        c_veh = solucion_k["desglose"]["vehiculos"]

        print(f"{k:^10} | {f'{dist} cuadras':^12} | {f'{mk} min':^12} | {f'${c_veh:.0f}':^12} | {f'${c_total:.1f}':^14}")

        if c_total < menor_costo:
            menor_costo = c_total
            mejor_solucion = solucion_k

    print("-" * 68)
    print(f"-> ÓPTIMO ELEGIDO: {mejor_solucion['k']} vehículo(s) con COSTO TOTAL = {mejor_solucion['costo_total']}")

    # 4. Guardar el plan ganador en la carpeta 'respuestas' en formato oficial JSON / CSV
    plan_dict = {"rutas": mejor_solucion["rutas"]}
    plan_obj = plan_desde_dict(plan_dict)
    ruta_salida = Path(archivo_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    guardar_plan(ruta_salida, plan_obj)

    # También actualizamos respuestas/plan.json como última respuesta generada
    ruta_plan_general = Path(__file__).resolve().parent / "respuestas" / "plan.json"
    guardar_plan(ruta_plan_general, plan_obj)

    # 5. Validar con el simulador oficial para garantizar validez 100%
    res_oficial = simular(mundo, pedidos_dict, vehiculos_dict, plan_obj)
    if res_oficial.valido:
        print(f"-> VALIDACIÓN OFICIAL: PLAN VÁLIDO (Costo oficial verificado: {res_oficial.costo['total']})")
        print(f"-> Archivo generado listo para entregar: {ruta_salida.resolve()}")
    else:
        print("-> ERROR EN VALIDACIÓN:", res_oficial.errores)

    print("=" * 68)
    return plan_dict


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "datos/ejemplo"
    salida = sys.argv[2] if len(sys.argv) > 2 else None
    resolver_dataset(carpeta, salida)
