"""Presentación del resultado: texto para humanos y JSON para máquinas."""
from .horas import a_hora
from .modelo import Mundo
from .simulador import Resultado


def _n(x):
    if isinstance(x, float):
        return f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)


def como_texto(r: Resultado, mundo: Mundo, detalle: bool = False) -> str:
    if not r.valido:
        lineas = ["PLAN INVÁLIDO — no recibe puntaje en este dataset.", ""]
        lineas += [f"  ✗ {e}" for e in r.errores]
        return "\n".join(lineas)

    m, c, k = r.metricas, r.costo, mundo.costos
    lineas = [
        "Plan válido",
        "",
        f"COSTO TOTAL: {_n(c['total'])}",
        f"  distancia  {m['distancia_total']} cuadras × {_n(k.por_cuadra)} = {_n(c['distancia'])}",
        f"  vehículos  {m['vehiculos_usados']} usados (costo fijo) = {_n(c['vehiculos'])}",
        f"  tiempo     {m['makespan']} min × {_n(k.por_minuto_total)} = {_n(c['tiempo'])}",
        f"  fallas     {m['fallidos']} × {_n(k.por_falla)} = {_n(c['fallas'])}",
    ]
    lineas.append(f"  premium    {m['minutos_premium']} min × {_n(k.por_minuto_premium)} = {_n(c['premium'])}")
    entregas = f"Entregas: {m['entregados']}/{m['pedidos']} entregados"
    lineas += ["", f"{entregas} · {m['sin_asignar']} sin asignar"]
    if m["premium_total"]:
        lineas.append(f"Premium: {m['premium_entregados']}/{m['premium_total']} entregados")
    lineas.append(f"Vuelve el último vehículo: {a_hora(m['hora_fin'])}")
    if r.no_asignados:
        lineas.append(f"Sin asignar: {', '.join(map(str, r.no_asignados))}")

    if detalle:
        lineas += ["", "DETALLE"]
        actual = None
        for v in r.visitas:
            if v.vehiculo != actual:
                actual = v.vehiculo
                lineas += ["", f"Vehículo {actual}",
                           "  viaje  parada     (x,y)    cuadras  llegada  espera  entrega  estado"]
            entrega = a_hora(v.inicio) if v.inicio is not None else "  -  "
            lineas.append(
                f"  {v.viaje:>5}  {str(v.parada):<9}  ({v.x:>2},{v.y:>2})  {v.cuadras:>7}  "
                f"{a_hora(v.llegada):>7}  {v.espera:>6}  {entrega:>7}  {v.estado}"
            )
    return "\n".join(lineas)


def como_dict(r: Resultado) -> dict:
    if not r.valido:
        return {"valido": False, "errores": r.errores}
    m = dict(r.metricas)
    m["hora_fin"] = a_hora(m["hora_fin"])
    return {
        "valido": True,
        "costo": r.costo,
        "metricas": m,
        "no_asignados": r.no_asignados,
        "visitas": [
            {
                "vehiculo": v.vehiculo, "viaje": v.viaje, "parada": v.parada, "x": v.x, "y": v.y,
                "cuadras": v.cuadras, "llegada": a_hora(v.llegada), "espera": v.espera,
                "entrega": a_hora(v.inicio) if v.inicio is not None else None,
                "salida": a_hora(v.salida), "estado": v.estado,
            }
            for v in r.visitas
        ],
    }
