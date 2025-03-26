// @ts-check

const explode_pis = document.getElementById("explode-pis-id")
const botao_carregar = document.getElementById("botao-multi-simples")
let codigo_processamento = getCookie("codigo_identificador")
const csrf = getCSRFToken()

console.log(getCookie("codigo_identificador"))

if (!codigo_processamento) {
  codigo_processamento = gerarCodigoAleatorio(10, document.getElementsByName("codigo-identificador"))
  document.cookie = `codigo_identificador=${codigo_processamento}`
} else {
  const campos_codigo_identificador = document.getElementsByName("codigo-identificador")
  
  if (campos_codigo_identificador.length > 0) {
    campos_codigo_identificador.forEach(el => {
      // @ts-ignore
      el.value = codigo_processamento
    })
  }
}

if (explode_pis) {
  explode_pis.onchange = el => {
    // @ts-ignore
    if (el.target.checked) {
      document.cookie = "explode_pis_phase_out=true;path=/"
    } else {
      document.cookie = "explode_pis_phase_out=false;path=/"
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // @ts-ignore
  const cookie_explode_pis_phase_out = getCookie("explode_pis_phase_out")

  if (cookie_explode_pis_phase_out && cookie_explode_pis_phase_out === "true") {
    explode_pis?.setAttribute("checked","true")
  } else if (cookie_explode_pis_phase_out && cookie_explode_pis_phase_out === "false") {
    explode_pis?.removeAttribute("checked")
  }

})

if (botao_carregar) {
  botao_carregar.onclick = () => {
    mostra_tela_aguarde(csrf, codigo_processamento, "phase_out")
  }
}
