from django.db import models

class Processamento(models.Model):
	codigo_identificador = models.CharField(max_length=10)
	caller = models.CharField(max_length=30)
	porcentagem = models.CharField(max_length=10)
	mensagem1 = models.CharField(max_length=150)
	mensagem2 = models.CharField(max_length=150)
	finalizado = models.BooleanField(default=False)