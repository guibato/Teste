# financeiro/urls.py (adicionar essas URLs ao seu arquivo existente)

from django.urls import path
from financeiro.views.envio_csv_views import envio_personalizado_views, envio_csv_views

app_name = 'financeiro'

urlpatterns = [
    # ... suas URLs existentes de lembretes ...
    
    # ================================================================
    # URLs PARA ENVIO PERSONALIZADO (sistema anterior)
    # ================================================================
    path('envio-personalizado/', 
         envio_personalizado_views.envio_personalizado, 
         name='envio_personalizado'),
    
    path('envio-personalizado/resultados/', 
         envio_personalizado_views.resultados_envio_personalizado, 
         name='resultados_envio_personalizado'),
    
    path('api/clientes/', 
         envio_personalizado_views.buscar_clientes_api, 
         name='buscar_clientes_api'),
    
    # ================================================================
    # URLs PARA SISTEMA CSV (novo sistema)
    # ================================================================
    path('csv/upload/', 
         envio_csv_views.upload_csv_leads, 
         name='upload_csv_leads'),
    
    path('csv/configurar/', 
         envio_csv_views.configurar_envio_csv, 
         name='configurar_envio_csv'),
    
    path('csv/resultados/', 
         envio_csv_views.resultados_csv, 
         name='resultados_csv'),
]

# ================================================================
# EXEMPLO DE COMO INTEGRAR NO MENU PRINCIPAL
# ================================================================

# Adicione essas opções ao seu menu principal/sidebar:

"""
<!-- No seu template base/menu -->
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
        <i class="fas fa-paper-plane"></i> Envio de Mensagens
    </a>
    <ul class="dropdown-menu">
        <li><a class="dropdown-item" href="{% url 'financeiro:envio_programado' %}">
            <i class="fas fa-calendar"></i> Lembretes Automáticos
        </a></li>
        <li><a class="dropdown-item" href="{% url 'financeiro:envio_personalizado' %}">
            <i class="fas fa-users"></i> Envio para Clientes
        </a></li>
        <li><a class="dropdown-item" href="{% url 'financeiro:upload_csv_leads' %}">
            <i class="fas fa-file-csv"></i> Upload CSV de Leads
        </a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="{% url 'financeiro:lembrete_list' %}">
            <i class="fas fa-list"></i> Histórico de Envios
        </a></li>
        <li><a class="dropdown-item" href="{% url 'financeiro:dashboard_lembretes' %}">
            <i class="fas fa-chart-bar"></i> Dashboard
        </a></li>
    </ul>
</li>
"""