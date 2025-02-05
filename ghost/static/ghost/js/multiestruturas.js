const abrir_detalhamentos = document.querySelectorAll(".abrir-detalhamento")
const fechar_detalhamentos = document.querySelectorAll(".x-fechar-detalhamento")
const detalhamentos = document.querySelectorAll(".detalhamento-custo-total")

if (abrir_detalhamentos) {
	abrir_detalhamentos.forEach((elemento) => {
		elemento.addEventListener("click", () => {
			document.querySelector(`#detalhamento-${elemento.id}`).style.display = "block"
		})
	})
}

if (fechar_detalhamentos) {
	fechar_detalhamentos.forEach((elemento) => {
		elemento.addEventListener("click", () => {
			const id_elemento = elemento.id.split("-")[1]
			document.querySelector(`#detalhamento-${id_elemento}`).style.display = "none"
		})
	})
}

document.addEventListener("keyup",(e) => {
	if (e.key === "Escape") {
		detalhamentos.forEach((det) => {
			det.style.display = "none"
		})
	}
})