from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # If you want to include urls from the sisimob app
    path('', include('sisimob.urls')),  # Only include this if sisimob has its own urls.py
    

    
]