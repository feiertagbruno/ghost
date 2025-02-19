const codigo_identificador = document.getElementById("codigo-identificador-id")
const textarea = document.getElementById('codigos-produtos-id');
const input_codigo = document.querySelector("#codigo-produto-id")
const armazens = document.querySelectorAll(".armazem-checkbox")
const form_tabela_simulador = document.getElementById("form-tabela-simulador-id")

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

form_tabela_simulador.onsubmit = () => {
	document.getElementById("tabela-simulador-html-id").value = document.querySelector(".tabela-simulador").outerHTML
}