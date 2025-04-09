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