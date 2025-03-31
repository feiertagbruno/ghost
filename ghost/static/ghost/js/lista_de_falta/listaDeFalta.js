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

document.getElementById('fileInput').addEventListener('change', function(event) {
  const file = event.target.files[0];
  const reader = new FileReader();
  const plan = []
  
  reader.onload = function(e) {
      const text = e.target.result;
      console.log(text); // Aqui você pode processar o CSV
      const linhas = text.split("\r\n")
      linhas.forEach(lin => {
        const infos = lin.split(";")
        console.log(infos)
        if (infos[0]) {
          const linha_plan = []
          infos.forEach(info => {
            linha_plan.push(info)
          })
          plan.push(linha_plan)
        }
      })
      console.log(plan)
  };
  
  reader.readAsText(file);
});
