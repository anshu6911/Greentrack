const API_BASE = '';

const showAlert = (message, type = 'error') => {
    const container = document.getElementById('auth-alert');
    if (!container) return;
    if (!message) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = `<div class="alert alert-${type === 'success' ? 'success' : 'error'}">${message}</div>`;
};

document.addEventListener('DOMContentLoaded', () => {
    // apply theme from main.js helpers if available
    if (typeof initTheme === 'function') {
        initTheme();
    }

    const tabButtons = document.querySelectorAll('.tab-button');
    const forms = {
        'login-form': document.getElementById('login-form'),
        'register-form': document.getElementById('register-form')
    };

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            Object.values(forms).forEach(form => form.style.display = 'none');
            const target = btn.getAttribute('data-form');
            forms[target].style.display = 'block';
            showAlert('');
        });
    });

    forms['login-form'].addEventListener('submit', async e => {
        e.preventDefault();

        try {
            const response = await fetch(`${API_BASE}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    email: document.getElementById('login-email').value,
                    password: document.getElementById('login-password').value,
                })
            });

            const data = await response.json();

            if (!response.ok) {
                showAlert(data.error || 'Login failed');
                return;
            }

            showAlert('Login successful! Redirecting...', 'success');
            setTimeout(() => window.location.href = 'dashboard.html', 800);
        } catch (error) {
            showAlert('Server error. Please try again.');
        }
    });

    forms['register-form'].addEventListener('submit', async e => {
        e.preventDefault();

        try {
            const response = await fetch(`${API_BASE}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    name: document.getElementById('register-name').value,
                    email: document.getElementById('register-email').value,
                    password: document.getElementById('register-password').value,
                    role: document.getElementById('register-role').value,
                })
            });

            const data = await response.json();

            if (!response.ok) {
                showAlert(data.error || 'Registration failed');
                return;
            }

            showAlert('Registration successful! You can now sign in.', 'success');
            document.querySelector('[data-form="login-form"]').click();
        } catch (error) {
            showAlert('Server error. Please try again.');
        }
    });

    // Pre-select form based on query params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('action') === 'register') {
        document.querySelector('[data-form="register-form"]').click();
        const role = urlParams.get('role');
        if (role) document.getElementById('register-role').value = role;
    }
});

