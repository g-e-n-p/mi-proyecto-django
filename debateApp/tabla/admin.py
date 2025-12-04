# tabla/admin.py
from django.contrib import admin
from .models import Torneo, Equipo, Debatiente, Ronda, Sala, SalaEquipo, ResultadoSala

@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'responsable', 'n_rondas', 'n_clasificados', 'cerrado', 'ganador')
    list_filter = ('cerrado',)
    search_fields = ('nombre', 'responsable')

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'torneo', 'es_swing', 'puntos', 'speakers_total', 'speakers_prom')
    list_filter = ('torneo', 'es_swing')
    search_fields = ('nombre',)

@admin.register(Debatiente)
class DebatienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'equipo')
    list_filter = ('equipo__torneo',)
    search_fields = ('nombre', 'equipo__nombre')

@admin.register(Ronda)
class RondaAdmin(admin.ModelAdmin):
    list_display = ('torneo', 'numero', 'emparejada', 'cerrada')
    list_filter = ('torneo', 'emparejada', 'cerrada')

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ronda')
    list_filter = ('ronda__torneo',)

@admin.register(SalaEquipo)
class SalaEquipoAdmin(admin.ModelAdmin):
    list_display = ('sala', 'equipo', 'posicion')
    list_filter = ('sala__ronda__torneo', 'posicion')

@admin.register(ResultadoSala)
class ResultadoSalaAdmin(admin.ModelAdmin):
    list_display = ('sala_equipo', 'ranking', 'puntos', 'orador1', 'orador2')
    list_filter = ('sala_equipo__sala__ronda__torneo', 'ranking')
