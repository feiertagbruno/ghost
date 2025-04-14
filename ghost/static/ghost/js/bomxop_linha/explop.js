const form_explop = document.querySelector(".form-explop")
document.getElementById("data-id").value = getTodayDate()

form_explop.onsubmit = () => {
	mostra_tela_aguarde(
		getCSRFToken(),
		gerarCodigoAleatorio(10,document.querySelector("#codigo-identificador-id")),
		"explop"
	)
}
