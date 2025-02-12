const input_op = document.querySelector("#numero-op-id")
const datas = document.querySelectorAll(".data-multiestrutura")
const data_inicial = document.querySelector("#data-inicial-id")
const data_final = document.querySelector("#data-final-id")
const input_codigo = document.querySelector("#codigo-produto-id")
const botao_buscar = document.querySelector("#botao-bomxop")
const codigo = gerarCodigoAleatorio(10, document.getElementById("codigo-identificador-id"))
const csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
const form_bomxop = document.getElementById("form-bomxop-id")

function evento_input_op() {
	input_op.value = input_op.value.replace(/[^0-9]/g, '');
	if (input_op.value === "") {
		datas.forEach((elemento) => {
			elemento.removeAttribute("readonly")
			elemento.style.backgroundColor = "white"
		})
		input_codigo.removeAttribute("readonly")
		input_codigo.style.backgroundColor = "white"
	} else {
		datas.forEach((elemento) => {
			elemento.setAttribute("readonly",true)
			elemento.style.backgroundColor = "lightgray"
		})
		input_codigo.setAttribute("readonly",true)
		input_codigo.style.backgroundColor = "lightgray"
	}
}

input_op.addEventListener("keyup",(e) => {
	if (/^[0-9]$/.test(e.key) || e.key === "Backspace" || e.key === "Delete") {
		evento_input_op()
		if (/^[0-9]$/.test(e.key) && e.target.value.length === 6) {
			e.target.value = `${e.target.value}01001`
		}
	}
})
input_op.addEventListener("change",() => {
	evento_input_op()
})

const ativa_input_op = () => {
	input_op.removeAttribute("readonly")
	input_op.style.backgroundColor = "white"
	input_codigo.removeAttribute("readonly")
	input_codigo.style.backgroundColor = "white"
}

function evento_datas() {
	if (data_inicial.value || data_final.value) {
		if (data_inicial.value[0] !== "0" && data_final.value[0] !== "0") {
			input_op.setAttribute("readonly",true)
			input_op.style.backgroundColor = "lightgray"
			input_codigo.setAttribute("readonly",true)
			input_codigo.style.backgroundColor = "lightgray"
		} else {
			ativa_input_op()
		}
	} else {ativa_input_op()}
}

datas.forEach((elemento) => {
	elemento.addEventListener("keyup",(e) => {
		if (/^[0-9]$/.test(e.key) || e.key === "Backspace" || e.key === "Delete") {
			evento_datas()
		}
	})
})

form_bomxop.addEventListener("submit", (e) => {
	if (input_op.value.length !== 11 && !data_final.value && !data_inicial.value) {
		// e.preventDefault()
		// alert("Dados inválidos")
	}
})

function evento_input_codigo() {
	if (input_codigo.value === "") {
		datas.forEach((elemento) => {
			elemento.removeAttribute("readonly")
			elemento.style.backgroundColor = "white"
		})
		input_op.removeAttribute("readonly")
		input_op.style.backgroundColor = "white"
	} else {
		datas.forEach((elemento) => {
			elemento.setAttribute("readonly",true)
			elemento.style.backgroundColor = "lightgray"
		})
		input_op.setAttribute("readonly",true)
		input_op.style.backgroundColor = "lightgray"
	}
}

input_codigo.addEventListener("keyup", (e) => {
	if (/^[a-zA-Z0-9]$/.test(e.key) || e.key === "Backspace" || e.key === "Delete") {
		input_codigo.value = input_codigo.value && input_codigo.value !== "" ? input_codigo.value.toUpperCase() : input_codigo.value
		evento_input_codigo()
	}
})
input_codigo.addEventListener("change", () => {
	evento_input_codigo()
})

form_bomxop.addEventListener("submit", () => {
	mostra_tela_aguarde(csrf, codigo, "bomxop")
})