const botao_buscar = document.getElementById("botao-multi-simples")
const form_multi = document.getElementById("form-multi-id")
const csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
const codigo_identificador = gerarCodigoAleatorio(10, document.getElementById("codigo-identificador-id"))
const explodir_pis = document.getElementById("explodir-pis-id")
const data_referencia = document.getElementById("data-referencia-id")
const traz_preco_futuro = document.getElementById("traz-preco-futuro-id")

form_multi.addEventListener("submit", () => {
	mostra_tela_aguarde(csrf, codigo_identificador, "multiestruturas")
})

explodir_pis.onclick = (e) => {
	if (e.target.checked) {
		document.getElementById("texto-checkbox-explodir-pis").innerText = "   (Todos os PIs serão explodidos)"
	} else {
		document.getElementById("texto-checkbox-explodir-pis").innerText = "   (Somente PIs fantasmas serão explodidos)"
	}
}

data_referencia.onchange = (el) => {
	if (el.target.value && el.target.value < getTodayDate() && parseInt(el.target.value.slice(0,4),10) > 2000) {
		traz_preco_futuro.setAttribute("checked", true)
		traz_preco_futuro.parentElement.classList.remove("hidden")
	} else if (el.target.value && el.target.value >= getTodayDate() && parseInt(el.target.value.slice(0,4),10) > 2000) {
		traz_preco_futuro.removeAttribute("checked")
		// traz_preco_futuro.parentElement.classList.add("hidden")
	}
}