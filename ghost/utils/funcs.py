from dotenv import load_dotenv
from os import environ
from sqlalchemy import create_engine, text
from sqlalchemy import text
import pandas as pd
from datetime import datetime, timedelta 

from ghost.queries import get_query_busca_descricao_produto

import random
import string




def gerar_codigo_aleatorio(tamanho=20):
    caracteres = string.ascii_letters + string.digits + "_"
    return ''.join(random.choices(caracteres, k=tamanho))




def extrai_data_fechamento_de_string_yyyy_mm(date_str: str):
    year, month = map(int, date_str.split('-'))
    first_day_next_month = datetime(year + (month // 12), (month % 12) + 1, 1)
    return first_day_next_month - timedelta(days=1)




def get_descricao_produto(codigo, engine = None):
	if not engine:
		engine = get_engine()

	resultado = pd.read_sql(
			text(get_query_busca_descricao_produto()),
			engine, params={"codigo":codigo}
		)
	descricao = resultado["descricao"].values[0]
	tipo = resultado["tipo"].values[0]
	return descricao, tipo




def get_engine():
	load_dotenv()

	SERVER = environ.get("SERVER")
	DB = environ.get("DB")
	USER = environ.get("USER")
	PWD = environ.get("PWD")
	DRIVER = "ODBC Driver 18 for SQL Server"

	connection_string = f"mssql+pyodbc://{USER}:{PWD}@{SERVER}/{DB}?driver={DRIVER}&TrustServerCertificate=yes"

	engine = create_engine(connection_string)
	
	return engine




def tratamento_data_referencia(data_referencia):
	if not data_referencia:
		data_referencia = datetime.today().date()
	elif type(data_referencia) == str:
		if data_referencia.count("-") == 2:
			data_referencia = datetime.strptime(data_referencia, "%Y-%m-%d").date()
		elif data_referencia.count("/") == 2:
			data_referencia = datetime.strptime(data_referencia, "%d/%m/%Y").date()
		else:
			data_referencia = datetime.strptime(data_referencia, "%Y%m%d").date()
	return data_referencia
