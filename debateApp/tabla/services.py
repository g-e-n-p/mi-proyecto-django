from __future__ import annotations

from collections import defaultdict
from typing import List, Tuple

from django.db import transaction
from django.db.models import F

from .models import (
    Torneo, Equipo, Ronda, Sala, SalaEquipo, ResultadoSala
)

# Posiciones BP en orden y rotación por número de ronda
POSICIONES = ['OG', 'OO', 'CG', 'CO']

# Puntos por ranking 1..4
PUNTOS_POR_RANKING = {1: 3, 2: 2, 3: 1, 4: 0}


# ------------------------- utilidades básicas -------------------------

def _puntos_por_ranking(r: int) -> int:
    """Devuelve los puntos de equipo según ranking (1..4)."""
    return PUNTOS_POR_RANKING.get(r, 0)


def _necesita_swings(torneo: Torneo) -> int:
    """Cuántos swings faltan para que el total de equipos sea múltiplo de 4."""
    n = torneo.equipos.count()
    resto = n % 4
    return 0 if resto == 0 else (4 - resto)


def _crear_swings_si_faltan(torneo: Torneo) -> None:
    """
    Crea swings SOLO si el total de equipos NO es múltiplo de 4.
    No crea swings adicionales en ningún otro caso.
    """
    faltan = _necesita_swings(torneo)
    if faltan <= 0:
        return
    base = torneo.equipos.filter(es_swing=True).count()
    for i in range(faltan):
        Equipo.objects.create(
            torneo=torneo,
            nombre=f"Swing {base + i + 1}",
            es_swing=True,
        )


def _asignar_posiciones_rotando(ronda: Ronda, equipos: List[Equipo]) -> List[Tuple[Equipo, str]]:
    """
    Asigna OG/OO/CG/CO rotando por número de ronda.
    Por seguridad, si llegan menos de 4 (no debería), asigna a los que existan.
    """
    rot = (ronda.numero - 1) % 4
    pos = POSICIONES[rot:] + POSICIONES[:rot]
    m = min(4, len(equipos))
    return [(equipos[i], pos[i]) for i in range(m)]


# ------------------------- emparejamiento -------------------------

@transaction.atomic
def generar_emparejamientos(ronda: Ronda) -> None:
    """
    Emparejamiento simple (power-pairing clásico):
      1) Asegura múltiplo de 4 creando swings SOLO si faltan para completar.
      2) Ordena equipos por ranking actual: puntos, speakers_total, speakers_prom, id.
      3) Parte consecutivamente en bloques de 4, sin restricciones adicionales.
      4) Asigna OG/OO/CG/CO rotando por ronda.

    Idempotente: si la ronda ya tiene salas, solo marca 'emparejada' (por si quedó false).
    """
    # Idempotencia
    if ronda.salas.exists():
        if not ronda.emparejada:
            ronda.emparejada = True
            ronda.save(update_fields=['emparejada'])
        return

    torneo = ronda.torneo

    # 1) Múltiplo de 4 (único momento en que se crean swings)
    _crear_swings_si_faltan(torneo)

    # 2) Orden por ranking actual
    equipos = list(
        torneo.equipos.order_by('-puntos', '-speakers_total', '-speakers_prom', 'id')
    )

    # 3) Partir en grupos de 4
    grupos = [equipos[i:i + 4] for i in range(0, len(equipos), 4)]

    # 4) Crear salas y posiciones
    for idx, grupo in enumerate(grupos, start=1):
        sala = Sala.objects.create(ronda=ronda, nombre=f"Sala {idx}")
        for equipo, pos in _asignar_posiciones_rotando(ronda, grupo):
            SalaEquipo.objects.create(sala=sala, equipo=equipo, posicion=pos)

    ronda.emparejada = True
    ronda.save(update_fields=['emparejada'])


# ------------------------- cierre de ronda y ranking -------------------------

@transaction.atomic
def cerrar_ronda_y_actualizar_tabla(ronda: Ronda) -> None:
    """
    1) Verifica que todas las participaciones (SalaEquipo) tengan ResultadoSala.
       - Usa related_name='resultado' (ajusta aquí si tu modelo usa otro nombre).
    2) Suma puntos y speakers de la ronda a cada equipo.
    3) Recalcula speakers_prom = speakers_total / (2 * debates_jugados).
    4) Marca la ronda como cerrada.
    """
    # 1) Validación: que no falten resultados en esta ronda
    #    Si tu ForeignKey ResultadoSala(sala_equipo=...) NO usa related_name='resultado',
    #    cambia 'resultado__isnull=True' por el nombre correcto (p.ej. 'resultadosala__isnull=True').
    faltantes = (
        SalaEquipo.objects
        .filter(sala__ronda=ronda, resultado__isnull=True)
        .count()
    )
    if faltantes:
        raise ValueError("Faltan resultados en una o más salas.")

    # 2) Sumar puntos y speakers de esta ronda
    resultados = (
        ResultadoSala.objects
        .filter(sala_equipo__sala__ronda=ronda)
        .select_related('sala_equipo', 'sala_equipo__equipo')
    )

    add_puntos = defaultdict(int)
    add_speakers = defaultdict(int)

    for r in resultados:
        eq_id = r.sala_equipo.equipo_id
        add_puntos[eq_id] += int(r.puntos)
        add_speakers[eq_id] += int(r.orador1) + int(r.orador2)

    for eq_id, pts in add_puntos.items():
        Equipo.objects.filter(id=eq_id).update(
            puntos=F('puntos') + pts,
            speakers_total=F('speakers_total') + add_speakers[eq_id],
        )

    # 3) Recalcular speakers_prom (promedio por orador)
    #    debates_jugados = cantidad de ResultadoSala del equipo (cada resultado = debate por equipo)
    for equipo in Equipo.objects.filter(id__in=add_puntos.keys()):
        debates = ResultadoSala.objects.filter(sala_equipo__equipo=equipo).count()
        denom = max(debates * 2, 1)  # 2 oradores por debate; evita división por 0
        equipo.refresh_from_db(fields=['speakers_total'])
        equipo.speakers_prom = equipo.speakers_total / denom
        equipo.save(update_fields=['speakers_prom'])

    # 4) Marcar ronda cerrada
    ronda.cerrada = True
    ronda.save(update_fields=['cerrada'])
