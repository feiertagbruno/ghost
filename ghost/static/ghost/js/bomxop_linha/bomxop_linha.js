const trazer_produzidos = document.getElementById("traz-produzidos-id")
const codigos = document.getElementById("codigos-produtos-id")
const form = document.querySelector(".form-bomxop-linha")

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

document.querySelector(".botao-mais").onclick = (el) => {
	add_nova_linha_datas()
}

function add_nova_linha_datas() {
	const div_ultima_data = document.querySelector(".ultima-div-data")
	const nova_div_data = div_ultima_data.cloneNode(true)
	div_ultima_data.querySelector(".botao-mais").remove()
	div_ultima_data.classList.remove("ultima-div-data")

	const data_inicial = nova_div_data.querySelector("input[id*='data-inicial']")
	const label_data_inicial = nova_div_data.querySelector(`label[for='${data_inicial.id}']`)
	let id = data_inicial.id.split("-")
	let novo_id = `${id[0]}-${id[1]}-${Number(id[2])+1}`
	data_inicial.id = novo_id
	data_inicial.value = ""
	label_data_inicial.setAttribute("for",novo_id)

	const data_final = nova_div_data.querySelector("input[id*='data-final']")
	const label_data_final = nova_div_data.querySelector(`label[for=${data_final.id}]`)
	id = data_final.id.split("-")
	novo_id = `${id[0]}-${id[1]}-${Number(id[2])+1}`
	data_final.id = novo_id
	data_final.value = ""
	label_data_final.setAttribute("for",novo_id)

	form.insertBefore(nova_div_data,div_ultima_data.nextSibling)

	data_inicial.focus()

	document.querySelector(".botao-mais").onclick = () => {
		add_nova_linha_datas()
	}

}

form.onsubmit = () => {
	mostra_tela_aguarde(
		getCSRFToken(),
		gerarCodigoAleatorio(
			10,
			document.querySelector("#codigo-identificador-id")
		),
		"bomxop_linha"
	)
}