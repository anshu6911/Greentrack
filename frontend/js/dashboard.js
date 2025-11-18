const API_BASE = window.location.port === '8000'
    ? 'http://127.0.0.1:5000'
    : '';

const state = {
    user: null,
    volunteers: [],
    filters: {
        status: '',
        category: '',
        q: ''
    }
};

const accessMatrix = {
    citizen: ['citizen'],
    volunteer: ['citizen', 'volunteer'],
    moderator: ['citizen', 'volunteer', 'moderator', 'admin'],
    admin: ['citizen', 'volunteer', 'moderator', 'admin']
};

const defaultTabs = {
    citizen: 'citizen',
    volunteer: 'volunteer',
    moderator: 'moderator',
    admin: 'admin'
};

const escapeHtml = (value = '') =>
    value
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

const setAlert = (message = '', type = 'success') => {
    const container = document.getElementById('dashboard-alert');
    if (!container) return;
    if (!message) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = `<div class="alert ${type === 'error' ? 'alert-error' : 'alert-success'}">${message}</div>`;
    if (type !== 'error') {
        setTimeout(() => (container.innerHTML = ''), 4000);
    }
};

const fetchWithAuth = async (url, options = {}) => {
    const response = await fetch(`${API_BASE}${url}`, {
        credentials: 'include',
        ...options
    });

    if (response.status === 401) {
        window.location.href = 'auth.html';
        throw new Error('Please sign in again.');
    }

    let data = {};
    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }

    if (!response.ok) {
        throw new Error(data.error || 'Request failed');
    }
    return data;
};

const renderReports = (reports = []) => {
    const container = document.getElementById('my-reports');
    if (!container) return;

    if (!reports.length) {
        container.innerHTML = '<p>No reports yet. Submit your first issue to get started.</p>';
        return;
    }

    container.innerHTML = reports
        .map(report => `
            <div class="report-card card">
                <div class="report-header">
                    <h4>${escapeHtml(report.category)}</h4>
                    <span class="status-badge status-${report.status?.toLowerCase() || 'pending'}">
                        ${escapeHtml(report.status?.replace('_', ' ') || 'Pending')}
                    </span>
                </div>
                <p>${escapeHtml(report.description)}</p>
                <p><strong>Location:</strong> ${escapeHtml(report.location_text)}</p>
                <p><strong>Severity:</strong> ${escapeHtml(report.severity)}</p>
                ${report.moderator_notes ? `<p><strong>Moderator Notes:</strong> ${escapeHtml(report.moderator_notes)}</p>` : ''}
                ${report.photo_path ? `<img src="../${report.photo_path}" class="photo-thumb" alt="Report photo">` : ''}
            </div>
        `)
        .join('');
};

const renderRewards = (data) => {
    const container = document.getElementById('citizen-rewards');
    if (!container) return;

    if (!data) {
        container.innerHTML = '<p>Rewards data is not available right now.</p>';
        return;
    }

    const completedCount = data.valid_reports || 0;
    const rewards = Array.isArray(data.rewards) ? data.rewards : [];
    const nextTier = data.next_tier || null;

    const parts = [];

    parts.push(`<p><strong>Completed reports:</strong> ${completedCount}</p>`);

    if (nextTier) {
        const remaining = Math.max(0, nextTier.threshold - completedCount);
        parts.push(
            `<p style="color:var(--muted);">` +
            (remaining > 0
                ? `Only ${remaining} more completed photo reports to unlock a reward from <strong>${escapeHtml(nextTier.brand)}</strong>.`
                : `You are eligible for the next reward tier from <strong>${escapeHtml(nextTier.brand)}</strong>.`)
            + `</p>`
        );
    } else {
        parts.push('<p style="color:var(--muted);">You have unlocked all available reward tiers for now. Thank you for keeping your city clean!</p>');
    }

    if (!rewards.length) {
        parts.push('<p>No rewards unlocked yet. Complete photo-backed cleanup reports to earn discount codes from Swiggy, Zomato, Blinkit, Ola, Uber, KFC, Domino\'s and more.</p>');
    } else {
        const items = rewards
            .map(r => {
                const brand = r.brand || '';
                const initial = brand.charAt(0).toUpperCase() || '?';
                const brandColors = {
                    'Swiggy': '#F26D21',
                    'Zomato': '#E23744',
                    'Blinkit': '#2AC74F',
                    'Ola': '#000000',
                    'Uber': '#000000',
                    'KFC': '#E4002B',
                    "Domino's": '#006491'
                };
                const bg = brandColors[brand] || '#2563eb';

                return `
                <li class="hotspot-item" style="display:flex;flex-direction:column;gap:0.35rem;align-items:flex-start;">
                    <div style="display:flex;align-items:center;gap:0.75rem;width:100%;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:0.75rem;">
                            <div style="width:36px;height:36px;border-radius:999px;background:${bg};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;flex-shrink:0;">
                                ${escapeHtml(initial)}
                            </div>
                            <div>
                                <div style="font-weight:600;">${escapeHtml(brand)}</div>
                                <div style="font-size:0.85rem;color:var(--muted);">${escapeHtml(r.description || '')}</div>
                            </div>
                        </div>
                        <button class="btn btn-secondary reward-reveal" data-code="${escapeHtml(r.code)}">Tap to reveal</button>
                    </div>
                </li>
            `;
            })
            .join('');
        parts.push(`<ul class="hotspot-list">${items}</ul>`);
    }

    container.innerHTML = parts.join('');

    const buttons = container.querySelectorAll('.reward-reveal');
    buttons.forEach(btn => {
        const code = btn.getAttribute('data-code') || '';
        btn.addEventListener('click', () => {
            if (!code) return;
            btn.textContent = code;
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        }, { once: true });
    });
};

const renderTaskList = (tasks = [], selector, type = 'available') => {
    const container = document.querySelector(selector);
    if (!container) return;

    if (!tasks.length) {
        container.innerHTML = type === 'available'
            ? '<p>No open tasks right now. Check back soon!</p>'
            : '<p>No assigned tasks yet.</p>';
        return;
    }

    container.innerHTML = tasks
        .map(task => {
            const rawStatus = task.task_status || task.status || '';
            const status = rawStatus.toLowerCase();
            const statusLabel = rawStatus.replace('_', ' ');
            const reportPhoto = task.photo_path;
            const proofPhoto = task.proof_photo_path;

            const actions = type === 'available'
                ? `<button class="btn btn-secondary" data-task-id="${task.task_id}" data-action="claim">Claim Task</button>`
                : status === 'completed'
                    ? '<p style="margin-top:0.75rem;color:var(--muted);">Proof uploaded. This task is completed.</p>'
                    : `
                        <div class="task-actions">
                            <button class="btn btn-primary" data-task-id="${task.task_id}" data-action="start">In Progress</button>
                            <button class="btn btn-outline" data-task-id="${task.task_id}" data-action="complete">Upload Proof</button>
                        </div>
                    `;

            return `
            <div class="task-card card">
                <div class="report-header">
                    <h4>${escapeHtml(task.category)}</h4>
                    <span class="status-badge status-${status}">
                        ${escapeHtml(statusLabel)}
                    </span>
                </div>
                <p>${escapeHtml(task.description)}</p>
                <p><strong>Location:</strong> ${escapeHtml(task.location_text)}</p>
                <p><strong>Severity:</strong> ${escapeHtml(task.severity || 'n/a')}</p>
                ${reportPhoto ? `<p style="margin-top:0.5rem;font-size:0.85rem;color:var(--muted);">Report photo:</p><img src="../${reportPhoto}" class="photo-thumb" alt="Report photo">` : ''}
                ${proofPhoto ? `<p style="margin-top:0.5rem;font-size:0.85rem;color:var(--muted);">Proof photo:</p><img src="../${proofPhoto}" class="photo-thumb" alt="Proof photo">` : ''}
                ${actions}
            </div>
        `;
        })
        .join('');
};

const renderPendingReports = (reports = []) => {
    const container = document.getElementById('pending-reports');
    if (!container) return;

    if (!reports.length) {
        container.innerHTML = '<p>All caught up! No pending reports.</p>';
        return;
    }

    container.innerHTML = reports
        .map(report => `
            <div class="card" data-report="${report.id}">
                <div class="report-header">
                    <h4>${escapeHtml(report.category)}</h4>
                    <span class="badge">${escapeHtml(report.severity)}</span>
                </div>
                ${report.photo_path ? `<img src="../${report.photo_path}" alt="Evidence" style="width:100%;height:220px;object-fit:cover;border-radius:12px;margin:1rem 0;">` : ''}
                <p>${escapeHtml(report.description)}</p>
                <p><strong>Location:</strong> ${escapeHtml(report.location_text)}</p>
                <p><strong>Citizen:</strong> ${escapeHtml(report.citizen_name)} (${escapeHtml(report.citizen_email)})</p>
                <textarea class="form-control" rows="2" data-notes="${report.id}" placeholder="Add moderator notes"></textarea>
                <div class="task-actions">
                    <button class="btn btn-primary" data-action="validate" data-valid="true" data-report-id="${report.id}">Mark Valid</button>
                    <button class="btn btn-outline" data-action="validate" data-valid="false" data-report-id="${report.id}">Mark Invalid</button>
                </div>
            </div>
        `)
        .join('');
};

const renderGlobalTasks = (tasks = []) => {
    const container = document.getElementById('global-tasks');
    if (!container) return;

    if (!tasks.length) {
        container.innerHTML = '<p>No tasks match the current filters.</p>';
        return;
    }

    const rows = tasks
        .map(task => `
            <tr>
                <td>#${task.task_id}</td>
                <td>${escapeHtml(task.category)}</td>
                <td>${escapeHtml(task.status.replace('_', ' '))}</td>
                <td>${escapeHtml(task.location_text)}</td>
                <td>${escapeHtml(task.volunteer_name || 'Unassigned')}</td>
            </tr>
        `)
        .join('');

    container.innerHTML = `
        <div class="table-wrapper">
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Location</th>
                        <th>Volunteer</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
};

const renderAnalytics = stats => {
    const statsContainer = document.getElementById('admin-stats');
    const hotspotsContainer = document.getElementById('admin-hotspots');
    if (!statsContainer || !hotspotsContainer) return;

    statsContainer.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${stats.total_reports}</div>
            <div class="stat-label">Total Reports</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.valid_reports}</div>
            <div class="stat-label">Verified Reports</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.completed_tasks}</div>
            <div class="stat-label">Tasks Completed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.volunteers_count}</div>
            <div class="stat-label">Volunteers</div>
        </div>
    `;

    hotspotsContainer.innerHTML = stats.hotspots.length
        ? stats.hotspots
            .map(h => `<li class="hotspot-item"><span>${escapeHtml(h.location)}</span><strong>${h.count}</strong></li>`)
            .join('')
        : '<li>No hotspots identified yet.</li>';
};

const populateVolunteerSelect = () => {
    const select = document.getElementById('assign-volunteer-id');
    if (!select) return;
    select.innerHTML = '<option value="" disabled selected>Choose volunteer</option>' +
        state.volunteers.map(vol => `<option value="${vol.id}">${escapeHtml(vol.name)} (${escapeHtml(vol.email)})</option>`).join('');
};

const handleTaskAction = async (taskId, action) => {
    try {
        if (action === 'complete') {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = async () => {
                if (!input.files.length) return;
                const formData = new FormData();
                formData.append('proof_photo', input.files[0]);
                formData.append('notes', 'Cleanup proof uploaded via dashboard.');
                await fetchWithAuth(`/api/tasks/${taskId}/complete`, {
                    method: 'POST',
                    body: formData
                });
                setAlert('Task marked as completed!', 'success');
                refreshDataByRole();
            };
            input.click();
            return;
        }

        const endpoints = {
            claim: `/api/tasks/${taskId}/claim`,
            start: `/api/tasks/${taskId}/start`
        };

        await fetchWithAuth(endpoints[action], { method: 'POST' });
        setAlert(`Task ${action === 'start' ? 'progress updated' : 'claimed'} successfully.`, 'success');
        refreshDataByRole();
    } catch (error) {
        setAlert(error.message, 'error');
    }
};

const setupTaskButtons = () => {
    ['available-tasks', 'my-tasks'].forEach(id => {
        const container = document.getElementById(id);
        if (!container) return;
        container.addEventListener('click', event => {
            const button = event.target.closest('[data-task-id]');
            if (!button) return;
            handleTaskAction(button.dataset.taskId, button.dataset.action);
        });
    });
};

const setupModeratorActions = () => {
    const pendingContainer = document.getElementById('pending-reports');
    if (pendingContainer) {
        pendingContainer.addEventListener('click', async event => {
            const button = event.target.closest('[data-action="validate"]');
            if (!button) return;
            const reportId = button.dataset.reportId;
            const isValid = button.dataset.valid === 'true';
            const notesField = pendingContainer.querySelector(`[data-notes="${reportId}"]`);
            const notes = notesField ? notesField.value : '';
            try {
                await fetchWithAuth(`/api/reports/${reportId}/validate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_valid: isValid, notes })
                });
                setAlert(`Report ${isValid ? 'validated' : 'marked invalid'}.`, 'success');
                refreshDataByRole();
            } catch (error) {
                setAlert(error.message, 'error');
            }
        });
    }

    const assignForm = document.getElementById('assign-form');
    if (assignForm) {
        assignForm.addEventListener('submit', async event => {
            event.preventDefault();
            const reportId = document.getElementById('assign-report-id').value;
            const volunteerId = document.getElementById('assign-volunteer-id').value;
            if (!reportId || !volunteerId) {
                setAlert('Please choose both report and volunteer.', 'error');
                return;
            }
            try {
                await fetchWithAuth(`/api/reports/${reportId}/assign`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ volunteer_id: Number(volunteerId) })
                });
                setAlert('Task assigned successfully.', 'success');
                assignForm.reset();
                populateVolunteerSelect();
                refreshDataByRole();
            } catch (error) {
                setAlert(error.message, 'error');
            }
        });
    }

    const filterForm = document.getElementById('task-filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', event => {
            event.preventDefault();
            state.filters.status = document.getElementById('filter-status').value;
            state.filters.category = document.getElementById('filter-category').value;
            state.filters.q = document.getElementById('filter-query').value;
            loadGlobalTasks();
        });
    }
};

const setupReportForm = () => {
    const form = document.getElementById('report-form');
    if (!form) return;

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const photo = document.getElementById('report-photo').files[0];
        if (!photo) {
            setAlert('Please attach a photo.', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('category', document.getElementById('report-category').value);
        formData.append('description', document.getElementById('report-description').value);
        formData.append('location_text', document.getElementById('report-location').value);
        formData.append('severity', document.getElementById('report-severity').value);
        formData.append('latitude', document.getElementById('report-latitude').value);
        formData.append('longitude', document.getElementById('report-longitude').value);
        formData.append('is_anonymous', document.getElementById('report-anonymous').checked);
        formData.append('photo', photo);

        try {
            await fetchWithAuth('/api/reports', { method: 'POST', body: formData });
            setAlert('Report submitted successfully.', 'success');
            form.reset();
            refreshDataByRole();
        } catch (error) {
            setAlert(error.message, 'error');
        }
    });
};

const loadCitizenData = () => fetchWithAuth('/api/reports/my').then(renderReports).catch(() => {});
const loadRewards = () => fetchWithAuth('/api/rewards').then(renderRewards).catch(() => {});
const loadAvailableTasks = () => fetchWithAuth(`/api/tasks/available?q=${encodeURIComponent(document.getElementById('available-search')?.value || '')}`).then(data => renderTaskList(data, '#available-tasks', 'available')).catch(() => {});
const loadMyTasks = () => fetchWithAuth('/api/tasks/my').then(data => renderTaskList(data, '#my-tasks', 'mine')).catch(() => {});
const loadPendingReports = () => fetchWithAuth('/api/reports/pending').then(renderPendingReports).catch(() => {});
const loadVolunteers = () => fetchWithAuth('/api/users/volunteers').then(list => { state.volunteers = list; populateVolunteerSelect(); });
const loadGlobalTasks = () => {
    const query = new URLSearchParams(state.filters);
    return fetchWithAuth(`/api/tasks/manage?${query.toString()}`).then(renderGlobalTasks).catch(() => {});
};
const loadAnalytics = () => fetchWithAuth('/api/stats').then(renderAnalytics).catch(() => {});

const refreshDataByRole = () => {
    loadCitizenData();
    loadRewards();
    if (['volunteer', 'admin'].includes(state.user.role)) {
        loadAvailableTasks();
        loadMyTasks();
    }
    if (['moderator', 'admin'].includes(state.user.role)) {
        loadPendingReports();
        loadVolunteers();
        loadGlobalTasks();
        loadAnalytics();
    }
};

const handleTabChange = role => {
    if (!state.user) return;
    const allowed = accessMatrix[state.user.role] || ['citizen'];
    if (!allowed.includes(role)) {
        setAlert('Access restricted for your role.', 'error');
        return;
    }

    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.toggle('active', btn.dataset.role === role));
    document.querySelectorAll('.tab-content').forEach(section => section.classList.toggle('active', section.id === `${role}-section`));
};

const initTabs = () => {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => handleTabChange(button.dataset.role));
    });
};

const setupLogout = () => {
    const logoutBtn = document.getElementById('logout-btn');
    if (!logoutBtn) return;
    logoutBtn.addEventListener('click', async () => {
        await fetchWithAuth('/api/logout', { method: 'POST' });
        window.location.href = 'auth.html';
    });
};

const initSearchDebounce = () => {
    const searchInput = document.getElementById('available-search');
    if (!searchInput) return;
    let timeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => loadAvailableTasks(), 400);
    });
};

const initDashboard = async () => {
    try {
        setupLogout();
        setupTaskButtons();
        setupModeratorActions();
        setupReportForm();
        initTabs();
        initSearchDebounce();

        const user = await fetchWithAuth('/api/me');
        state.user = user;
        document.getElementById('user-info').textContent = `${user.name} (${user.role})`;

        handleTabChange(defaultTabs[user.role] || 'citizen');
        refreshDataByRole();
    } catch (error) {
        window.location.href = 'auth.html';
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (typeof initTheme === 'function') {
        initTheme();
    }

    initDashboard();
});

