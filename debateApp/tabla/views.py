from __future__ import annotations
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Max

from .models import (
    Torneo, Equipo, Debatiente, Ronda, Sala, SalaEquipo, ResultadoSala
)
from .forms import (
    TorneoForm, EquipoForm, DebatienteForm,
    EquiposFormSet
)
from .services import (
    generar_emparejamientos,
    cerrar_ronda_y_actualizar_tabla,
    _puntos_por_ranking,
)


# =========================
# Autenticación
# =========================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Bienvenido, {user.username}.')
            return redirect('home')
    else:
        form = AuthenticationForm(request)

    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente. Ahora puedes iniciar sesión.')
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Sesión cerrada.')
    return redirect('login')


# =========================
# Home / Lista de torneos
# =========================
@login_required
def home(request):
    torneos = Torneo.objects.order_by('-creado')
    return render(request, 'home.html', {'torneos': torneos})


# =========================
# CRUD Torneo
# =========================
@login_required
@transaction.atomic
def torneo_nuevo(request):
    if request.method == 'POST':
        form = TorneoForm(request.POST)
        if form.is_valid():
            torneo = form.save()
            # crear rondas clasificatorias 1..N
            for n in range(1, torneo.n_rondas + 1):
                Ronda.objects.create(torneo=torneo, numero=n)
            messages.success(request, 'Torneo creado. Ahora ingresa los equipos.')
            return redirect('torneo_equipos', torneo_id=torneo.id)
    else:
        form = TorneoForm()
    return render(request, 'torneo_nuevo.html', {'form': form})

@login_required
@transaction.atomic
def torneo_editar(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)
    if request.method == 'POST':
        form = TorneoForm(request.POST, instance=torneo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Torneo actualizado.')
            return redirect('home')
    else:
        form = TorneoForm(instance=torneo)
    return render(request, 'torneo_nuevo.html', {'form': form})

@login_required
@transaction.atomic
def torneo_eliminar(request, pk):
    torneo = get_object_or_404(Torneo, pk=pk)
    if request.method == 'POST':
        torneo.delete()
        messages.success(request, 'Torneo eliminado.')
        return redirect('home')
    return render(request, 'confirm_delete.html', {'obj': torneo, 'volver': 'home'})


# ===========================================
# Paso 2: Carga MASIVA de equipos (exactamente N)
# ===========================================
@login_required
@transaction.atomic
def torneo_equipos(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    prefix = 'eq'
    if request.method == 'POST':
        formset = EquiposFormSet(request.POST, prefix=prefix)
        if formset.is_valid():
            # limpiar equipos no-swing previos (si los hubiera)
            Equipo.objects.filter(torneo=torneo, es_swing=False).delete()
            creados = 0
            for f in formset:
                data = f.cleaned_data
                if not data or not data.get('nombre_equipo'):
                    continue
                equipo = Equipo.objects.create(torneo=torneo, nombre=data['nombre_equipo'])
                Debatiente.objects.create(equipo=equipo, nombre=data['integrante1'])
                Debatiente.objects.create(equipo=equipo, nombre=data['integrante2'])
                creados += 1
            if creados == 0:
                messages.error(request, 'Debes ingresar al menos un equipo.')
                formset = EquiposFormSet(prefix=prefix, initial=[{} for _ in range(torneo.n_equipos)])
                return render(request, 'torneo_equipos.html', {'torneo': torneo, 'formset': formset})
            messages.success(request, f'{creados} equipos guardados.')
            return redirect('ronda_view', torneo_id=torneo.id, num=1)
        else:
            return render(request, 'torneo_equipos.html', {'torneo': torneo, 'formset': formset})
    else:
        formset = EquiposFormSet(prefix=prefix, initial=[{} for _ in range(torneo.n_equipos)])
        return render(request, 'torneo_equipos.html', {'torneo': torneo, 'formset': formset})


# =========================
# CRUD Equipos
# =========================
@login_required
def equipos_list(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = torneo.equipos.order_by('nombre')
    return render(request, 'equipos_list.html', {'torneo': torneo, 'equipos': equipos})

@login_required
@transaction.atomic
def equipo_nuevo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    if request.method == 'POST':
        form = EquipoForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            e.torneo = torneo
            e.save()
            messages.success(request, 'Equipo creado.')
            return redirect('equipos_list', torneo_id=torneo.id)
    else:
        form = EquipoForm()
    return render(request, 'equipo_form.html', {'torneo': torneo, 'form': form})

@login_required
@transaction.atomic
def equipo_editar(request, pk):
    e = get_object_or_404(Equipo, pk=pk)
    if request.method == 'POST':
        form = EquipoForm(request.POST, instance=e)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo actualizado.')
            return redirect('equipos_list', torneo_id=e.torneo_id)
    else:
        form = EquipoForm(instance=e)
    return render(request, 'equipo_form.html', {'torneo': e.torneo, 'form': form})

@login_required
@transaction.atomic
def equipo_eliminar(request, pk):
    e = get_object_or_404(Equipo, pk=pk)
    torneo_id = e.torneo_id
    if request.method == 'POST':
        e.delete()
        messages.success(request, 'Equipo eliminado.')
        return redirect('equipos_list', torneo_id=torneo_id)
    return render(request, 'confirm_delete.html', {
        'obj': e, 'volver': 'equipos_list', 'volver_kwargs': {'torneo_id': torneo_id}
    })


# =========================
# CRUD Miembros (Debatientes)
# =========================
@login_required
def miembros_list(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    miembros = equipo.debatientes.order_by('id')
    return render(request, 'miembros_list.html', {'equipo': equipo, 'miembros': miembros})

@login_required
@transaction.atomic
def miembro_nuevo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    if request.method == 'POST':
        form = DebatienteForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.equipo = equipo
            m.save()
            messages.success(request, 'Miembro agregado.')
            return redirect('miembros_list', equipo_id=equipo.id)
    else:
        form = DebatienteForm()
    return render(request, 'miembro_form.html', {'equipo': equipo, 'form': form})

@login_required
@transaction.atomic
def miembro_editar(request, pk):
    m = get_object_or_404(Debatiente, pk=pk)
    if request.method == 'POST':
        form = DebatienteForm(request.POST, instance=m)
        if form.is_valid():
            form.save()
            messages.success(request, 'Miembro actualizado.')
            return redirect('miembros_list', equipo_id=m.equipo_id)
    else:
        form = DebatienteForm(instance=m)
    return render(request, 'miembro_form.html', {'equipo': m.equipo, 'form': form})

@login_required
@transaction.atomic
def miembro_eliminar(request, pk):
    m = get_object_or_404(Debatiente, pk=pk)
    equipo_id = m.equipo_id
    if request.method == 'POST':
        m.delete()
        messages.success(request, 'Miembro eliminado.')
        return redirect('miembros_list', equipo_id=equipo_id)
    return render(request, 'confirm_delete.html', {
        'obj': m, 'volver': 'miembros_list', 'volver_kwargs': {'equipo_id': equipo_id}
    })


# =========================
# Tabla / Ranking
# =========================
@login_required
def torneo_tabla(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = torneo.equipos.order_by('-puntos', '-speakers_total', '-speakers_prom', 'id')
    return render(request, 'torneo_tabla.html', {'torneo': torneo, 'equipos': equipos})


@login_required
def torneo_continuar(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    # 1) Si el torneo ya está cerrado, ir directo a la tabla
    if torneo.cerrado:
        return redirect('torneo_tabla', torneo_id=torneo.id)

    ronda_abierta = (
        Ronda.objects
        .filter(torneo=torneo, cerrada=False)
        .order_by('numero')
        .first()
    )
    if ronda_abierta:
        return redirect('ronda_view', torneo_id=torneo.id, num=ronda_abierta.numero)

    if Ronda.objects.filter(torneo=torneo).exists():
        return redirect('eliminatorias', torneo_id=torneo.id)

    return redirect('torneo_tabla', torneo_id=torneo.id)


# ===========================================
# Pantalla intermedia entre rondas (ranking)
# ===========================================
@login_required
def entre_rondas(request, torneo_id, num):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = torneo.equipos.order_by('-puntos', '-speakers_total', '-speakers_prom', 'id')

    if request.method == 'POST':
        next_num = num + 1
        if next_num <= torneo.n_rondas:
            # Garantizar que la ronda exista (si no, crearla)
            r, created = Ronda.objects.get_or_create(
                torneo=torneo,
                numero=next_num,
                defaults={'emparejada': False, 'cerrada': False},
            )
            if not r.emparejada:
                # limpiar si hubiese algo inconsistentemente creado
                if r.salas.exists():
                    for s in r.salas.all():
                        s.participaciones.all().delete()
                        s.delete()
                generar_emparejamientos(r)
            return redirect('ronda_view', torneo_id=torneo.id, num=next_num)
        else:
            return redirect('eliminatorias', torneo_id=torneo.id)

    return render(request, 'entre_rondas.html', {
        'torneo': torneo, 'num': num, 'equipos': equipos
    })


# =========================
# Ronda: ingreso de resultados
# =========================
@login_required
@transaction.atomic
def ronda_view(request, torneo_id: int, num: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    ronda = get_object_or_404(Ronda, torneo=torneo, numero=num)

    # Generar emparejamientos si hace falta (idempotente)
    if not ronda.emparejada:
        if ronda.salas.exists():
            for s in ronda.salas.all():
                s.participaciones.all().delete()
                s.delete()
        generar_emparejamientos(ronda)

    salas = list(ronda.salas.all().order_by('id'))

    if request.method == 'POST':
        # Guardar resultados
        for sala in salas:
            ses = list(sala.participaciones.order_by('posicion'))
            rankings, valores = [], []
            for idx, se in enumerate(ses):
                prefix = f"s{sala.id}_{idx}_"
                try:
                    ranking = int(request.POST.get(prefix + "ranking"))
                    or1 = int(request.POST.get(prefix + "orador1"))
                    or2 = int(request.POST.get(prefix + "orador2"))
                except (TypeError, ValueError):
                    messages.error(request, f"Completa todos los resultados de {sala.nombre}.")
                    return redirect('ronda_view', torneo_id=torneo.id, num=num)
                if ranking not in (1, 2, 3, 4) or not (50 <= or1 <= 100) or not (50 <= or2 <= 100):
                    messages.error(request, f"Valores inválidos en {sala.nombre}.")
                    return redirect('ronda_view', torneo_id=torneo.id, num=num)
                rankings.append(ranking)
                valores.append((se, ranking, or1, or2))
            if set(rankings) != {1, 2, 3, 4}:
                messages.error(request, f"En {sala.nombre}, los lugares deben ser 1, 2, 3 y 4 (sin repetir).")
                return redirect('ronda_view', torneo_id=torneo.id, num=num)

            for se, ranking, or1, or2 in valores:
                puntos = _puntos_por_ranking(ranking)
                ResultadoSala.objects.update_or_create(
                    sala_equipo=se,
                    defaults={'ranking': ranking, 'puntos': puntos, 'orador1': or1, 'orador2': or2}
                )

        # Cerrar y actualizar tabla
        try:
            cerrar_ronda_y_actualizar_tabla(ronda)
        except Exception as e:
            messages.error(request, f"No se pudo cerrar la ronda: {e}")
            return redirect('ronda_view', torneo_id=torneo.id, num=num)

        # ¿Es una final? (eliminatoria con una sola sala)
        es_eliminatoria = ronda.numero > torneo.n_rondas
        es_final = es_eliminatoria and ronda.salas.count() == 1

        if es_final:
            sala_final = ronda.salas.first()
            try:
                se_ganador = sala_final.participaciones.get(resultado__ranking=1)
            except SalaEquipo.DoesNotExist:
                messages.warning(request, "No se encontró el ganador de la Final. Revisa los resultados.")
                return redirect('ronda_view', torneo_id=torneo.id, num=num)
            torneo.ganador = se_ganador.equipo
            torneo.cerrado = True
            torneo.save(update_fields=['ganador', 'cerrado'])
            messages.success(request, f"🏆 ¡{torneo.ganador.nombre} es el campeón de {torneo.nombre}!")
            return redirect('torneo_tabla', torneo_id=torneo.id)

        # Flujo normal: clasif o siguiente eliminatoria
        if num < torneo.n_rondas:
            return redirect('entre_rondas', torneo_id=torneo.id, num=num)
        else:
            messages.success(request, 'Rondas finalizadas. Puedes crear eliminatorias.')
            return redirect('eliminatorias', torneo_id=torneo.id)

    # GET: pintar formulario
    paquetes = []
    for sala in salas:
        ses = list(sala.participaciones.order_by('posicion'))
        paquetes.append((sala, ses))
    return render(request, 'ronda.html', {'torneo': torneo, 'ronda': ronda, 'paquetes': paquetes})


# =========================
# Eliminatorias (progresivas)
# =========================
def _nombre_fase(n: int) -> str:
    mapping = {32: 'Octavos', 16: 'Cuartos', 8: 'Semifinal', 4: 'Final'}
    return mapping.get(n, 'Eliminatoria')

@login_required
@transaction.atomic
def eliminatorias_view(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    # Si el torneo ya está cerrado -> no crear nada
    if torneo.cerrado:
        messages.info(request, 'Este torneo ya está cerrado.')
        return redirect('torneo_tabla', torneo_id=torneo.id)

    base = torneo.n_rondas
    elim_qs = torneo.rondas.filter(numero__gt=base).order_by('numero')

    # 1) Si no hay eliminatorias aún -> crear la primera desde la tabla final
    if not elim_qs.exists():
        clasificados = list(
            torneo.equipos.order_by('-puntos', '-speakers_total', '-speakers_prom', 'id')[:torneo.n_clasificados]
        )
        if len(clasificados) < 4 or (len(clasificados) % 4 != 0):
            messages.error(request, 'El número de clasificados debe ser un múltiplo de 4 (mínimo 4).')
            return redirect('torneo_tabla', torneo_id=torneo.id)

        numero = base + 1
        ronda = Ronda.objects.create(torneo=torneo, numero=numero, emparejada=True, cerrada=False)

        fase = _nombre_fase(len(clasificados))
        idx = 1
        for i in range(0, len(clasificados), 4):
            grupo = clasificados[i:i+4]
            sala = Sala.objects.create(ronda=ronda, nombre=f'{fase} {idx}')
            for pidx, equipo in enumerate(grupo):
                SalaEquipo.objects.create(sala=sala, equipo=equipo, posicion=['OG', 'OO', 'CG', 'CO'][pidx])
            idx += 1

        messages.success(request, f'{fase} creadas. Ingresa resultados.')
        return redirect('ronda_view', torneo_id=torneo.id, num=ronda.numero)

    # 2) Ya hay eliminatorias: ver la última
    last_num = elim_qs.aggregate(m=Max('numero'))['m']
    last_round = elim_qs.get(numero=last_num)

    # 2.a) Si la última NO está cerrada -> ir a ingresarla (no crear otra)
    if not last_round.cerrada:
        return redirect('ronda_view', torneo_id=torneo.id, num=last_round.numero)

    # 2.b) La última sí está cerrada -> calcular ganadores para siguiente fase
    ganadores = list(
        Equipo.objects.filter(
            salaequipo__sala__ronda=last_round,
            salaequipo__resultado__ranking=1
        ).distinct()
    )

    # Si ya tenemos 1 ganador -> cerrar torneo
    if len(ganadores) == 1:
        torneo.ganador = ganadores[0]
        torneo.cerrado = True
        torneo.save(update_fields=['ganador', 'cerrado'])
        messages.success(request, f"🏆 ¡{torneo.ganador.nombre} es el campeón de {torneo.nombre}!")
        return redirect('torneo_tabla', torneo_id=torneo.id)

    # Si hay 0 ganadores, avisar
    if len(ganadores) == 0:
        messages.error(request, 'No se encontraron ganadores en la última eliminatoria. Revisa resultados.')
        return redirect('ronda_view', torneo_id=torneo.id, num=last_round.numero)

    # Crear siguiente fase (debe ser múltiplo de 4)
    if len(ganadores) % 4 != 0:
        messages.error(request, 'La cantidad de ganadores no es múltiplo de 4. Revisa resultados.')
        return redirect('ronda_view', torneo_id=torneo.id, num=last_round.numero)

    numero = last_round.numero + 1
    ronda = Ronda.objects.create(torneo=torneo, numero=numero, emparejada=True, cerrada=False)

    fase = _nombre_fase(len(ganadores))
    idx = 1
    for i in range(0, len(ganadores), 4):
        grupo = ganadores[i:i+4]
        sala = Sala.objects.create(ronda=ronda, nombre=f'{fase} {idx}')
        for pidx, equipo in enumerate(grupo):
            SalaEquipo.objects.create(sala=sala, equipo=equipo, posicion=['OG', 'OO', 'CG', 'CO'][pidx])
        idx += 1

    messages.success(request, f'{fase} creadas. Ingresa resultados.')
    return redirect('ronda_view', torneo_id=torneo.id, num=ronda.numero)


@login_required
@require_GET
def torneo_ubicacion_api(request, torneo_id: int):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    return JsonResponse({
        'id': torneo.id,
        'nombre': torneo.nombre,
        'ubicacion_nombre': torneo.lugar_nombre,
        'lat': torneo.lugar_lat,
        'lng': torneo.lugar_lng,
    })
