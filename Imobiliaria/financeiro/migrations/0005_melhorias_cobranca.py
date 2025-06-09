from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal

class Migration(migrations.Migration):
    
    dependencies = [
        ('financeiro', '0004_alter_reajustealuguel_data_reajuste_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cobranca',
            name='valor_despesas',
            field=models.DecimalField(
                max_digits=10, 
                decimal_places=2, 
                default=Decimal('0.00')
            ),
        ),
        
        migrations.AddField(
            model_name='cobranca',
            name='status_detalhes',
            field=models.JSONField(default=dict, blank=True),
        ),
        
        migrations.CreateModel(
            name='AsaasIntegracao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('asaas_id', models.CharField(max_length=100, unique=True)),
                ('gateway_status', models.CharField(max_length=30, blank=True, null=True)),
                ('boleto_url', models.URLField(blank=True, null=True)),
                ('pix_copia_cola', models.TextField(blank=True, null=True)),
                ('pix_url', models.URLField(blank=True, null=True)),
                ('data_integracao', models.DateTimeField(auto_now_add=True)),
                ('cobranca', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, 
                    to='financeiro.cobranca'
                )),
            ],
        ),
    ]