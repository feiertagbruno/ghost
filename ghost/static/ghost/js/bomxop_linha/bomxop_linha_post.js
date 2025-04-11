const commods = document.getElementsByClassName("commod-titulo")
const sku_titulos = document.querySelectorAll(".sku-titulo")

if (commods.length > 0) {
	Array.from(commods).forEach(el => {
		el.onclick = () => {
			const id = el.id
			const tabela = document.querySelector(`#tabela-${id}`)
			if (tabela.classList.contains("hidden")) {
				tabela.classList.remove("hidden")
			} else {
				tabela.classList.add("hidden")
			}
		}
	});
}

if (sku_titulos.length > 0) {
	Array.from(sku_titulos).forEach(el => {
		el.onclick = () => {
			const tabelas = el.parentElement.querySelectorAll(".tabela-boxmop-linha-div")
			console.log(tabelas)
			if (tabelas.length > 0) {
				Array.from(tabelas).forEach(tab => {
					if (!tab.classList.contains("hidden")) {
						tab.classList.add("hidden")
					}
				})
			}
			const id = el.id
			const dados = document.querySelectorAll(`.dados-${id}`)
			Array.from(dados).forEach(dd => {
				if (dd.classList.contains("hidden")) {
					dd.classList.remove("hidden")
				} else {
					dd.classList.add("hidden")
				}
				})
		}
	})
}