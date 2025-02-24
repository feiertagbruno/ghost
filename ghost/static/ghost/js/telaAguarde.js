let tentativa = 0

function getRandomMudaTexto() {
	let num;
	do {
			num = Math.floor(Math.random() * 80);
	} while (num >= 30 && num <= 50); 
	return num +10;
}

function muda_texto_tela_aguarde(tela_aguarde) {
	const texto = document.querySelector(".texto-tela-aguarde")
	if (texto) texto.remove()

	const texto_tela_aguarde = document.createElement("div")
	texto_tela_aguarde.classList.add("texto-tela-aguarde")

	const vermelho_ou_branco = (Math.floor(Math.random() * 101) <= 50) ? "rgb(192,0,0)" : "white"
	
	texto_tela_aguarde.innerText = "Gama Italy"
	texto_tela_aguarde.style.position = "fixed"
	texto_tela_aguarde.style.color = vermelho_ou_branco
	texto_tela_aguarde.style.fontSize = "2rem"
	texto_tela_aguarde.style.width = "fit-content"
	texto_tela_aguarde.style.top = `${getRandomMudaTexto()}%`
	texto_tela_aguarde.style.left = `${getRandomMudaTexto()}%`
	texto_tela_aguarde.style.transform = "translate(-50%,-50%)"
	tela_aguarde.append(texto_tela_aguarde)

	setTimeout(muda_texto_tela_aguarde,2000,tela_aguarde)
}

function gerarCodigoAleatorio(tamanho, elemento) {
  const caracteres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let codigo = '';
  for (let i = 0; i < tamanho; i++) {
      const indice = Math.floor(Math.random() * caracteres.length);
      codigo += caracteres[indice];
  }
	elemento.value = codigo
  return codigo;
}

function formata_tela_aguarde(tela_aguarde) {
	tela_aguarde.id = "tela-aguarde"
	tela_aguarde.style.width = "100vw"
	tela_aguarde.style.height = "100vh"
	tela_aguarde.style.background = "rgba(0, 0, 0, 0.7)"
	tela_aguarde.style.position = "fixed"
	tela_aguarde.style.top = "0"
	tela_aguarde.style.left = "0"
	tela_aguarde.style.color = "white"
	tela_aguarde.style.fontSize = "2rem"
	tela_aguarde.style.display = "flex"
	tela_aguarde.style.flexFlow = "column"
	tela_aguarde.style.justifyContent = "center"
	tela_aguarde.style.alignItems = "center"

	return tela_aguarde
}

function formata_elemento_tela_aguarde(elemento) {
	elemento.style.color = "white"
	elemento.style.fontSize = "2rem"

	return elemento
}

async function buscar_processamento(tela_aguarde, porcentagem, mensagem1, mensagem2, csrf, codigo, caller) {
	try {
		const response = await fetch("/buscarprocessamento/", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": csrf,
			},
			body: JSON.stringify({
				"codigo_identificador": codigo,
				"caller": caller,
			})
		})
		const data = await response.json()

		porcentagem.innerHTML = `<strong>${data.porcentagem}</strong>`
		mensagem1.innerText = data.mensagem1
		mensagem2.innerText = data.mensagem2

	} catch {
		tentativa ++
	}

	if (tentativa <= 3) {
		setTimeout(buscar_processamento, 300,tela_aguarde, porcentagem, mensagem1, mensagem2, csrf, codigo, caller)
	}

}

function mostra_tela_aguarde(csrf, codigo, caller) {

	let tela_aguarde = document.createElement("div")
	tela_aguarde = formata_tela_aguarde(tela_aguarde)	
	document.body.append(tela_aguarde)

	let porcentagem = document.createElement("div")
	porcentagem = formata_elemento_tela_aguarde(porcentagem)
	let mensagem1 = document.createElement("div")
	mensagem1 = formata_elemento_tela_aguarde(mensagem1)
	let mensagem2 = document.createElement("div")
	mensagem2 = formata_elemento_tela_aguarde(mensagem2)

	tela_aguarde.append(porcentagem)
	tela_aguarde.append(mensagem1)
	tela_aguarde.append(mensagem2)

	muda_texto_tela_aguarde(tela_aguarde)
	setTimeout(buscar_processamento,500, tela_aguarde, porcentagem, mensagem1, mensagem2, csrf, codigo, caller)

}

function remove_texto_tela_aguarde() {
	tela_aguarde.remove()
}
/**
 * 
 * @param {"message-error" | "message-info" | "message-success"} style 
 */
function mensagem_padrao(style, mensagem) {
	const mensagem_padrao = document.createElement("div")
	mensagem_padrao.textContent = mensagem
	mensagem_padrao.classList.add("message")
	mensagem_padrao.classList.add(style)
	document.querySelector(".linha-logo").insertAdjacentElement("afterend",mensagem_padrao)
}