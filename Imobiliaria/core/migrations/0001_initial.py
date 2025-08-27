from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Imovel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Contrato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fiador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contratos_fiador', to='core.cliente')),
                ('imovel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contratos_imovel', to='core.imovel')),
                ('inquilino', models.ManyToManyField(related_name='contratos_inquilino', to='core.cliente')),
                ('proprietario', models.ManyToManyField(related_name='contratos_proprietario', to='core.cliente')),
            ],
        ),
    ]