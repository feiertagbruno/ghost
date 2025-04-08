const trazer_produzidos = document.getElementById("traz-produzidos-id")
const codigos = document.getElementById("codigos-produtos-id")

if (trazer_produzidos) {
	trazer_produzidos.onchange = e => {
		if (e.target.checked) {
			codigos.value = ""
			codigos.setAttribute("readOnly", true)
			codigos.style.background = "lightgray"
		} else {
			codigos.removeAttribute("readOnly")
			codigos.style.background = "white"
		}
	}
}