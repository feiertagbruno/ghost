const codigo_identificador = document.getElementById("codigo-identificador-id")
const textarea = document.getElementById('codigos-produtos-id');
const input_codigo = document.querySelector("#codigo-produto-id")
const armazens = document.querySelectorAll(".armazem-checkbox")
const form_add_producao = document.getElementById("form-multi-id")
const data_producao = document.getElementById("data-producao-id")
const quant = document.getElementById("quantidade-id")
const botao_trazer_simulacao = document.getElementById("botao-trazer-simulacao-id")
const csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
const abre_detalhamento = document.getElementById("abre-detalhamento-id")
const explode_pis = document.getElementById("explode-pis-id")


mostra_tela_aguarde(csrf,codigo_identificador,"simulador-de-producao")

gerarCodigoAleatorio(10, codigo_identificador)
input_codigo.addEventListener("keyup", (e) => {
	if (/^[a-zA-Z0-9]$/.test(e.key) || e.key === "Backspace" || e.key === "Delete") {
		input_codigo.value = input_codigo.value && input_codigo.value !== "" ? input_codigo.value.toUpperCase() : input_codigo.value
	}
})

armazens.forEach(arm => {
	arm.onclick = (el) => {
		console.log(el)
	}
})

form_add_producao.onsubmit = e => {
	if (input_codigo.value === '' | data_producao.value === '' | quant.value === '') {
		e.preventDefault()
		mensagem_padrao("message-error","Informações Inválidas")
	} else if (!/[a-z]{3}[0-9]{4}/i.test(input_codigo.value) && 
	!/[a-z]{5}[0-9]{10}/i.test(input_codigo.value)) {
		mensagem_padrao("message-error","Informações Inválidas")
		e.preventDefault()
	} else {
		mostra_tela_aguarde(csrf, codigo_identificador, "adicionar_producao")
	}
}

if (botao_trazer_simulacao) {
	botao_trazer_simulacao.onclick = e => {
		e.preventDefault()
		const simulacoes = document.getElementById("simulacoes-id")
		if (!simulacoes) {
			mensagem_padrao("message-info","Não há simulações salvas")
			return
		}
		simulacoes.style.display = "flex"
		botao_trazer_simulacao.remove()
		simulacoes.onchange = () => {
			mostra_tela_aguarde(csrf, codigo_identificador, "trazer_simulacao")
			document.getElementById("form-trazer-simulacao-salva-id").submit()
		}
	}
	
}

document.addEventListener("DOMContentLoaded", () => {
	const caller = document.querySelector("#caller-id")
	if (caller) {
		if (caller.value === "trazer_simulacao") {
			finalizacao_salvar_tabela(document.querySelector("#nome-da-simulacao-id"))
			
		} else if (caller.value === "adicionar_nova_producao") {
			document.getElementById("tabela-salva-id").value = document.querySelector("#nome-da-simulacao-id").value
		}
		
		remove_texto_tela_aguarde()
		
	}

	const cookie_abre_detalhamento = getCookie("abre_detalhamento_simulador_de_producao")
	const cookie_explode_pis = getCookie("explode_pis_simulador_de_producao")
	
	if (cookie_abre_detalhamento === "true") {
		abre_detalhamento.checked = true
	} else {
		abre_detalhamento.checked = false
	}
	
	if (cookie_explode_pis === "true") {
		explode_pis.checked = true
	} else {
		explode_pis.checked = false
	}

})

abre_detalhamento.onchange = e => {

	if (e.target.checked) {
		document.cookie = "abre_detalhamento_simulador_de_producao=true;path=/"
	} else {
		document.cookie = "abre_detalhamento_simulador_de_producao=false;path=/"
	}
}

explode_pis.onchange = e => {
	if (e.target.checked) {
		document.cookie = "explode_pis_simulador_de_producao=true;path=/"
	} else {
		document.cookie = "explode_pis_simulador_de_producao=false;path=/"
	}
}