const textarea = document.getElementById('codigos-produtos-id');
const botao_buscar = document.getElementById("botao-multi-simples")
const form_multi = document.getElementById("form-multi-id")
const csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
const codigo_identificador = gerarCodigoAleatorio(10, document.getElementById("codigo-identificador-id"))

textarea.addEventListener('input', () => {
	textarea.style.height = 'auto';
	textarea.style.height = (textarea.scrollHeight) + 'px';
});
form_multi.addEventListener("submit", () => {
	mostra_tela_aguarde(csrf, codigo_identificador, "multiestruturas")
})
