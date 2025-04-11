from datetime import datetime

def get_query_ultima_op_por_produto_por_data_de_referencia():
	return """
DECLARE @DATA_REFERENCIA VARCHAR(8) = CONVERT(VARCHAR, :data_referencia, 112)
DECLARE @CODIGO VARCHAR(15) = :codigo ;

SELECT TOP 1
	TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) op
FROM VW_MN_SC2 C2
WHERE C2.D_E_L_E_T_ = ''
	AND C2_DATRF <= @DATA_REFERENCIA
	AND C2_DATRF <> ''
	AND C2_PRODUTO = @CODIGO
ORDER BY R_E_C_N_O_ DESC
"""


def get_query_numeros_op_varios_periodos_somente_PA(datas_iniciais:list, datas_finais:list):

	str_datas = ""
	for i in range(len(datas_iniciais)):
		data_inicial = datetime.strftime(datas_iniciais[i],"%Y%m%d")
		data_final = datetime.strftime(datas_finais[i],"%Y%m%d")

		if i != 0: str_datas += " OR"
		str_datas += f" C2_DATRF BETWEEN '{data_inicial}' AND '{data_final}' "
	
	query = f"""
DECLARE @CODIGOS VARCHAR(MAX) = :codigos ;
DECLARE @TIPOS_APONTAMENTO VARCHAR(MAX) = :tipos_apontamento ;

SELECT 
	TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) op,
	CONVERT(DATE, C2_DATRF) data_encerramento_op,
	TRIM(C2_PRODUTO) produto,
	TRIM(B1_DESC) descricao,
	B1_TIPO tipo

FROM VW_MN_SC2 C2
INNER JOIN VW_MN_SB1 B1
	ON B1.D_E_L_E_T_ <> '*'
	AND C2_PRODUTO = B1_COD
	AND B1_TIPO = 'PA'
WHERE C2.D_E_L_E_T_ <> '*'
	AND C2_DATRF <> ''
	AND ( {str_datas} )
	AND ( @CODIGOS IS NULL OR C2_PRODUTO IN ( SELECT value FROM string_split(@CODIGOS, ',') ) )
	AND ( @TIPOS_APONTAMENTO IS NULL OR C2_XTPAPON IN ( SELECT value FROM string_split(@TIPOS_APONTAMENTO, ',') ) )
GROUP BY TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN), C2_DATRF, C2_PRODUTO, B1_DESC, B1_TIPO
ORDER BY C2_DATRF DESC, TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) DESC
"""

	return query