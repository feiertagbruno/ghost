// @ts-check

const abre_detalhamento = document.getElementById("abre-detalhamento-id")
const explode_pis = document.getElementById("explode-pis-id")

if (abre_detalhamento) {
  abre_detalhamento.onchange = el => {
      // @ts-ignore
      if (el.target.checked) {
        document.cookie = "abre_detalhamento_phase_out=true;path=/"
      } else {
        document.cookie = "abre_detalhamento_phase_out=false;path=/"
      }
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
  const cookie_abre_detalhamento_phase_out = getCookie("abre_detalhamento_phase_out")
  const cookie_explode_pis_phase_out = getCookie("explode_pis_phase_out")

  if (cookie_abre_detalhamento_phase_out && cookie_abre_detalhamento_phase_out === "true") {
    abre_detalhamento?.setAttribute("checked","true")
  } else if (cookie_abre_detalhamento_phase_out && cookie_abre_detalhamento_phase_out === "false") {
    abre_detalhamento?.removeAttribute("checked")
  }

  if (cookie_explode_pis_phase_out && cookie_explode_pis_phase_out === "true") {
    explode_pis?.setAttribute("checked","true")
  } else if (cookie_explode_pis_phase_out && cookie_explode_pis_phase_out === "false") {
    explode_pis?.removeAttribute("checked")
  }

})