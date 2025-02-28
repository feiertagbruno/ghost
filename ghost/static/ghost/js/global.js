function getCookie(name) {
	let cookies = document.cookie.split("; ");
	for (let cookie of cookies) {
			let [chave, valor] = cookie.split("=");
			if (chave === name) return valor;
	}
	return null;
}