"""Lectura y escritura de datos en CSV y JSON (mismos campos en ambos formatos)."""
import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path

from .horas import a_hora, a_minutos
from .modelo import DEPOSITO, Costos, Mundo, Pedido, Plan, Punto, Ruta, Vehiculo


class ErrorDatos(Exception):
    """Datos de entrada mal formados."""


class ErrorPlan(Exception):
    """Archivo de plan mal formado (no se puede ni leer)."""


# --------------------------------------------------------------------------- utilidades

def _vacio(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _entero(v, donde: str) -> int:
    if isinstance(v, bool):
        raise ErrorDatos(f"{donde}: se esperaba un entero y vino {v!r}")
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    try:
        return int(str(v).strip())
    except ValueError:
        raise ErrorDatos(f"{donde}: se esperaba un entero y vino {v!r}") from None


def _numero(v, donde: str) -> float:
    if isinstance(v, bool):
        raise ErrorDatos(f"{donde}: se esperaba un número y vino {v!r}")
    try:
        n = float(str(v).strip().replace(",", ".")) if isinstance(v, str) else float(v)
    except (TypeError, ValueError):
        raise ErrorDatos(f"{donde}: se esperaba un número y vino {v!r}") from None
    return int(n) if n.is_integer() else n


def _booleano(v, donde: str) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and v in (0, 1):
        return bool(v)
    t = str(v).strip().lower()
    if t in ("1", "true", "si", "sí", "verdadero"):
        return True
    if t in ("0", "false", "no", "falso"):
        return False
    raise ErrorDatos(f"{donde}: se esperaba un booleano (1/0) y vino {v!r}")


def _hora(v, donde: str) -> int:
    try:
        return a_minutos(v)
    except ValueError as e:
        raise ErrorDatos(f"{donde}: {e}") from None


ARCHIVOS_DATOS = {f"{n}.{e}" for n in ("mundo", "pedidos", "vehiculos") for e in ("json", "csv")}
MAX_ZIP_DESCOMPRIMIDO = 2 * 1024 * 1024


def _filas_csv(texto: str) -> list:
    texto = texto.lstrip("﻿")
    primera = texto.splitlines()[0] if texto.strip() else ""
    sep = ";" if (";" in primera and "," not in primera) else ","
    filas = []
    for fila in csv.DictReader(io.StringIO(texto), delimiter=sep):
        limpia = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in fila.items()}
        if not all(_vacio(v) for v in limpia.values()):
            filas.append(limpia)
    return filas


def _leer_csv(path: Path) -> list:
    return _filas_csv(path.read_text(encoding="utf-8-sig"))


def _leer_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ErrorDatos(f"{path.name}: JSON inválido ({e})") from None


# --------------------------------------------------------------------------- mundo

# (clave en archivo, tipo, defecto)
CAMPOS_MUNDO = [
    ("grilla_ancho", "entero", 20),
    ("grilla_alto", "entero", 20),
    ("deposito_x", "entero", 0),
    ("deposito_y", "entero", 0),
    ("hora_salida", "hora", "08:00"),
    ("tiempo_servicio", "entero", 5),
    ("tiempo_carga", "entero", 10),
    ("min_por_cuadra", "entero", 3),
    ("costo_por_cuadra", "numero", 3),
    ("costo_por_vehiculo", "numero", 60),
    ("costo_por_minuto_total", "numero", 1),
    ("costo_por_falla", "numero", 200),
]
CAMPOS_MUNDO += [("costo_por_minuto_premium", "numero", 1)]


def mundo_desde_dict(d: dict) -> Mundo:
    if not isinstance(d, dict):
        raise ErrorDatos("mundo: se esperaba un objeto con claves")
    v = {}
    for clave, tipo, defecto in CAMPOS_MUNDO:
        crudo = d.get(clave)
        crudo = defecto if _vacio(crudo) else crudo
        donde = f"mundo.{clave}"
        v[clave] = {"entero": _entero, "numero": _numero, "hora": _hora}[tipo](crudo, donde)
    m = Mundo(
        ancho=v["grilla_ancho"], alto=v["grilla_alto"],
        deposito=Punto(v["deposito_x"], v["deposito_y"]),
        hora_salida=v["hora_salida"], tiempo_servicio=v["tiempo_servicio"],
        tiempo_carga=v["tiempo_carga"], min_por_cuadra=v["min_por_cuadra"],
        costos=Costos(
            por_cuadra=v["costo_por_cuadra"], por_vehiculo=v["costo_por_vehiculo"],
            por_minuto_total=v["costo_por_minuto_total"], por_falla=v["costo_por_falla"],
        ),
    )
    m.costos.por_minuto_premium = v["costo_por_minuto_premium"]
    if m.ancho <= 0 or m.alto <= 0:
        raise ErrorDatos("mundo: la grilla debe tener tamaño positivo")
    if not m.contiene(m.deposito):
        raise ErrorDatos("mundo: el depósito está fuera de la grilla")
    if m.min_por_cuadra <= 0 or m.tiempo_servicio < 0 or m.tiempo_carga < 0:
        raise ErrorDatos("mundo: tiempos inválidos")
    return m


def mundo_a_dict(m: Mundo) -> dict:
    c = m.costos
    d = {
        "grilla_ancho": m.ancho, "grilla_alto": m.alto,
        "deposito_x": m.deposito.x, "deposito_y": m.deposito.y,
        "hora_salida": a_hora(m.hora_salida), "tiempo_servicio": m.tiempo_servicio,
        "tiempo_carga": m.tiempo_carga, "min_por_cuadra": m.min_por_cuadra,
        "costo_por_cuadra": c.por_cuadra, "costo_por_vehiculo": c.por_vehiculo,
        "costo_por_minuto_total": c.por_minuto_total, "costo_por_falla": c.por_falla,
    }
    d["costo_por_minuto_premium"] = c.por_minuto_premium
    return d


# --------------------------------------------------------------------------- pedidos

CAMPOS_PEDIDO = ["id", "x", "y", "peso"]
CAMPOS_PEDIDO += ["premium"]


def pedidos_desde_filas(filas, mundo: Mundo) -> dict:
    if not isinstance(filas, list):
        raise ErrorDatos("pedidos: se esperaba una lista")
    pedidos = {}
    for i, f in enumerate(filas, start=1):
        if not isinstance(f, dict):
            raise ErrorDatos(f"pedidos, elemento {i}: se esperaba un objeto")
        for req in ("id", "x", "y", "peso"):
            if _vacio(f.get(req)):
                raise ErrorDatos(f"pedidos, elemento {i}: falta '{req}'")
        pid = _entero(f["id"], f"pedidos, elemento {i}, id")
        donde = f"pedido {pid}"
        pos = Punto(_entero(f["x"], f"{donde}, x"), _entero(f["y"], f"{donde}, y"))
        peso = _entero(f["peso"], f"{donde}, peso")
        extra = {}
        extra["premium"] = False if _vacio(f.get("premium")) else _booleano(f["premium"], f"{donde}, premium")
        if pid in pedidos:
            raise ErrorDatos(f"{donde}: id repetido")
        if not mundo.contiene(pos):
            raise ErrorDatos(f"{donde}: ({pos.x},{pos.y}) está fuera de la grilla")
        if peso < 0:
            raise ErrorDatos(f"{donde}: peso negativo")
        pedidos[pid] = Pedido(pid, pos, peso, **extra)
    return pedidos


def pedidos_a_filas(pedidos: dict) -> tuple:
    """Devuelve (columnas, filas). Solo incluye columnas opcionales si algún pedido las usa."""
    lista = list(pedidos.values())
    columnas = ["id", "x", "y", "peso"]
    if any(p.premium for p in lista):
        columnas.append("premium")
    filas = []
    for p in lista:
        f = {"id": p.id, "x": p.pos.x, "y": p.pos.y, "peso": p.peso}
        if "premium" in columnas:
            f["premium"] = p.premium
        filas.append(f)
    return columnas, filas


# --------------------------------------------------------------------------- vehículos

CAMPOS_VEHICULO = ["id"]


def vehiculos_desde_filas(filas, mundo: Mundo) -> dict:
    if not isinstance(filas, list):
        raise ErrorDatos("vehiculos: se esperaba una lista")
    vehiculos = {}
    for i, f in enumerate(filas, start=1):
        if not isinstance(f, dict) or _vacio(f.get("id")):
            raise ErrorDatos(f"vehiculos, elemento {i}: falta 'id'")
        vid = str(f["id"]).strip()
        donde = f"vehículo {vid}"
        if vid in vehiculos:
            raise ErrorDatos(f"{donde}: id repetido")
        if vid.upper() == DEPOSITO:
            raise ErrorDatos(f"{donde}: '{DEPOSITO}' no puede usarse como id de vehículo")
        v = Vehiculo(vid, min_por_cuadra=mundo.min_por_cuadra, costo_fijo=mundo.costos.por_vehiculo)
        vehiculos[vid] = v
    return vehiculos


def vehiculos_a_filas(vehiculos: dict, mundo: Mundo) -> tuple:
    lista = list(vehiculos.values())
    columnas = ["id"]
    filas = []
    for v in lista:
        filas.append({k: getattr(v, k) for k in columnas})
    return columnas, filas


# --------------------------------------------------------------------------- plan

def _parada(v, donde: str):
    if isinstance(v, str) and v.strip().upper() == DEPOSITO:
        return DEPOSITO
    if isinstance(v, bool):
        raise ErrorPlan(f"{donde}: parada inválida {v!r}")
    if isinstance(v, int):
        return v
    try:
        return int(str(v).strip())
    except ValueError:
        raise ErrorPlan(f"{donde}: parada inválida {v!r} (se espera id de pedido o {DEPOSITO})") from None


def plan_desde_dict(d) -> Plan:
    if not isinstance(d, dict) or not isinstance(d.get("rutas"), list):
        raise ErrorPlan("el plan debe ser un objeto con una lista 'rutas'")
    rutas = []
    for i, r in enumerate(d["rutas"], start=1):
        if not isinstance(r, dict) or _vacio(r.get("vehiculo")):
            raise ErrorPlan(f"ruta {i}: falta 'vehiculo'")
        paradas = r.get("paradas", [])
        if not isinstance(paradas, list):
            raise ErrorPlan(f"ruta {i}: 'paradas' debe ser una lista")
        vid = str(r["vehiculo"]).strip()
        rutas.append(Ruta(vid, [_parada(p, f"ruta {i} ({vid})") for p in paradas]))
    return Plan(rutas)


def plan_desde_filas_csv(filas) -> Plan:
    rutas = {}
    for i, f in enumerate(filas, start=2):  # fila 1 = encabezado
        if _vacio(f.get("vehiculo")) or _vacio(f.get("parada")):
            raise ErrorPlan(f"plan CSV, fila {i}: faltan 'vehiculo' o 'parada'")
        vid = f["vehiculo"].strip()
        rutas.setdefault(vid, []).append(_parada(f["parada"], f"plan CSV, fila {i}"))
    return Plan([Ruta(v, p) for v, p in rutas.items()])


def plan_a_dict(plan: Plan) -> dict:
    return {"rutas": [{"vehiculo": r.vehiculo, "paradas": list(r.paradas)} for r in plan.rutas]}


# --------------------------------------------------------------------------- archivos

def _elegir(directorio: Path, nombre: str, formato):
    if formato:
        p = directorio / f"{nombre}.{formato}"
        return p if p.exists() else None
    for ext in ("json", "csv"):
        p = directorio / f"{nombre}.{ext}"
        if p.exists():
            return p
    return None


def cargar_datos(directorio, formato=None):
    """Carga mundo, pedidos y vehículos de una carpeta. formato: None (prefiere JSON), 'json' o 'csv'."""
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise ErrorDatos(f"no existe la carpeta de datos: {directorio}")

    p = _elegir(directorio, "mundo", formato)
    if p is None:
        mundo = mundo_desde_dict({})
    elif p.suffix == ".json":
        mundo = mundo_desde_dict(_leer_json(p))
    else:
        filas = _leer_csv(p)
        if filas and not {"clave", "valor"} <= set(filas[0]):
            raise ErrorDatos("mundo.csv: se esperan las columnas 'clave,valor'")
        mundo = mundo_desde_dict({f["clave"]: f["valor"] for f in filas})

    salida = [mundo]
    for nombre, func in (("pedidos", pedidos_desde_filas), ("vehiculos", vehiculos_desde_filas)):
        p = _elegir(directorio, nombre, formato)
        if p is None:
            raise ErrorDatos(f"falta {nombre}.json o {nombre}.csv en {directorio}")
        filas = _leer_json(p) if p.suffix == ".json" else _leer_csv(p)
        salida.append(func(filas, mundo))
    return tuple(salida)


def plan_desde_texto(texto: str, nombre_archivo: str) -> Plan:
    """Lee un plan desde su contenido; el formato sale de la extensión (.json o .csv)."""
    ext = Path(nombre_archivo).suffix.lower()
    if ext == ".csv":
        filas = _filas_csv(texto)
        if filas and not {"vehiculo", "parada"} <= set(filas[0]):
            raise ErrorPlan("plan CSV: se esperan las columnas 'vehiculo,parada'")
        return plan_desde_filas_csv(filas)
    if ext == ".json":
        try:
            d = json.loads(texto.lstrip("﻿"))
        except json.JSONDecodeError as e:
            raise ErrorPlan(f"plan: JSON inválido ({e})") from None
        return plan_desde_dict(d)
    raise ErrorPlan("el plan tiene que ser un archivo .json o .csv")


def cargar_plan(ruta) -> Plan:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorPlan(f"no existe el archivo de plan: {ruta}")
    # por línea de comandos, todo lo que no sea .csv se lee como JSON (como antes)
    nombre = ruta.name if ruta.suffix.lower() == ".csv" else "plan.json"
    return plan_desde_texto(ruta.read_text(encoding="utf-8-sig"), nombre)


def datos_desde_zip(contenido: bytes, formato=None):
    """Carga un dataset desde un .zip. Toma solo mundo/pedidos/vehiculos (.json/.csv), estén o no en una carpeta."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile:
        raise ErrorDatos("el archivo no es un .zip válido") from None
    with zf, tempfile.TemporaryDirectory() as tmp:
        def nombre(i):   # algunos compresores de Windows usan "\\" como separador
            return i.filename.replace("\\", "/").rsplit("/", 1)[-1]
        miembros = [i for i in zf.infolist() if not i.is_dir() and nombre(i) in ARCHIVOS_DATOS]
        if sum(i.file_size for i in miembros) > MAX_ZIP_DESCOMPRIMIDO:
            raise ErrorDatos("el .zip es demasiado grande")
        for i in miembros:
            destino = Path(tmp) / nombre(i)   # solo el nombre: nunca se escribe fuera de tmp
            if destino.exists():
                raise ErrorDatos(f"el .zip tiene más de un {destino.name}")
            destino.write_bytes(zf.read(i))
        return cargar_datos(tmp, formato)


def datos_a_zip(mundo, pedidos, vehiculos) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        guardar_datos(tmp, mundo, pedidos, vehiculos)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(Path(tmp).iterdir()):
                zf.write(p, p.name)
        return buf.getvalue()


def datos_a_dict(mundo, pedidos, vehiculos) -> dict:
    return {"mundo": mundo_a_dict(mundo), "pedidos": pedidos_a_filas(pedidos)[1],
            "vehiculos": vehiculos_a_filas(vehiculos, mundo)[1]}


def datos_desde_dict(d: dict):
    mundo = mundo_desde_dict(d["mundo"])
    return mundo, pedidos_desde_filas(d["pedidos"], mundo), vehiculos_desde_filas(d["vehiculos"], mundo)


def _csv_valor(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def _escribir_csv(path: Path, columnas, filas):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columnas)
        for f in filas:
            w.writerow([_csv_valor(f.get(c)) for c in columnas])


def _escribir_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def guardar_datos(directorio, mundo, pedidos, vehiculos, formatos=("json", "csv")):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    md = mundo_a_dict(mundo)
    cp, fp = pedidos_a_filas(pedidos)
    cv, fv = vehiculos_a_filas(vehiculos, mundo)
    if "json" in formatos:
        _escribir_json(directorio / "mundo.json", md)
        _escribir_json(directorio / "pedidos.json", fp)
        _escribir_json(directorio / "vehiculos.json", fv)
    if "csv" in formatos:
        _escribir_csv(directorio / "mundo.csv", ["clave", "valor"], [{"clave": k, "valor": v} for k, v in md.items()])
        _escribir_csv(directorio / "pedidos.csv", cp, fp)
        _escribir_csv(directorio / "vehiculos.csv", cv, fv)


def guardar_plan(ruta, plan: Plan):
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".csv":
        filas = [{"vehiculo": r.vehiculo, "parada": p} for r in plan.rutas for p in r.paradas]
        _escribir_csv(ruta, ["vehiculo", "parada"], filas)
    else:
        _escribir_json(ruta, plan_a_dict(plan))
