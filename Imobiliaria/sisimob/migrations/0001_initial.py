# Generated by Django 3.1.12 on 2025-02-15 01:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Imovel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cep', models.CharField(max_length=10, verbose_name='CEP')),
                ('endereco', models.CharField(max_length=255, verbose_name='Endereço')),
                ('numero', models.CharField(max_length=10, verbose_name='Número')),
                ('complemento', models.CharField(blank=True, max_length=100, null=True, verbose_name='Complemento')),
                ('bairro', models.CharField(blank=True, max_length=100, null=True, verbose_name='Bairro')),
                ('cidade', models.CharField(max_length=100, verbose_name='Cidade')),
                ('estado', models.CharField(max_length=2, verbose_name='Estado')),
                ('iptu', models.CharField(blank=True, max_length=14, null=True, verbose_name='IPTU')),
                ('comgas', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Comgás')),
                ('sabesp', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Sabesp')),
                ('enel', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Enel')),
            ],
        ),
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('Proprietário(a)', 'Proprietário(a)'), ('Inquilino(a)', 'Inquilino(a)'), ('Anuente', 'Anuente'), ('Fiador(a)', 'Fiador(a)')], max_length=20, verbose_name='Tipo')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('nacionalidade', models.CharField(blank=True, max_length=100, null=True, verbose_name='Nacionalidade')),
                ('profissao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Profissão')),
                ('estado_civil', models.CharField(blank=True, choices=[('Solteiro', 'Solteiro(a)'), ('Casado', 'Casado(a)'), ('Divorciado', 'Divorciado(a)'), ('Viuvo', 'Viúvo(a)')], max_length=20, null=True)),
                ('regime_casamento', models.CharField(blank=True, choices=[('comunhao_total', 'Comunhão Total de Bens'), ('comunhao_parcial', 'Comunhão Parcial de Bens'), ('separacao_total', 'Separação Total de Bens')], max_length=20, null=True)),
                ('telefone', models.CharField(blank=True, max_length=15, null=True, verbose_name='Telefone')),
                ('codigo_internacional_celular', models.CharField(blank=True, max_length=5, null=True, verbose_name='Código Internacional (Celular)')),
                ('celular', models.CharField(blank=True, max_length=15, null=True, verbose_name='Celular')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='E-mail')),
                ('pix_modalidade', models.CharField(blank=True, choices=[('cpf', 'CPF'), ('email', 'E-mail'), ('telefone', 'Telefone'), ('aleatorio', 'Chave Aleatória')], max_length=20, null=True, verbose_name='Modalidade PIX')),
                ('chave_pix', models.CharField(blank=True, max_length=100, null=True, verbose_name='Chave PIX')),
                ('banco', models.CharField(blank=True, max_length=100, null=True, verbose_name='Banco')),
                ('agencia', models.CharField(blank=True, max_length=100, null=True, verbose_name='Agência')),
                ('conta_corrente', models.CharField(blank=True, max_length=100, null=True, verbose_name='Conta Corrente')),
                ('poupanca', models.CharField(blank=True, max_length=100, null=True, verbose_name='Poupança')),
                ('cep', models.CharField(max_length=10, verbose_name='CEP')),
                ('endereco', models.CharField(max_length=255, verbose_name='Endereço')),
                ('numero', models.CharField(max_length=10, verbose_name='Número')),
                ('complemento', models.CharField(blank=True, max_length=100, null=True, verbose_name='Complemento')),
                ('bairro', models.CharField(blank=True, max_length=100, null=True, verbose_name='Bairro')),
                ('cidade', models.CharField(max_length=100, verbose_name='Cidade')),
                ('estado', models.CharField(max_length=2, verbose_name='Estado')),
                ('documento', models.FileField(blank=True, null=True, upload_to='documentos/')),
                ('anuente', models.ForeignKey(blank=True, limit_choices_to={'tipo': 'Anuente'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='sisimob.cliente', verbose_name='Anuente')),
            ],
        ),
    ]
