
def get_query_estrutura_produto():
	return """
DECLARE @DATA_REFERENCIA VARCHAR(10); SET @DATA_REFERENCIA = CONVERT(VARCHAR,:data_referencia,112);
DECLARE @PRODUTO VARCHAR(15); SET @PRODUTO = :codigo;
DECLARE @REVISAO VARCHAR(3); DECLARE @DESCRICAO VARCHAR(50);
DECLARE @TIPO VARCHAR(2);
SELECT
	@REVISAO = MAX(TRIM(B1_REVATU)),
	@DESCRICAO = MAX(TRIM(B1_DESC)),
	@TIPO = MAX(TRIM(B1_TIPO))
FROM VW_MN_SB1 B1
	WHERE B1.D_E_L_E_T_ <> '*' AND B1_COD = @PRODUTO; 

SELECT 
	@PRODUTO codigo_pai,
	@DESCRICAO descricao_pai,
	@TIPO tipo_pai,
	TRIM(G1_COMP) insumo,
	TRIM(B1_DESC) descricao_insumo,
	G1_QUANT quant_utilizada,
	TRIM(B1_FANTASM) fantasma,
	TRIM(B1_TIPO) tipo_insumo,
	TRIM(B1_XORIMRP) origem,
	NULL verificado

FROM VW_MN_SG1 G1

INNER JOIN VW_MN_SB1 B1
	ON B1.D_E_L_E_T_ <> '*'
	AND G1_COMP = B1_COD
	AND B1_TIPO <> 'MO'

WHERE G1.D_E_L_E_T_ <> '*'
	AND G1_COD = @PRODUTO
	AND @DATA_REFERENCIA BETWEEN G1_INI AND G1_FIM
	AND @REVISAO BETWEEN G1_REVINI AND G1_REVFIM
	
"""

def get_query_alternativos():
	return """
SELECT 
	TRIM(GI_PRODORI) prodori,
	TRIM(GI_PRODALT) alternativos,
	TRIM(GI_ORDEM) ordem_alt
FROM VW_MN_SGI GI
WHERE GI.D_E_L_E_T_ <> '*'
	AND GI_PRODORI IN (SELECT value FROM string_split(:codigos,','))
ORDER BY GI_ORDEM DESC
"""


def get_query_ultima_compra_produtos():
	return """
DECLARE @PRODUTOS VARCHAR(MAX); SET @PRODUTOS = :codigos;
DECLARE @DATA_REFERENCIA VARCHAR(10); SET @DATA_REFERENCIA =  CONVERT(varchar,:data_referencia,112);
DECLARE @DATA_INICIAL VARCHAR(10); SET @DATA_INICIAL = CONVERT( VARCHAR, DATEADD(YEAR,-4, @DATA_REFERENCIA),112);
WITH
FRETES AS (
	SELECT 
		[NF ORI], [SERIE NF],
		FORNECEDOR, LOJA,
		SUM(D1_CUSTO) custo_frete

	FROM VW_MN_INFO_FRETE
	INNER JOIN VW_MN_SD1 D1
		ON D1.D_E_L_E_T_ <> '*'
		AND D1_DOC = [NUM CTE]
		AND D1_SERIE = [SERIE CTE]
		AND D1_FORNECE = TRANSP
		AND D1_LOJA = [LOJA TRANSP]

	WHERE [DT DIGIT] BETWEEN @DATA_INICIAL AND @DATA_REFERENCIA
	GROUP BY  [NF ORI], [SERIE NF], FORNECEDOR, LOJA
),
ENTRADAS AS (
SELECT 
	TRIM(D1_COD) codigo, 
	TRIM(D1_FORNECE) forn, 
	TRIM(D1_LOJA) loja,
	TRIM(D1_DOC) doc, 
	TRIM(D1_SERIE) serie,
	D1_DTDIGIT digitacao, 
	SUM(D1_QUANT) quant, 
	SUM(D1_TOTAL) total, 
	SUM(D1_CUSTO) custo

FROM VW_MN_SD1 D1
WHERE
	D1.D_E_L_E_T_ <> '*'
	AND D1_DTDIGIT BETWEEN @DATA_INICIAL AND @DATA_REFERENCIA
	AND ( D1_TES IN ('011','012','159','086','134')
	OR D1_CF IN ('1101','1124','2101','3101') )
	AND D1_COD IN ( SELECT value FROM string_split(@PRODUTOS, ',') )
	AND D1_QUANT <> 0
GROUP BY
	D1_COD, 
	D1_FORNECE, 
	D1_LOJA,
	D1_DOC, 
	D1_SERIE,
	D1_DTDIGIT

),

ULTIMAS_COMPRAS AS (
	SELECT 
		codigo,
		TRIM(A2_NOME) fornecedor,
		digitacao, quant,
		
		custo + ISNULL(
			(custo_frete * total /
			SUM(total) OVER(PARTITION BY forn, loja, doc, serie))
		,0) custo,

		ROW_NUMBER() OVER (
			PARTITION BY codigo
			ORDER BY digitacao DESC, doc DESC
		) num_linha

	FROM ENTRADAS E
	LEFT JOIN FRETES FR
		ON E.doc = FR.[NF ORI]
		AND E.serie = FR.[SERIE NF]
		AND E.forn = FR.FORNECEDOR
		AND E.loja = FR.LOJA

	LEFT JOIN VW_MN_SA2 A2
		ON A2.D_E_L_E_T_ <> '*'
		AND forn = TRIM(A2_COD)
		AND loja = TRIM(A2_LOJA)

	WHERE codigo IN (SELECT value FROM string_split(@PRODUTOS,','))
),

CONSULTA AS (
	SELECT 
		'Código: ' + codigo + ',' + CHAR(10) + 
		'Fornecedor: ' + fornecedor + ',' + CHAR(10) +
		'Data: ' + CONVERT(VARCHAR,CONVERT(DATE, digitacao),103) + ',' + CHAR(10) +
		'Quantidade: ' + CAST(quant AS varchar(20))  + ',' + CHAR(10) +
		'Custo Últ. Entrada: ' + REPLACE(CAST(ROUND(custo / quant, 5) AS varchar(20)),'.',',') comentario_ultima_compra,

		ROUND(custo / quant, 5) ult_compra_custo_utilizado,
		codigo insumo

	FROM ULTIMAS_COMPRAS
	WHERE num_linha = 1
)

SELECT * FROM CONSULTA
ORDER BY insumo
"""


def get_query_ultimo_fechamento_produtos():
	return """
	DECLARE @PRODUTOS VARCHAR(MAX) =  :codigos;
	DECLARE @DATA_REFERENCIA VARCHAR(10) = CONVERT(VARCHAR,:data_referencia,112);
	DECLARE @DATA_INICIAL VARCHAR(10) = CONVERT(VARCHAR, DATEADD(YEAR,-4,:data_referencia),112);
	DECLARE @ARMAZENS VARCHAR(20) = '11,14,20'

	SELECT TRIM(B9_COD) insumo,
		B9_CM1 fechamento_custo_utilizado,
		'Código: ' + TRIM(B9_COD) + ',' + CHAR(10) +
		'Data Fechamento: ' + CONVERT(VARCHAR,CONVERT(DATE,B9_DATA),103) + ',' + CHAR(10) +
		'Custo Últ Fechamento: ' + REPLACE(CAST(B9_CM1 AS varchar(20)),'.',',') comentario_fechamento

	FROM VW_MN_SB9 B9
	WHERE B9.D_E_L_E_T_ <> '*'
		AND B9_QINI > 0
		AND B9_COD IN (SELECT value FROM string_split(@PRODUTOS,','))
		AND B9_DATA BETWEEN @DATA_INICIAL AND @DATA_REFERENCIA
		AND B9_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
		AND R_E_C_N_O_ = (
			SELECT MAX(R_E_C_N_O_) FROM VW_MN_SB9 B9A
			WHERE B9A.D_E_L_E_T_ <> '*'
				AND B9.B9_COD = B9A.B9_COD
				AND B9A.B9_QINI > 0
				AND B9A.B9_DATA BETWEEN @DATA_INICIAL AND @DATA_REFERENCIA
				AND B9A.B9_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
		)
	ORDER BY insumo
"""


def get_query_custos_medios_produtos():
	return """
	DECLARE @PRODUTOS VARCHAR(MAX) = :codigos;
	DECLARE @DATA_REFERENCIA VARCHAR(10) = CONVERT(VARCHAR,GETDATE(),112);
	DECLARE @ARMAZENS VARCHAR(20) = '11,14,20'

	SELECT
		TRIM(B2_COD) insumo, 
		ROUND(B2_CM1,5) medio_atual_custo_utilizado,
		CASE
			WHEN B2_CM1 = 0 THEN '' ELSE
			'Código: ' + TRIM(B2_COD) + ',' + CHAR(10) +
			'Custo Médio em ' + CONVERT(VARCHAR,GETDATE(),103) + ',' + CHAR(10) +
			'Custo: R$ ' + REPLACE(CAST(B2_CM1 AS varchar(20)),'.',',')
		END comentario_custo_medio


	FROM VW_MN_SB2 B2
	WHERE B2.D_E_L_E_T_ <> '*'
		AND B2_COD IN ( SELECT value FROM string_split(@PRODUTOS, ',') )
		--AND B2_QATU > 0
		AND B2_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
		AND B2_LOCAL = (
			SELECT MIN(B2_LOCAL) FROM VW_MN_SB2 B2A
			WHERE B2A.D_E_L_E_T_ <> '*'
			AND B2.B2_COD = B2A.B2_COD
			--AND B2_QATU > 0
			AND B2_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
		)
	ORDER BY insumo
"""

def get_query_detalhamento_op():
	return """
DECLARE @NUMERO_OP VARCHAR(11) = :numero_op ;

WITH CONSULTA_OP AS (
	SELECT
		TRIM(D4_OP) op,
		TRIM(D4_PRODUTO) codigo_original,
		ISNULL(CONVERT(VARCHAR, CONVERT(DATE, C2_EMISSAO),103),'') data_referencia,
		ISNULL(CONVERT(VARCHAR, CONVERT(DATE, C2_DATRF),103),'') data_encerramento_op,
		TRIM(D4_COD) insumo,
		TRIM(B1_DESC) descricao_insumo,
		TRIM(B1_TIPO) tipo_insumo,
		ROUND((D4_QTDEORI / C2_QUANT),5) quant_utilizada,
		C2_QUJE quant_produzida, 
		D4_QTDEORI - D4_QUANT quant_total_utilizada
	
	FROM VW_MN_SD4 D4
	INNER JOIN VW_MN_SC2 C2
		ON C2.D_E_L_E_T_ <> '*' 
		AND D4_PRODUTO = C2_PRODUTO
		AND (TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN)) = D4_OP
	INNER JOIN VW_MN_SB1 B1
		ON B1.D_E_L_E_T_ <> '*'
		AND D4_COD = B1_COD
		AND B1_TIPO <> 'MO'

	WHERE D4.D_E_L_E_T_ <> '*'
		AND D4_OP = @NUMERO_OP
)

SELECT 
	op, codigo_original, data_referencia,
	data_encerramento_op, insumo,
	descricao_insumo, tipo_insumo,
	SUM(quant_utilizada) quant_utilizada,
	SUM(quant_produzida) quant_produzida,
	SUM(quant_total_utilizada) quant_total_utilizada

FROM CONSULTA_OP

GROUP BY op, codigo_original, data_referencia,
	data_encerramento_op, insumo,
	descricao_insumo, tipo_insumo
"""

def get_query_busca_descricao_produto():
	return """
	SELECT TOP 1 TRIM(B1_DESC) descricao, TRIM(B1_TIPO) tipo 
	FROM VW_MN_SB1 B1 WHERE B1.D_E_L_E_T_ <> '*' AND B1_COD = :codigo
"""

def get_query_busca_info_produtos():
	return """
DECLARE @CODIGOS VARCHAR(MAX) = :codigos ;
SELECT 
	TRIM(B1_COD) codigo,
	TRIM(B1_DESC) descricao, 
	TRIM(B1_TIPO) tipo 
FROM VW_MN_SB1 B1 WHERE B1.D_E_L_E_T_ <> '*' 
	AND B1_COD IN ( SELECT value FROM string_split(@CODIGOS, ',') )
"""

def get_query_numeros_op_por_periodo():
	return """
DECLARE @DATA_INICIAL VARCHAR(10) = CONVERT(VARCHAR, :data_inicial,112)
DECLARE @DATA_FINAL VARCHAR(10) = CONVERT(VARCHAR, :data_final, 112)

SELECT 
	TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) op

FROM VW_MN_SC2 C2
WHERE C2.D_E_L_E_T_ <> '*'
	AND C2_DATRF <> ''
	AND C2_DATRF BETWEEN @DATA_INICIAL AND @DATA_FINAL
GROUP BY TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN), C2_DATRF
ORDER BY C2_DATRF DESC, TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) DESC
"""

def get_query_busca_op_pelo_produto():
	return """
DECLARE @PRODUTO VARCHAR(15) = :produto ;
SELECT TOP 1
	TRIM(C2_NUM) + TRIM(C2_ITEM) + TRIM(C2_SEQUEN) op
FROM VW_MN_SC2 C2
WHERE C2.D_E_L_E_T_ <> '*'
	AND C2_DATRF <> ''
	AND C2_PRODUTO = @PRODUTO
ORDER BY R_E_C_N_O_ DESC
"""

def get_query_compra_mais_antiga():
	return """
DECLARE @PRODUTOS VARCHAR(MAX); SET @PRODUTOS = :produtos ;
DECLARE @DATA_REFERENCIA VARCHAR(10); SET @DATA_REFERENCIA =  CONVERT(VARCHAR,:data_referencia,112);
WITH
FRETES AS (
	SELECT 
		[NF ORI], [SERIE NF],
		FORNECEDOR, LOJA,
		SUM(D1_CUSTO) custo_frete

	FROM VW_MN_INFO_FRETE
	INNER JOIN VW_MN_SD1 D1
		ON D1.D_E_L_E_T_ <> '*'
		AND D1_DOC = [NUM CTE]
		AND D1_SERIE = [SERIE CTE]
		AND D1_FORNECE = TRANSP
		AND D1_LOJA = [LOJA TRANSP]

	WHERE [DT DIGIT] >= @DATA_REFERENCIA
	GROUP BY  [NF ORI], [SERIE NF], FORNECEDOR, LOJA
),
ENTRADAS AS (
SELECT 
	TRIM(D1_COD) codigo, 
	TRIM(D1_FORNECE) forn, 
	TRIM(D1_LOJA) loja,
	TRIM(D1_DOC) doc, 
	TRIM(D1_SERIE) serie,
	D1_DTDIGIT digitacao, 
	SUM(D1_QUANT) quant, 
	SUM(D1_TOTAL) total, 
	SUM(D1_CUSTO) custo

FROM VW_MN_SD1 D1
WHERE
	D1.D_E_L_E_T_ <> '*'
	AND D1_DTDIGIT >= @DATA_REFERENCIA
	AND ( D1_TES IN ('011','012','159','086','134')
	OR D1_CF IN ('1101','1124','2101','3101') )
	AND D1_COD IN ( SELECT value FROM string_split(@PRODUTOS, ',') )
	AND D1_QUANT <> 0
GROUP BY
	D1_COD, 
	D1_FORNECE, 
	D1_LOJA,
	D1_DOC, 
	D1_SERIE,
	D1_DTDIGIT

),

ULTIMAS_COMPRAS AS (
	SELECT 
		codigo,
		TRIM(A2_NOME) fornecedor,
		digitacao, quant,
		
		custo + ISNULL(
			(custo_frete * total /
			SUM(total) OVER(PARTITION BY forn, loja, doc, serie))
		,0) custo,

		ROW_NUMBER() OVER (
			PARTITION BY codigo
			ORDER BY digitacao, doc
		) num_linha

	FROM ENTRADAS E
	LEFT JOIN FRETES FR
		ON E.doc = FR.[NF ORI]
		AND E.serie = FR.[SERIE NF]
		AND E.forn = FR.FORNECEDOR
		AND E.loja = FR.LOJA

	LEFT JOIN VW_MN_SA2 A2
		ON A2.D_E_L_E_T_ <> '*'
		AND forn = TRIM(A2_COD)
		AND loja = TRIM(A2_LOJA)

	WHERE codigo IN (SELECT value FROM string_split(@PRODUTOS,','))
),

CONSULTA AS (
	SELECT 
		'Código: ' + codigo + ',' + CHAR(10) + 
		'Fornecedor: ' + fornecedor + ',' + CHAR(10) +
		'Data: ' + CONVERT(VARCHAR,CONVERT(DATE, digitacao),103) + ',' + CHAR(10) +
		'Quantidade: ' + CAST(quant AS varchar(20))  + ',' + CHAR(10) +
		'Custo Últ. Entrada: ' + REPLACE(CAST(ROUND(custo / quant, 5) AS varchar(20)),'.',',') comentario_ultima_compra,

		ROUND(custo / quant, 5) ult_compra_custo_utilizado,
		codigo insumo

	FROM ULTIMAS_COMPRAS
	WHERE num_linha = 1
)

SELECT * FROM CONSULTA
ORDER BY insumo
"""

def get_query_menor_fechamento():
	return """
DECLARE @PRODUTOS VARCHAR(MAX) =  :produtos ;
DECLARE @DATA_REFERENCIA VARCHAR(10) = CONVERT(VARCHAR, :data_fechamento,112);
DECLARE @ARMAZENS VARCHAR(20) = '11,14,20';

SELECT TRIM(B9_COD) insumo,
	B9_CM1 fechamento_custo_utilizado,
	'Código: ' + TRIM(B9_COD) + ',' + CHAR(10) +
	'Data Fechamento: ' + CONVERT(VARCHAR,CONVERT(DATE,B9_DATA),103) + ',' + CHAR(10) +
	'Custo Últ Fechamento: ' + REPLACE(CAST(B9_CM1 AS varchar(20)),'.',',') comentario_fechamento

FROM VW_MN_SB9 B9
WHERE B9.D_E_L_E_T_ <> '*'
	AND B9_QINI > 0
	AND B9_COD IN (SELECT value FROM string_split(@PRODUTOS,','))
	AND B9_DATA >= @DATA_REFERENCIA
	AND B9_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
	AND R_E_C_N_O_ = (
		SELECT MIN(R_E_C_N_O_) FROM VW_MN_SB9 B9A
		WHERE B9A.D_E_L_E_T_ <> '*'
			AND B9.B9_COD = B9A.B9_COD
			AND B9A.B9_QINI > 0
			AND B9A.B9_DATA >= @DATA_REFERENCIA
			AND B9A.B9_LOCAL IN ( SELECT value FROM string_split(@ARMAZENS, ',') )
	)
	ORDER BY insumo
"""

def get_query_estoque_atual():
	return """
DECLARE @CODIGOS VARCHAR(MAX) = :codigos ;
SELECT
	TRIM(B2_COD) codigo,
	B2_LOCAL armazem,
	ISNULL(B2_QATU,0) quant
FROM VW_MN_SB2 B2
WHERE B2.D_E_L_E_T_ <> '*'
	AND B2_QATU <> 0
	AND B2_COD IN ( SELECT value FROM string_split(@CODIGOS, ',') )
"""

def get_query_pedidos_para_simulador_de_producao():
	return """
DECLARE @HOJE VARCHAR(10) = CONVERT(VARCHAR,GETDATE(),112);
DECLARE @CODIGOS VARCHAR(MAX) = :codigos ;
SELECT
	Produto codigo,
	CONVERT(VARCHAR, CONVERT(DATE,
		CASE 
			WHEN Entrega < @HOJE THEN DATEADD(DAY,1,@HOJE)
			ELSE Entrega
		END
	), 105) entrega,
	SUM([Quant.Receber]) quant
FROM VW_MN_PEDIDOS_COMPRA_EM_ABERTO
	WHERE Tipo IN ('BN','EM','MP','PI')
		AND (@CODIGOS IS NULL OR Produto IN ( ( SELECT value FROM string_split(@CODIGOS, ',') ) ))
GROUP BY Produto, Emissao, Entrega, Tipo
"""

def get_query_ultima_compra_sem_frete():
	return """
DECLARE @PRODUTOS VARCHAR(MAX); SET @PRODUTOS = :codigos;
DECLARE @DATA_REFERENCIA VARCHAR(10); SET @DATA_REFERENCIA =  CONVERT(varchar,:data_referencia,112);
DECLARE @DATA_INICIAL VARCHAR(10); SET @DATA_INICIAL = CONVERT( VARCHAR, DATEADD(YEAR,-4, @DATA_REFERENCIA),112);
WITH
ENTRADAS AS (
SELECT 
	TRIM(D1_COD) codigo, 
	TRIM(D1_FORNECE) forn, 
	TRIM(D1_LOJA) loja,
	TRIM(D1_DOC) doc, 
	TRIM(D1_SERIE) serie,
	D1_DTDIGIT digitacao, 
	SUM(D1_QUANT) quant, 
	SUM(D1_TOTAL) total, 
	SUM(D1_CUSTO) custo

FROM VW_MN_SD1 D1
WHERE
	D1.D_E_L_E_T_ <> '*'
	AND D1_DTDIGIT BETWEEN @DATA_INICIAL AND @DATA_REFERENCIA
	AND ( D1_TES IN ('011','012','159','086','134')
	OR D1_CF IN ('1101','1124','2101','3101') )
	AND D1_COD IN ( SELECT value FROM string_split(@PRODUTOS, ',') )
	AND D1_QUANT <> 0
GROUP BY
	D1_COD, 
	D1_FORNECE, 
	D1_LOJA,
	D1_DOC, 
	D1_SERIE,
	D1_DTDIGIT

),

ULTIMAS_COMPRAS AS (
	SELECT 
		codigo,
		TRIM(A2_NOME) fornecedor,
		digitacao, quant,
		
		total custo,

		ROW_NUMBER() OVER (
			PARTITION BY codigo
			ORDER BY digitacao DESC, doc DESC
		) num_linha

	FROM ENTRADAS E

	LEFT JOIN VW_MN_SA2 A2
		ON A2.D_E_L_E_T_ <> '*'
		AND forn = TRIM(A2_COD)
		AND loja = TRIM(A2_LOJA)

	WHERE codigo IN (SELECT value FROM string_split(@PRODUTOS,','))
),

CONSULTA AS (
	SELECT 
		'Código: ' + codigo + ',' + CHAR(10) + 
		'Fornecedor: ' + fornecedor + ',' + CHAR(10) +
		'Data: ' + CONVERT(VARCHAR,CONVERT(DATE, digitacao),103) + ',' + CHAR(10) +
		'Quantidade: ' + CAST(quant AS varchar(20))  + ',' + CHAR(10) +
		'Custo Últ. Entrada: ' + REPLACE(CAST(ROUND(custo / quant, 5) AS varchar(20)),'.',',') comentario_ultima_compra,

		ROUND(custo / quant, 5) ult_compra_custo_utilizado,
		codigo insumo

	FROM ULTIMAS_COMPRAS
	WHERE num_linha = 1
)

SELECT * FROM CONSULTA
ORDER BY insumo
"""

def get_query_compra_mais_antiga_sem_frete():
	return """
DECLARE @PRODUTOS VARCHAR(MAX); SET @PRODUTOS = :produtos ;
DECLARE @DATA_REFERENCIA VARCHAR(10); SET @DATA_REFERENCIA =  CONVERT(VARCHAR,:data_referencia,112);
WITH
ENTRADAS AS (
SELECT 
	TRIM(D1_COD) codigo, 
	TRIM(D1_FORNECE) forn, 
	TRIM(D1_LOJA) loja,
	TRIM(D1_DOC) doc, 
	TRIM(D1_SERIE) serie,
	D1_DTDIGIT digitacao, 
	SUM(D1_QUANT) quant, 
	SUM(D1_TOTAL) total, 
	SUM(D1_CUSTO) custo

FROM VW_MN_SD1 D1
WHERE
	D1.D_E_L_E_T_ <> '*'
	AND D1_DTDIGIT >= @DATA_REFERENCIA
	AND ( D1_TES IN ('011','012','159','086','134')
	OR D1_CF IN ('1101','1124','2101','3101') )
	AND D1_COD IN ( SELECT value FROM string_split(@PRODUTOS, ',') )
	AND D1_QUANT <> 0
GROUP BY
	D1_COD, 
	D1_FORNECE, 
	D1_LOJA,
	D1_DOC, 
	D1_SERIE,
	D1_DTDIGIT

),

ULTIMAS_COMPRAS AS (
	SELECT 
		codigo,
		TRIM(A2_NOME) fornecedor,
		digitacao, quant,
		
		total custo,

		ROW_NUMBER() OVER (
			PARTITION BY codigo
			ORDER BY digitacao, doc
		) num_linha

	FROM ENTRADAS E

	LEFT JOIN VW_MN_SA2 A2
		ON A2.D_E_L_E_T_ <> '*'
		AND forn = TRIM(A2_COD)
		AND loja = TRIM(A2_LOJA)

	WHERE codigo IN (SELECT value FROM string_split(@PRODUTOS,','))
),

CONSULTA AS (
	SELECT 
		'Código: ' + codigo + ',' + CHAR(10) + 
		'Fornecedor: ' + fornecedor + ',' + CHAR(10) +
		'Data: ' + CONVERT(VARCHAR,CONVERT(DATE, digitacao),103) + ',' + CHAR(10) +
		'Quantidade: ' + CAST(quant AS varchar(20))  + ',' + CHAR(10) +
		'Custo Últ. Entrada: ' + REPLACE(CAST(ROUND(custo / quant, 5) AS varchar(20)),'.',',') comentario_ultima_compra,

		ROUND(custo / quant, 5) ult_compra_custo_utilizado,
		codigo insumo

	FROM ULTIMAS_COMPRAS
	WHERE num_linha = 1
)

SELECT * FROM CONSULTA
ORDER BY insumo
"""




def get_query_produzidos_da_data():
	return """
DECLARE @DATA_INICIAL VARCHAR(10) = CONVERT(varchar, :data_inicial,112);
DECLARE @DATA_FINAL VARCHAR(10) = CONVERT(varchar, :data_final,112);
DECLARE @CODIGOS VARCHAR(MAX) = :codigos;

SELECT 
	TRIM(D3_COD) codigo,
	SUM(D3_QUANT) quant,
	CONVERT(date, D3_EMISSAO) data
FROM VW_MN_SD3 D3
WHERE D3.D_E_L_E_T_ <> '*'
	AND D3_TM = '200'
	AND D3_ESTORNO <> 'S'
	AND D3_FILIAL = '01'
	AND D3_EMISSAO BETWEEN @DATA_INICIAL AND @DATA_FINAL
	AND ( @CODIGOS IS NULL OR D3_COD IN ( SELECT value FROM string_split(@CODIGOS, ',') ) )
GROUP BY D3_COD, D3_EMISSAO
"""