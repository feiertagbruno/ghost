
const form = document.querySelector(".form-lista-de-falta")
const botao_mais = form.querySelector(".botao-mais-lista-de-falta")
const linhas_lista_de_falta = document.querySelector(".linhas-lista-de-falta")
let draggedItem = null

document.querySelector("label[for='codigo-1']").style.left = `${document.querySelector("#codigo-1").offsetLeft}px`
document.querySelector("label[for='mes-1']").style.left = `${document.querySelector("#mes-1").offsetLeft}px`
document.querySelector("label[for='quant-1']").style.left = `${document.querySelector("#quant-1").offsetLeft}px`

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

  linhas_lista_de_falta.append(nova_linha)
  codigo.focus()

  novo_botao.onclick = () => {
    adicionar_nova_linha()
  }

}
const plan = []
document.getElementById('fileInput').addEventListener('change', function(event) {
  const file = event.target.files[0];
  const reader = new FileReader();
  
  
  reader.onload = function(e) {
      const text = e.target.result;
      
      const linhas = text.split("\r\n")

      linhas.forEach(lin => {

        const infos = lin.split(";")
        
        if (infos[0]) {
          const linha_plan = []
          infos.forEach(info => {
            linha_plan.push(info)
          })
          plan.push(linha_plan)
        }

      })
      
      let contagem_ordem = 1
      const len_plan_0 = plan[0].length
      const len_plan = plan.length

      if (len_plan_0 > 3) {
        for (let i = 2; i < len_plan_0; i++) {
          for (let j = 1; j < len_plan; j++) {
            if (plan[j][i] > 0) {
              document.getElementById(`codigo-${contagem_ordem}`).value = plan[j][0]
              document.getElementById(`quant-${contagem_ordem}`).value = plan[j][i]
              const data = plan[0][i].split("/")
              document.getElementById(`mes-${contagem_ordem}`).value = `${data[2]}-${data[1]}`
              document.querySelector(".botao-mais-lista-de-falta").click()
              contagem_ordem ++
            }
          }
        }
      } else {
        plan.forEach(linha => {
          document.getElementById(`codigo-${contagem_ordem}`).value = linha[0]
          document.getElementById(`quant-${contagem_ordem}`).value = linha[1]
          const data = linha[2].split("/")
          document.getElementById(`mes-${contagem_ordem}`).value = `${data[2]}-${data[1]}`
          document.querySelector(".botao-mais-lista-de-falta").click()
          contagem_ordem ++
        })
      }


  };
  
  reader.readAsText(file);
});


//DRAG
linhas_lista_de_falta.addEventListener("dragstart", e => {
  if (e.target.classList.contains("linha-lista-de-falta")) {
    draggedItem = e.target
    e.target.style.opacity = "0.5"
  }
})

linhas_lista_de_falta.addEventListener("dragover", e => {
  e.preventDefault()

  const hovering = e.target.closest(".linha-lista-de-falta")
  if (hovering && hovering !== draggedItem) {
    let items = [...linhas_lista_de_falta.children]
    let draggedIndex = items.indexOf(draggedItem)
    let targetIndex = items.indexOf(hovering)

    if (draggedIndex < targetIndex) {
      hovering.after(draggedItem)
    } else {
      hovering.before(draggedItem)
    }

  }
})

linhas_lista_de_falta.addEventListener("dragend", e => {
  e.target.style.opacity = "1"
  atualizarOrdem()
})

function atualizarOrdem() {
  document.querySelectorAll(".linha-lista-de-falta").forEach((el, index) => {
    const i = index + 1
    el.querySelector("input[id*='ordem']").value = i
    el.querySelector("input[id*='ordem']").id = `ordem-${i}`
    el.querySelector("input[id*='codigo']").id = `codigo-${i}`
    el.querySelector("input[id*='quant']").id = `quant-${i}`
    el.querySelector("input[id*='mes']").id = `mes-${i}`
    
  });
}