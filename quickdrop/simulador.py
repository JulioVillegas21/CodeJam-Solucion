"""Validación y simulación de un plan de reparto."""
from dataclasses import dataclass, field
from typing import Optional

from .modelo import DEPOSITO, Mundo, Plan

ENTREGADO = "ENTREGADO"
RECARGA = "RECARGA"
REGRESO = "REGRESO"


@dataclass
class Visita:
    vehiculo: str
    viaje: int
    parada: object          # id de pedido o DEPOSITO
    x: int
    y: int
    cuadras: int            # recorridas desde la parada anterior
    llegada: int            # minutos desde 00:00
    espera: int
    inicio: Optional[int]   # inicio de la entrega (None si falló o no es entrega)
    salida: int             # cuando el vehículo queda libre
    estado: str


@dataclass
class Resultado:
    valido: bool
    errores: list = field(default_factory=list)
    visitas: list = field(default_factory=list)
    no_asignados: list = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    costo: Optional[dict] = None   # componentes + "total"


def validar_plan(mundo: Mundo, pedidos: dict, vehiculos: dict, plan: Plan) -> list:
    errores = []
    vehiculos_vistos = set()
    pedidos_vistos = {}
    for i, ruta in enumerate(plan.rutas, start=1):
        v = vehiculos.get(ruta.vehiculo)
        if v is None:
            errores.append(f"Ruta {i}: el vehículo '{ruta.vehiculo}' no existe.")
            continue
        if ruta.vehiculo in vehiculos_vistos:
            errores.append(f"El vehículo '{ruta.vehiculo}' aparece en más de una ruta.")
            continue
        vehiculos_vistos.add(ruta.vehiculo)

        carga, viaje = 0, 1
        for parada in list(ruta.paradas) + [DEPOSITO]:
            if parada == DEPOSITO:
                carga, viaje = 0, viaje + 1
                continue
            p = pedidos.get(parada)
            if p is None:
                errores.append(f"Vehículo {v.id}: el pedido {parada} no existe.")
                continue
            if parada in pedidos_vistos:
                errores.append(
                    f"El pedido {parada} aparece más de una vez "
                    f"(vehículos {pedidos_vistos[parada]} y {v.id})."
                )
                continue
            pedidos_vistos[parada] = v.id
            carga += p.peso
    return errores


def simular(mundo: Mundo, pedidos: dict, vehiculos: dict, plan: Plan) -> Resultado:
    errores = validar_plan(mundo, pedidos, vehiculos, plan)
    if errores:
        return Resultado(valido=False, errores=errores)

    dep = mundo.deposito
    visitas = []
    asignados = set()
    usados = []
    distancia_total = 0
    fin_ultimo = mundo.hora_salida
    entregados = 0

    for ruta in plan.rutas:
        v = vehiculos[ruta.vehiculo]
        if not any(p != DEPOSITO for p in ruta.paradas):
            continue  # vehículo sin pedidos: no se usa
        usados.append(v)
        t, pos, viaje = mundo.hora_salida, dep, 1

        for parada in ruta.paradas:
            if parada == DEPOSITO:
                d = mundo.distancia(pos, dep)
                t += d * v.min_por_cuadra
                llegada = t
                t += mundo.tiempo_carga
                visitas.append(Visita(v.id, viaje, DEPOSITO, dep.x, dep.y, d, llegada, 0, None, t, RECARGA))
                distancia_total += d
                pos, viaje = dep, viaje + 1
                continue

            p = pedidos[parada]
            asignados.add(p.id)
            d = mundo.distancia(pos, p.pos)
            t += d * v.min_por_cuadra
            distancia_total += d
            pos = p.pos
            llegada = t
            inicio = llegada
            t = inicio + mundo.tiempo_servicio
            entregados += 1
            visitas.append(Visita(v.id, viaje, p.id, p.pos.x, p.pos.y, d, llegada, inicio - llegada, inicio, t, ENTREGADO))

        d = mundo.distancia(pos, dep)
        t += d * v.min_por_cuadra
        distancia_total += d
        visitas.append(Visita(v.id, viaje, DEPOSITO, dep.x, dep.y, d, t, 0, None, t, REGRESO))
        fin_ultimo = max(fin_ultimo, t)

    no_asignados = [pid for pid in pedidos if pid not in asignados]
    fallidos = len(no_asignados)
    makespan = fin_ultimo - mundo.hora_salida
    c = mundo.costos
    componentes = {
        "distancia": distancia_total * c.por_cuadra,
        "vehiculos": sum(v.costo_fijo for v in usados),
        "tiempo": makespan * c.por_minuto_total,
        "fallas": fallidos * c.por_falla,
    }
    componentes["total"] = sum(componentes.values())

    metricas = {
        "pedidos": len(pedidos),
        "entregados": entregados,
        "sin_asignar": len(no_asignados),
        "fallidos": fallidos,
        "distancia_total": distancia_total,
        "vehiculos_usados": len(usados),
        "makespan": makespan,
        "hora_fin": fin_ultimo,
    }
    return Resultado(True, [], visitas, no_asignados, metricas, componentes)
