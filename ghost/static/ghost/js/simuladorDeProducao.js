const codigo_identificador = document.getElementById("codigo-identificador-id")
const textarea = document.getElementById('codigos-produtos-id');
const input_codigo = document.querySelector("#codigo-produto-id")
const armazens = document.querySelectorAll(".armazem-checkbox")
const form_add_producao = document.getElementById("form-multi-id")
const data_producao = document.getElementById("data-producao-id")
const quant = document.getElementById("quantidade-id")
const botao_trazer_simulacao = document.getElementById("botao-trazer-simulacao-id")

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
	}
}

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
		document.getElementById("form-trazer-simulacao-salva-id").submit()
	}
}

document.addEventListener("DOMContentLoaded", () => {
	const caller = document.querySelector("#caller-id")
	if (caller) {
		if (caller.value === "trazer_simulacao") {
			finalizacao_salvar_tabela(document.querySelector("#nome-da-simulacao-id"))
			
		}
	}
})