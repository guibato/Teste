from django.db import models
from django.utils import timezone
from decimal import Decimal


class TimestampedModel(models.Model):
    """
    Modelo base com campos de timestamp
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


