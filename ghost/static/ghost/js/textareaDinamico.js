const textarea = document.getElementById('codigos-produtos-id');
textarea.addEventListener('input', () => {
	textarea.style.height = 'auto';
	textarea.style.height = (textarea.scrollHeight) + 'px';
});
