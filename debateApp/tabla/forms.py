from django import forms
from django.forms import formset_factory
from .models import Torneo, Equipo, Debatiente, ResultadoSala

# ---- Torneo ----
class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo
        fields = ['nombre', 'responsable', 'n_equipos', 'n_clasificados', 'n_rondas']
        labels = {
            'nombre': 'Nombre del torneo',
            'responsable': 'Responsable',
            'n_equipos': 'Cantidad de equipos',
            'n_clasificados': 'Equipos que clasifican',
            'n_rondas': 'Rondas clasificatorias',
        }

# ---- Equipo (CRUD individual) ----
class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'es_swing']
        labels = {'nombre': 'Nombre del equipo', 'es_swing': '¿Swing?'}

# ---- Debatiente (CRUD individual) ----
class DebatienteForm(forms.ModelForm):
    class Meta:
        model = Debatiente
        fields = ['nombre']
        labels = {'nombre': 'Nombre del debatiente'}

# ---- Paso 2: carga masiva de equipos (exactamente N) ----
class EquiposSimpleForm(forms.Form):
    nombre_equipo = forms.CharField(label='Nombre del equipo', max_length=120)
    integrante1   = forms.CharField(label='Integrante 1', max_length=120)
    integrante2   = forms.CharField(label='Integrante 2', max_length=120)

EquiposFormSet = formset_factory(EquiposSimpleForm, extra=0)

# (opcional) modelo de resultado si llegas a usarlo como form
class ResultadoItemForm(forms.ModelForm):
    class Meta:
        model = ResultadoSala
        fields = ['ranking', 'puntos', 'orador1', 'orador2']


class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo
        fields = [
            'nombre', 'responsable',
            'n_equipos', 'n_clasificados', 'n_rondas',
            'lugar_nombre', 'lugar_lat', 'lugar_lng',
        ]
        labels = {
            'nombre': 'Nombre del torneo',
            'responsable': 'Responsable',
            'n_equipos': 'Cantidad de equipos',
            'n_clasificados': 'Equipos que clasifican',
            'n_rondas': 'Rondas clasificatorias',
            'lugar_nombre': 'Lugar (nombre / sede)',
            'lugar_lat': 'Latitud',
            'lugar_lng': 'Longitud',
        }
       
