const codigo_aleatorio = document.getElementById("codigo-aleatorio-id").value
const csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value

document.ondblclick = (el) => {
	if (el.target.tagName === "TD") {

		if (el.target.querySelector("input[type='text']")) return
		
		const unique = el.target.getAttribute("data-unique")
		console.dir(el.target)
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
	}
}

async function salva_valor_no_bd(codigo_aleatorio, unique, novo_valor, el, input) {
	const response = await fetch("/alterasimuladordeproducao/", {
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
		console.log("sucesso")
		el.innerText = novo_valor
		input.remove()
	} else {
		console.log(data.erro)
	}
}