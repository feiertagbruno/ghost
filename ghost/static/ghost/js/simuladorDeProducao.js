const codigo_identificador = document.getElementById("codigo-identificador-id")
const textarea = document.getElementById('codigos-produtos-id');
const input_codigo = document.querySelector("#codigo-produto-id")

gerarCodigoAleatorio(10, codigo_identificador)

input_codigo.addEventListener("keyup", (e) => {
	if (/^[a-zA-Z0-9]$/.test(e.key) || e.key === "Backspace" || e.key === "Delete") {
		input_codigo.value = input_codigo.value && input_codigo.value !== "" ? input_codigo.value.toUpperCase() : input_codigo.value
	}
})
