# tabla/models.py
from django.db import models

class Torneo(models.Model):
    nombre = models.CharField(max_length=120)
    responsable = models.CharField(max_length=120)
    n_equipos = models.PositiveIntegerField()
    n_clasificados = models.PositiveIntegerField()
    n_rondas = models.PositiveIntegerField()
    creado = models.DateTimeField(auto_now_add=True)
        # Ubicación del torneo
    lugar_nombre = models.CharField(max_length=200, blank=True)
    lugar_lat = models.FloatField(null=True, blank=True)
    lugar_lng = models.FloatField(null=True, blank=True)


    # Estado final
    cerrado = models.BooleanField(default=False)
    ganador = models.ForeignKey(
        'Equipo', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='torneos_ganados'
    )

    def __str__(self):
        return self.nombre


class Equipo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='equipos')
    nombre = models.CharField(max_length=120)
    es_swing = models.BooleanField(default=False)
    puntos = models.IntegerField(default=0)
    speakers_total = models.IntegerField(default=0)
    speakers_prom = models.FloatField(default=0.0)

    def __str__(self):
        return self.nombre


class Debatiente(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='debatientes')
    nombre = models.CharField(max_length=120)

    def __str__(self):
        return f'{self.nombre} ({self.equipo.nombre})'


class Ronda(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='rondas')
    numero = models.PositiveIntegerField()
    emparejada = models.BooleanField(default=False)
    cerrada = models.BooleanField(default=False)

    def __str__(self):
        return f'Ronda {self.numero} – {self.torneo.nombre}'


class Sala(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, related_name='salas')
    nombre = models.CharField(max_length=120)

    def __str__(self):
        return self.nombre


class SalaEquipo(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='participaciones')
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    posicion = models.CharField(max_length=2)  # OG/OO/CG/CO

    class Meta:
        unique_together = (('sala', 'posicion'),)

    def __str__(self):
        return f'{self.sala} - {self.equipo} ({self.posicion})'


class ResultadoSala(models.Model):
    sala_equipo = models.OneToOneField(
        SalaEquipo, on_delete=models.CASCADE, related_name='resultado'
    )
    ranking = models.PositiveIntegerField()  # 1..4
    puntos = models.IntegerField()           # 3/2/1/0
    orador1 = models.PositiveIntegerField()
    orador2 = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.sala_equipo} -> {self.ranking}'
