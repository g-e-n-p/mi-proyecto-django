from django.contrib import admin
from django.urls import path
from tabla import views as tv

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('login/', tv.login_view, name='login'),
    path('registro/', tv.register_view, name='register'),
    path('logout/', tv.logout_view, name='logout'),

    # Home / Torneos
    path('', tv.home, name='home'),
    path('torneo/nuevo/', tv.torneo_nuevo, name='torneo_nuevo'),
    path('torneo/<int:pk>/editar/', tv.torneo_editar, name='torneo_editar'),
    path('torneo/<int:pk>/eliminar/', tv.torneo_eliminar, name='torneo_eliminar'),
    path('torneo/<int:torneo_id>/continuar/', tv.torneo_continuar, name='torneo_continuar'),

    # Paso 2: carga masiva de equipos
    path('torneo/<int:torneo_id>/equipos/carga/', tv.torneo_equipos, name='torneo_equipos'),

    # CRUD Equipos
    path('torneo/<int:torneo_id>/equipos/', tv.equipos_list, name='equipos_list'),
    path('torneo/<int:torneo_id>/equipos/nuevo/', tv.equipo_nuevo, name='equipo_nuevo'),
    path('equipo/<int:pk>/editar/', tv.equipo_editar, name='equipo_editar'),
    path('equipo/<int:pk>/eliminar/', tv.equipo_eliminar, name='equipo_eliminar'),

    # CRUD Miembros (debatientes)
    path('equipo/<int:equipo_id>/miembros/', tv.miembros_list, name='miembros_list'),
    path('equipo/<int:equipo_id>/miembros/nuevo/', tv.miembro_nuevo, name='miembro_nuevo'),
    path('miembro/<int:pk>/editar/', tv.miembro_editar, name='miembro_editar'),
    path('miembro/<int:pk>/eliminar/', tv.miembro_eliminar, name='miembro_eliminar'),

    # Rondas + pantallas
    path('torneo/<int:torneo_id>/tabla/', tv.torneo_tabla, name='torneo_tabla'),
    path('torneo/<int:torneo_id>/ronda/<int:num>/', tv.ronda_view, name='ronda_view'),
    path('torneo/<int:torneo_id>/entre/<int:num>/', tv.entre_rondas, name='entre_rondas'),

    # Eliminatorias
    path('torneo/<int:torneo_id>/eliminatorias/', tv.eliminatorias_view, name='eliminatorias'),

    # API REST – ubicación del torneo
    path('api/torneos/<int:torneo_id>/ubicacion/', tv.torneo_ubicacion_api,
         name='torneo_ubicacion_api'),
]

