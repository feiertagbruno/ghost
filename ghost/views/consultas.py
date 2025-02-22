from pandas import read_sql
from sqlalchemy import text
from typing import Literal

from ghost.utils.funcs import get_engine
from ghost.queries import (
	get_query_produzidos_da_data, get_query_pedidos_para_simulador_de_producao
)

def get_produzidos_na_data(data_inicial,data_final = None, codigos = None, engine = None):

	if not engine:
		engine = get_engine()

	if not data_final:
		data_final = data_inicial

	query = get_query_produzidos_da_data()

	resultado = read_sql(text(query), engine, params={
		"data_inicial": data_inicial,
		"data_final": data_final,
		"codigos": codigos
	})

	return resultado




def get_pedidos(solicitante: Literal["simulador"], codigos: str = None,  engine = None):
	"""Deixe 'codigos' em branco para retornar todos os produtos"""
	
	if not engine: engine = get_engine()
	resultado = None

	if solicitante == "simulador":
		query = get_query_pedidos_para_simulador_de_producao()
		resultado = read_sql(text(query),engine, params={"codigos":codigos})

	return resultado

