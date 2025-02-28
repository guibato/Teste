from decimal import Decimal
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
from django.conf import settings
import logging

# Move the calcular_aluguel_projetado function here, but don't import models
logger = logging.getLogger(__name__)

def calcular_aluguel_projetado(contrato):
    """
    Calculates the projected rent based on the IPCA inflation index.
    """
    logger.info(f"Calculando aluguel projetado para contrato ID: {contrato.id}")
    
    # Use the same function body from your utils.py
    # ...rest of your calculation function...