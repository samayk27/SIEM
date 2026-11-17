const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const response = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: document.getElementById('login-username').value,
      password: document.getElementById('login-password').value,
    }),
  });
  if (!response.ok) {
    const data = await response.json();
    loginError.textContent = data.error || 'Unable to sign in';
    loginError.classList.remove('hidden');
    return;
  }
  window.location.replace('/workspace');
});
