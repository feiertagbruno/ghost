function getCookie(name) {
	let cookies = document.cookie.split("; ");
	for (let cookie of cookies) {
			let [chave, valor] = cookie.split("=");
			if (chave === name) return valor;
	}
	return null;
}


function getTodayDate() {
	const today = new Date();
	return today.toISOString().split("T")[0];
}
