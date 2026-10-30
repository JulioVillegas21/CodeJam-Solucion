"""
Archivo 3: main.py (Solución 2 - Pedidos Premium)
Orquestador principal:
1. Lee 'Datos/mundo.json', 'Datos/pedidos.json' y 'Datos/vehiculos.json'.
2. Ejecuta geometria.py para calcular ángulos (0° a 360°), distancias y recortar zonas vacías.
3. Ejecuta ruteo_premium.py probando desde k = 1 hasta N vehículos.
4. Compara el array de costos, elige la cantidad óptima de autos y guarda 'respuestas/plan.json'.
"""
import json
import sys
from pathlib import Path

from geometria import calcular_angulos_y_distancias
from ruteo_premium import calcular_rutas_para_k_autos_premium


def resolver_premium(carpeta_datos: str = "Datos") -> dict:
    base_dir = Path(__file__).resolve().parent
    ruta_datos = Path(carpeta_datos) if Path(carpeta_datos).is_Absolute() if hasattr(Path(carpeta_datos), "is_Absolute") else (Path(carpeta_datos) if Path(carpeta_datos).is_absolute() else base_dir / carpeta_datos)

    mundo = json.loads((ruta_datos / "mundo.json").read_text(encoding="utf-8-sig"))
    lista_pedidos = json.loads((ruta_datos / "pedidos.json").read_text(encoding="utf-8-sig"))
    lista_vehiculos = json.loads((ruta_datos / "vehiculos.json").read_text(encoding="utf-8-sig"))

    dep_x = int(mundo.get("deposito_x", 0))
    dep_y = int(mundo.get("deposito_y", 0))
    ids_vehiculos = [str(v["id"]).strip() for v in lista_vehiculos]

    # Array de parámetros de costo:
    # [dep_x, dep_y, min_por_cuadra, tiempo_servicio, tiempo_carga,
    #  costo_por_cuadra, costo_por_vehiculo, costo_por_minuto_total,
    #  costo_por_falla, costo_por_minuto_premium]
    parametros_costo = [
        dep_x,
        dep_y,
        int(mundo.get("min_por_cuadra", 3)),
        int(mundo.get("tiempo_servicio", 5)),
        int(mundo.get("tiempo_carga", 10)),
        float(mundo.get("costo_por_cuadra", 3)),
        float(mundo.get("costo_por_vehiculo", 60)),
        float(mundo.get("costo_por_minuto_total", 1)),
        float(mundo.get("costo_por_falla", 200)),
        float(mundo.get("costo_por_minuto_premium", 1)),
    ]

    # Fase 1: Geometría (ángulos 0° a 360°, distancia al depósito y recorte de huecos vacíos)
    pedidos_con_angulo = calcular_angulos_y_distancias(lista_pedidos, dep_x, dep_y)
    cant_premium = sum(1 for p in pedidos_con_angulo if p["premium"])

    print("=" * 78)
    print(f"DATASET: {carpeta_datos}")
    print(
        f"Depósito: ({dep_x}, {dep_y}) | Pedidos: {len(pedidos_con_angulo)} "
        f"(Premium: {cant_premium}) | Flota disponible: {len(ids_vehiculos)}"
    )
    print("-" * 78)
    print(
        f"{'Autos (k)':^9} | {'Distancia':^11} | {'Makespan':^10} | "
        f"{'Min.Prem':^10} | {'Costo Autos':^11} | {'COSTO TOTAL':^13}"
    )
    print("-" * 78)

    # Fase 2: Evaluar k = 1 .. N vehículos y elegir el de menor costo total
    mejor_solucion = None
    menor_costo = float("inf")

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
    print(f"-> ÓPTIMO ELEGIDO: {mejor_solucion['k']} vehículo(s) | COSTO TOTAL = ${mejor_solucion['costo_total']}")

    # Guardar respuesta en 'respuestas/plan.json'
    carpeta_respuestas = base_dir / "respuestas"
    carpeta_respuestas.mkdir(parents=True, exist_ok=True)
    ruta_salida = carpeta_respuestas / "plan.json"

    plan_dict = {"rutas": mejor_solucion["rutas"]}
    ruta_salida.write_text(json.dumps(plan_dict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"-> Respuesta guardada en: {ruta_salida}")
    print("=" * 78)
    return plan_dict


if __name__ == "__main__":
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "Datos"
    resolver_premium(carpeta)
