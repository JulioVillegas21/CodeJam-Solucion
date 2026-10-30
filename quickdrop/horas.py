"""Conversión entre "HH:MM" y minutos desde las 00:00."""


def a_minutos(valor) -> int:
    if isinstance(valor, bool):
        raise ValueError(f"hora inválida: {valor!r}")
    if isinstance(valor, int):
        return valor
    texto = str(valor).strip()
    partes = texto.split(":")
    if len(partes) != 2 or not all(p.strip().isdigit() for p in partes):
        raise ValueError(f"hora inválida: {valor!r} (se espera HH:MM)")
    h, m = int(partes[0]), int(partes[1])
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"hora inválida: {valor!r}")
    return h * 60 + m


def a_hora(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"
