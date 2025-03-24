// @ts-check

const explode_pis = document.getElementById("explode-pis-id")

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