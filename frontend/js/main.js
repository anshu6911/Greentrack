const THEME_KEY = 'greentrack-theme';

const applyTheme = (theme) => {
    const root = document.documentElement;
    const value = theme === 'dark' ? 'dark' : 'light';
    if (value === 'dark') {
        root.setAttribute('data-theme', 'dark');
    } else {
        root.removeAttribute('data-theme');
    }

    const toggles = document.querySelectorAll('.theme-toggle');
    toggles.forEach(btn => {
        const icon = btn.querySelector('i');
        const label = btn.querySelector('span');
        if (!icon || !label) return;

        if (value === 'dark') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            label.textContent = 'Light';
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            label.textContent = 'Dark';
        }
    });
};

const initTheme = () => {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) {
        applyTheme(stored);
        return;
    }

    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(prefersDark ? 'dark' : 'light');
};

document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    const previewTabs = document.querySelectorAll('.preview-tab');
    const previewPanels = document.querySelectorAll('.preview-panel');

    previewTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            previewTabs.forEach(t => t.classList.remove('active'));
            previewPanels.forEach(panel => panel.classList.remove('active'));

            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            const panel = document.getElementById(target);
            if (panel) panel.classList.add('active');
        });
    });

    document.body.addEventListener('click', (event) => {
        const btn = event.target.closest('.theme-toggle');
        if (!btn) return;

        const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem(THEME_KEY, next);
        applyTheme(next);
    });
});

