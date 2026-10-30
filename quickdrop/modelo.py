"""Entidades del dominio QuickDrop."""
from dataclasses import dataclass, field
from typing import Optional, Union

DEPOSITO = "DEPOSITO"

Parada = Union[int, str]  # id de pedido o DEPOSITO


@dataclass(frozen=True)
class Punto:
    x: int
    y: int


@dataclass
class Costos:
    por_cuadra: float = 3
    por_vehiculo: float = 60
    por_minuto_total: float = 1
    por_falla: float = 200
    por_minuto_premium: float = 1


@dataclass
class Mundo:
    ancho: int = 20
    alto: int = 20
    deposito: Punto = field(default_factory=lambda: Punto(0, 0))
    hora_salida: int = 8 * 60
    tiempo_servicio: int = 5
    tiempo_carga: int = 10
    min_por_cuadra: int = 3
    costos: Costos = field(default_factory=Costos)

    def distancia(self, a: Punto, b: Punto) -> int:
        """Único lugar donde se define cómo se mide la distancia."""
        return abs(a.x - b.x) + abs(a.y - b.y)

    def contiene(self, p: Punto) -> bool:
        return 0 <= p.x < self.ancho and 0 <= p.y < self.alto


@dataclass
class Pedido:
    id: int
    pos: Punto
    peso: int
    premium: bool = False


@dataclass
class Vehiculo:
    id: str
    min_por_cuadra: int
    costo_fijo: float


@dataclass
class Ruta:
    vehiculo: str
    paradas: list


@dataclass
class Plan:
    rutas: list
