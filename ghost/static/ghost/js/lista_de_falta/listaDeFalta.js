const form = document.querySelector(".form-lista-de-falta")
const botao_mais = form.querySelector(".botao-mais-lista-de-falta")

botao_mais.onclick = () => {
  adicionar_nova_linha()
}

function adicionar_nova_linha() {
  const linha = document.querySelector(".ultima-linha-lista-de-falta")
  const nova_linha = linha.cloneNode(true)
  const novo_botao = nova_linha.querySelector(".botao-mais-lista-de-falta")
  const ordem = nova_linha.querySelector("input[name='ordem']")
  const codigo = nova_linha.querySelector("input[name='codigo']")
  const quant = nova_linha.querySelector("input[name='quant']")
  const mes = nova_linha.querySelector("input[name='mes']")
  const labels = nova_linha.querySelectorAll("label")
  linha.querySelector(".botao-mais-lista-de-falta").remove()
  labels.forEach(el => {
    el.remove()
  })

  linha.classList.remove("ultima-linha-lista-de-falta")
  nova_linha.classList.add("ultima-linha-lista-de-falta")

  ordem_numero = Number(ordem.value) + 1 
  ordem.value = ordem_numero
  ordem.id = `ordem-${ordem_numero}`
  codigo.id = `codigo-${ordem_numero}`
  codigo.value = ""
  quant.id = `quant-${ordem_numero}`
  quant.value = ""
  mes.id = `mes-${ordem_numero}`

  form.append(nova_linha)
  codigo.focus()

  novo_botao.onclick = () => {
    adicionar_nova_linha()
  }

}
