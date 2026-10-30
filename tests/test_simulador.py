"""Tests del simulador. Correr con: python -m unittest -v"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quickdrop.cargar import (
    ErrorDatos, ErrorPlan, cargar_datos, cargar_plan, guardar_plan, mundo_desde_dict,
    pedidos_desde_filas, plan_desde_dict, vehiculos_desde_filas,
)
from quickdrop.horas import a_hora, a_minutos
from quickdrop.modelo import DEPOSITO, Punto
from quickdrop.simulador import ENTREGADO, simular

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "datos" / "ejemplo"


def escenario(pedidos, vehiculos, mundo=None):
    m = mundo_desde_dict(mundo or {})
    return m, pedidos_desde_filas(pedidos, m), vehiculos_desde_filas(vehiculos, m)


def correr(pedidos, vehiculos, rutas, mundo=None):
    m, p, v = escenario(pedidos, vehiculos, mundo)
    return simular(m, p, v, plan_desde_dict({"rutas": rutas}))


DOS_PEDIDOS = [{"id": 1, "x": 2, "y": 3, "peso": 10}, {"id": 2, "x": 5, "y": 3, "peso": 5}]
UN_VEHICULO = [{"id": "A"}]


class TestHoras(unittest.TestCase):
    def test_ida_y_vuelta(self):
        self.assertEqual(a_minutos("08:00"), 480)
        self.assertEqual(a_minutos("10:30"), 630)
        self.assertEqual(a_hora(630), "10:30")
        self.assertEqual(a_hora(a_minutos("23:59")), "23:59")

    def test_invalidas(self):
        for h in ("8", "25:00", "10:60", "aa:bb", "10:30:00"):
            with self.assertRaises(ValueError):
                a_minutos(h)


class TestMundo(unittest.TestCase):
    def test_distancia_manhattan(self):
        m = mundo_desde_dict({})
        self.assertEqual(m.distancia(Punto(0, 0), Punto(3, 4)), 7)
        self.assertEqual(m.distancia(Punto(5, 1), Punto(2, 9)), 11)

    def test_defectos(self):
        m = mundo_desde_dict({})
        self.assertEqual((m.ancho, m.alto, m.hora_salida, m.min_por_cuadra), (20, 20, 480, 3))


class TestCalculoBasico(unittest.TestCase):
    def test_costo_calculado_a_mano(self):
        # 0,0 -> (2,3): 5 cuadras; -> (5,3): 3; -> 0,0: 8. Total 16.
        # Tiempos: llega 08:15, sale 08:20; llega 08:29, sale 08:34; vuelve 08:58.
        r = correr(DOS_PEDIDOS, UN_VEHICULO, [{"vehiculo": "A", "paradas": [1, 2]}])
        self.assertTrue(r.valido)
        self.assertEqual(r.metricas["distancia_total"], 16)
        self.assertEqual(r.metricas["makespan"], 58)
        self.assertEqual(r.visitas[0].llegada, a_minutos("08:15"))
        self.assertEqual(r.visitas[1].llegada, a_minutos("08:29"))
        esperado = {"distancia": 48, "vehiculos": 60, "tiempo": 58, "fallas": 0, "total": 166}
        self.assertEqual(r.costo, esperado)

    def test_dos_vehiculos_suman_distancia_y_costo_fijo(self):
        r = correr(DOS_PEDIDOS, [{"id": "A"}, {"id": "B"}],
                   [{"vehiculo": "A", "paradas": [1]}, {"vehiculo": "B", "paradas": [2]}])
        self.assertEqual(r.metricas["distancia_total"], 10 + 16)
        self.assertEqual(r.metricas["vehiculos_usados"], 2)
        self.assertEqual(r.costo["vehiculos"], 120)
        # B: 8 cuadras ida (24 min) + 5 servicio + 24 vuelta = 53
        self.assertEqual(r.metricas["makespan"], 53)

    def test_vehiculo_sin_pedidos_no_cuenta(self):
        r = correr(DOS_PEDIDOS, [{"id": "A"}, {"id": "B"}],
                   [{"vehiculo": "A", "paradas": [1, 2]}, {"vehiculo": "B", "paradas": []}])
        self.assertEqual(r.metricas["vehiculos_usados"], 1)

    def test_pedido_sin_asignar_es_falla(self):
        r = correr(DOS_PEDIDOS, UN_VEHICULO, [{"vehiculo": "A", "paradas": [1]}])
        self.assertTrue(r.valido)
        self.assertEqual(r.no_asignados, [2])
        self.assertEqual(r.costo["fallas"], 200)








class TestValidez(unittest.TestCase):
    def test_pedido_repetido(self):
        r = correr(DOS_PEDIDOS, [{"id": "A"}, {"id": "B"}],
                   [{"vehiculo": "A", "paradas": [1, 2]}, {"vehiculo": "B", "paradas": [2]}])
        self.assertFalse(r.valido)

    def test_pedido_inexistente(self):
        self.assertFalse(correr(DOS_PEDIDOS, UN_VEHICULO, [{"vehiculo": "A", "paradas": [1, 2, 99]}]).valido)

    def test_vehiculo_inexistente(self):
        self.assertFalse(correr(DOS_PEDIDOS, UN_VEHICULO, [{"vehiculo": "Z", "paradas": [1, 2]}]).valido)

    def test_vehiculo_repetido(self):
        r = correr(DOS_PEDIDOS, UN_VEHICULO,
                   [{"vehiculo": "A", "paradas": [1]}, {"vehiculo": "A", "paradas": [2]}])
        self.assertFalse(r.valido)

    def test_plan_mal_formado(self):
        with self.assertRaises(ErrorPlan):
            plan_desde_dict({"rutas": [{"vehiculo": "A", "paradas": ["casa"]}]})
        with self.assertRaises(ErrorPlan):
            plan_desde_dict([1, 2, 3])

    def test_datos_invalidos(self):
        casos = [
            [{"id": 1, "x": 20, "y": 0, "peso": 1}],                         # fuera de la grilla
            [{"id": 1, "x": 1, "y": 1, "peso": 1}, {"id": 1, "x": 2, "y": 2, "peso": 1}],  # id repetido
            [{"id": 1, "x": 1, "y": 1}],                                      # falta peso
        ]
        for pedidos in casos:
            with self.subTest(pedidos=pedidos), self.assertRaises(ErrorDatos):
                escenario(pedidos, UN_VEHICULO)


class TestFormatos(unittest.TestCase):
    def test_csv_y_json_del_ejemplo_son_iguales(self):
        self.assertEqual(cargar_datos(EJEMPLO, "json"), cargar_datos(EJEMPLO, "csv"))

    def test_plan_csv_y_json_dan_el_mismo_resultado(self):
        m, p, v = cargar_datos(EJEMPLO)
        plan = cargar_plan(EJEMPLO / "plan_ejemplo.json")
        with tempfile.TemporaryDirectory() as tmp:
            ruta_csv = Path(tmp) / "plan.csv"
            guardar_plan(ruta_csv, plan)
            plan_csv = cargar_plan(ruta_csv)
        self.assertEqual(plan, plan_csv)
        self.assertEqual(simular(m, p, v, plan).costo, simular(m, p, v, plan_csv).costo)

    def test_csv_con_punto_y_coma_y_campos_vacios(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pedidos.csv").write_text("id;x;y;peso;notas\n1;2;3;10;\n2;5;3;5;algo\n")
            (d / "vehiculos.csv").write_text("id;notas\nA;\n")
            m, p, v = cargar_datos(d)
        self.assertEqual((p[1].peso, p[2].peso), (10, 5))
        self.assertEqual(v["A"].min_por_cuadra, 3)



# Costo del plan de ejemplo con los campos de cada etapa develada.
TOTAL_EJEMPLO = 1013


class TestEjemplo(unittest.TestCase):
    def test_resultado_del_plan_de_ejemplo(self):
        m, p, v = cargar_datos(EJEMPLO)
        r = simular(m, p, v, cargar_plan(EJEMPLO / "plan_ejemplo.json"))
        self.assertTrue(r.valido)
        self.assertEqual(r.costo["total"], TOTAL_EJEMPLO)

    def test_cli_json(self):
        salida = subprocess.run(
            [sys.executable, "-m", "quickdrop", "simular", str(EJEMPLO), str(EJEMPLO / "plan_ejemplo.json"), "--json"],
            cwd=RAIZ, capture_output=True, text=True,
        )
        self.assertEqual(salida.returncode, 0, salida.stderr)
        self.assertEqual(json.loads(salida.stdout)["costo"]["total"], TOTAL_EJEMPLO)


if __name__ == "__main__":
    unittest.main()
