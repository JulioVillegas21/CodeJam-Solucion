"""Línea de comandos del simulador QuickDrop.

  python -m quickdrop simular  <carpeta_datos> <plan.json|plan.csv> [--detalle] [--json] [--formato csv|json]
  python -m quickdrop convertir <carpeta_datos> [--desde csv|json]
"""
import argparse
import json
import sys

from .cargar import ErrorDatos, ErrorPlan, cargar_datos, cargar_plan, guardar_datos
from .reporte import como_dict, como_texto
from .simulador import simular

try:  # comandos de organizadores; no están en el repo de participantes (decisión 0013)
    from . import cli_org
except ImportError:
    cli_org = None

SALIDA_OK, SALIDA_DATOS, SALIDA_INVALIDO = 0, 1, 2


def _cmd_simular(a) -> int:
    try:
        mundo, pedidos, vehiculos = cargar_datos(a.datos, a.formato)
    except ErrorDatos as e:
        print(f"Error en los datos: {e}", file=sys.stderr)
        return SALIDA_DATOS
    try:
        plan = cargar_plan(a.plan)
    except ErrorPlan as e:
        print(f"PLAN INVÁLIDO — no se pudo leer: {e}", file=sys.stderr)
        return SALIDA_INVALIDO
    r = simular(mundo, pedidos, vehiculos, plan)
    if a.json:
        print(json.dumps(como_dict(r), ensure_ascii=False, indent=2))
    else:
        print(como_texto(r, mundo, a.detalle))
    return SALIDA_OK if r.valido else SALIDA_INVALIDO


def _cmd_convertir(a) -> int:
    try:
        mundo, pedidos, vehiculos = cargar_datos(a.datos, a.desde)
    except ErrorDatos as e:
        print(f"Error en los datos: {e}", file=sys.stderr)
        return SALIDA_DATOS
    guardar_datos(a.datos, mundo, pedidos, vehiculos)
    print(f"Escritos mundo/pedidos/vehiculos en JSON y CSV en {a.datos}")
    return SALIDA_OK


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="quickdrop", description="Simulador oficial QuickDrop")
    sub = ap.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("simular", help="evalúa un plan sobre un dataset")
    s.add_argument("datos", help="carpeta con mundo, pedidos y vehiculos")
    s.add_argument("plan", help="archivo de plan (.json o .csv)")
    s.add_argument("--formato", choices=["json", "csv"], help="formato de los datos a leer (por defecto JSON si existe)")
    s.add_argument("--detalle", action="store_true", help="muestra cada parada con sus horarios")
    s.add_argument("--json", action="store_true", help="salida en JSON")
    s.set_defaults(func=_cmd_simular)

    c = sub.add_parser("convertir", help="genera las versiones JSON y CSV de un dataset")
    c.add_argument("datos", help="carpeta con mundo, pedidos y vehiculos")
    c.add_argument("--desde", choices=["json", "csv"], help="formato de origen (por defecto JSON si existe)")
    c.set_defaults(func=_cmd_convertir)

    if cli_org is not None:
        cli_org.registrar(sub)

    a = ap.parse_args(argv)
    return a.func(a)
