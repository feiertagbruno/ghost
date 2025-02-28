const codigo_aleatorio = document.getElementById("codigo-aleatorio-id").value
const form_tabela_simulador = document.getElementById("form-tabela-simulador-id")
const btn_salvar_simulacao = document.getElementById("salvar-simulacao-id")
const nome_da_simulacao = form_tabela_simulador.querySelector("#nome-da-simulacao-id")


document.ondblclick = (el) => {
	if (el.target.tagName === "TD") {

		if (el.target.querySelector("input[type='text']")) return
		
		const unique = el.target.getAttribute("data-unique")
		
		const campos_alteraveis = JSON.parse(document.getElementById("campos-alteraveis-id").value)
		const nome_campo = unique.split("|")[0].split("xxx")[2]

		if (!campos_alteraveis.includes(nome_campo)) {
			pisca_elemento_em_vermelho(el.target)
			return
		}

		const valor = el.target.innerText
		const input_valor = document.createElement("input")
		input_valor.type = "text"
		input_valor.value = valor
		el.target.append(input_valor)
		input_valor.focus()
		input_valor.onkeyup = (e) => {
			if (e.key === "Enter") {
				salva_valor_no_bd(codigo_aleatorio, unique, input_valor.value, el.target, input_valor)
			} else if (e.key === "Escape") {
				input_valor.remove()
			}
		}
		input_valor.onblur = () => input_valor.remove()
	}
}

async function salva_valor_no_bd(codigo_aleatorio, unique, novo_valor, el, input) {
	const response = await fetch("/ghost/materiais/alterasimuladordeproducao/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf
    },
    body: JSON.stringify({
			codigo_aleatorio: codigo_aleatorio,
			unique: unique,
			novo_valor: novo_valor
		})
  })
	const data = await response.json()
	if (data.sucesso) {
		el.innerText = novo_valor
		input.remove()
	} else {
		console.log(data.erro)
	}
}

btn_salvar_simulacao.onclick = e => {
	e.preventDefault()
	if (nome_da_simulacao.value) {
		const mensagem_tabela_simulador = document.querySelector(".mensagem-tabela-simulador")
		if ('0123456789'.includes(nome_da_simulacao.value.slice(0,1))) {
			add_msg_mensagem_tabela_simulador(
				mensagem_tabela_simulador, 
				"O primeiro dígito do nome não pode ser um número", 
				"color-vermelho"
			)
			return
		}
		mensagem_tabela_simulador.classList.add("hidden")
		
		
		salvar_simulacao(codigo_aleatorio, nome_da_simulacao, mensagem_tabela_simulador)

	} else {
		nome_da_simulacao.classList.add("background-vermelho-claro")
		nome_da_simulacao.classList.add("transition-500")
		setTimeout(() => nome_da_simulacao.classList.remove("background-vermelho-claro"),500)
	}
}

async function salvar_simulacao(codigo_aleatorio, nome_da_simulacao, mensagem_tabela_simulador) {
	try {
		const response = await fetch("/ghost/materiais/salvarsimulacao/", {
			method:"POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": csrf
			},
			body: JSON.stringify({
				codigo_aleatorio: codigo_aleatorio,
				nome_da_simulacao: nome_da_simulacao.value.trim()
			})
		})
		const data = await response.json()

		if (data.sucesso) {
			add_msg_mensagem_tabela_simulador(
				mensagem_tabela_simulador, "Simulação salva.", "color-verde"
			)
			finalizacao_salvar_tabela(nome_da_simulacao)
			
			return
		} else {
			add_msg_mensagem_tabela_simulador(mensagem_tabela_simulador, data.erro, "color-vermelho")
			return
		}

	} catch {
		add_msg_mensagem_tabela_simulador(
			mensagem_tabela_simulador, "A simulação não foi salva", "color-vermelho"
		)
		return
	}

}
function finalizacao_salvar_tabela(nome_da_simulacao) {
	// nome_da_simulacao.setAttribute("readOnly", true)
	nome_da_simulacao.classList.remove("background-amarelo")
	nome_da_simulacao.classList.add("background-verde")
	document.getElementById("tabela-salva-id").value = nome_da_simulacao.value.trim()
	btn_salvar_simulacao.setAttribute("disabled", true)
	btn_salvar_simulacao.style.cursor = "default"
	btn_salvar_simulacao.style.backgroundColor = "white"
	btn_salvar_simulacao.style.color = "lightgray"
}


function add_msg_mensagem_tabela_simulador(mensagem_tabela_simulador, mensagem, classe) {
	mensagem_tabela_simulador.textContent = mensagem
	mensagem_tabela_simulador.classList.remove("hidden")
	mensagem_tabela_simulador.classList.add(classe)
}

document.addEventListener("DOMContentLoaded", ()=> {
	if (nome_da_simulacao.value) {
		nome_da_simulacao.setAttribute("readOnly", true)
		nome_da_simulacao.classList.add("background-amarelo")
	}

	let offset = 0
	let i = 0
	document.querySelectorAll(".fixed-left-col").forEach(cell => {

		cell.style.left = `${offset}px`
		offset += cell.getBoundingClientRect().width
		i ++
		if (i === 3) {
			offset = 0
			i = 0
		}
	})

})

function pisca_elemento_em_vermelho(el) {
	
	let bck = ''
	el.classList.forEach(c => {
		try {
			if (c.includes("background")) {
				bck = c
				el.classList.remove(c)
			}
		} catch {true}
	})

	const bck_style = el.style.background

	el.classList.add("background-vermelho-claro")
	el.classList.add("transition-500")
	setTimeout(() => {
		el.classList.remove("background-vermelho-claro")
		if (bck !== '') {
			el.classList.add(bck)
		} else if (bck_style !== '') {
			el.style.background = bck_style
		}
	},300)
//el.classList.remove("background-vermelho-claro")
}