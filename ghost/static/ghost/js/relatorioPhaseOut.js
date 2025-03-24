// @ts-check
const botao_relatorio = document.querySelector(".botao-relatorio-phase-out")
const csrf = document.getElementById("")
const data_code = botao_relatorio?.getAttribute("data-code")

if (botao_relatorio) {
  // @ts-ignore
  botao_relatorio.onclick = e => {
    baixar_relatrio_phase_out()
  }
}

async function baixar_relatrio_phase_out() {
  const response = await fetch("/ghost/materiais/gerarrelatoriophaseout/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken()
    },
    body: JSON.stringify({
      codigo_aleatorio: data_code
    })
  })
  const blob = await response.blob()
  const file = new File([blob], `${data_code}.xlsx`, {type:blob.type})
  const url = window.URL.createObjectURL(file)

  window.location.href = url
  window.URL.revokeObjectURL(url)

}