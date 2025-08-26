from django.urls import path
from core.views.base import (
    home,
    logout_view,
    buscar,
    sucesso,
    autocomplete_field,
    nacionalidade_autocomplete,
    confirmar_exclusao
)

urlpatterns = [
    # Página inicial
    path('', home, name='home'),
    path('logout/', logout_view, name='logout'),
    
    # Páginas auxiliares
    path('buscar/', buscar, name='buscar'),
    path('sucesso/', sucesso, name='sucesso'),
    
    # URLs de autocomplete
    path('autocomplete/<str:model_name>/<str:field_name>/', autocomplete_field, name='autocomplete_field'),
    path('nacionalidade-autocomplete/', nacionalidade_autocomplete, name='nacionalidade-autocomplete'),
    
    # Confirmação de exclusão
    path('confirmar-exclusao/<str:model_name>/<int:id>/', confirmar_exclusao, name='confirmar_exclusao'),
]