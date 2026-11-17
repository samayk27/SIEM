document.getElementById('signup-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const error = document.getElementById('signup-error');
  const response = await fetch('/api/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      display_name: document.getElementById('display-name').value,
      username: document.getElementById('username').value,
      department: document.getElementById('department').value,
      password: document.getElementById('password').value,
    }),
  });
  if (!response.ok) {
    error.textContent = (await response.json()).error || 'Unable to create account';
    error.classList.remove('hidden');
    return;
  }
  window.location.replace('/workspace');
});
