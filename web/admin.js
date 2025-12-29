document.addEventListener('DOMContentLoaded', () => {
    // ... [Keep existing Auth logic] ...
    // --- AUTHENTICATION CHECK ---
    const savedPassword = sessionStorage.getItem('admin_session_key');
    const savedEmail = sessionStorage.getItem('admin_email');

    const overlay = document.getElementById('adminLoginOverlay');
    const passInput = document.getElementById('adminPasswordInput');
    const loginBtn = document.getElementById('adminLoginBtn');
    const errorText = document.getElementById('adminLoginError');

    if (savedPassword && savedEmail) {
        overlay.style.display = 'none';
        loadAdminData();
    } else {
        overlay.style.display = 'flex';
    }

    loginBtn.addEventListener('click', async () => {
        const emailVal = document.getElementById('adminEmailInput').value.trim();
        const passVal = passInput.value.trim();

        if (!emailVal || !passVal) {
            errorText.textContent = "Please enter Email and Password.";
            return;
        }

        loginBtn.textContent = "Verifying...";
        loginBtn.disabled = true;

        try {
            const res = await fetch(`/api/admin/verify_access`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-admin-password': passVal
                },
                body: JSON.stringify({ admin_email: emailVal })
            });

            if (res.ok) {
                sessionStorage.setItem('admin_session_key', passVal);
                sessionStorage.setItem('admin_email', emailVal);
                overlay.style.display = 'none';
                loadAdminData();
            } else {
                errorText.textContent = "Invalid Credentials.";
            }
        } catch (e) {
            errorText.textContent = "Network Error.";
        } finally {
            loginBtn.textContent = "Unlock Dashboard";
            loginBtn.disabled = false;
        }
    });

    // --- NEW: MOBILE SIDEBAR TOGGLE ---
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    const closeBtn = document.getElementById('mobileSidebarClose');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.add('active');
        });
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            sidebar.classList.remove('active');
        });
    }
    // Close sidebar when a nav item is clicked (on mobile)
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }

            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');

            const tab = btn.dataset.tab;
            if (tab === 'logs') fetchLogs();
            if (tab === 'moderation') fetchModeration();
            if (tab === 'feedback') fetchFeedback();
        });
    });

    // ... [Rest of your listeners remain the same] ...
    document.getElementById('logoutBtn').addEventListener('click', () => {
        sessionStorage.clear();
        window.location.reload();
    });

    document.getElementById('sendBroadcastBtn').addEventListener('click', sendBroadcast);

    document.querySelectorAll('input[name="targetType"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            document.getElementById('filterControls').style.display = e.target.value === 'filtered' ? 'block' : 'none';
        });
    });

    let searchTimeout;
    document.getElementById('userSearch').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => filterUsers(e.target.value.toLowerCase()), 300);
    });

    document.getElementById('saveUserBtn').addEventListener('click', saveUserStats);
    document.getElementById('msgSearchBtn').addEventListener('click', searchMessages);
    document.getElementById('refreshLogsBtn')?.addEventListener('click', fetchLogs);
    document.getElementById('refreshModBtn')?.addEventListener('click', fetchModeration);
    document.getElementById('refreshFeedbackBtn')?.addEventListener('click', fetchFeedback);
    document.getElementById('closeChatModal').addEventListener('click', () => closeModal('chatModal'));
    document.getElementById('closeEditUserModal').addEventListener('click', () => closeModal('editUserModal'));
    document.getElementById('promoteUserBtn')?.addEventListener('click', () => {
        const id = document.getElementById('editUserId').value;
        window.promoteUser(id);
    });

    // New Admin Listeners
    document.getElementById('saveNewAdminBtn')?.addEventListener('click', createNewAdmin);

    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = "none";
        }
    });

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            if (tab === 'admins') fetchAdmins();
        });
    });

    document.getElementById('maintenanceToggle').addEventListener('change', toggleMaintenance);
    document.getElementById('exportUsersBtn').addEventListener('click', exportUsersCSV);

    setInterval(fetchHealth, 5000);
});

// ... [Keep the rest of the API logic from previous admin.js - no changes needed below this point] ...
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'x-admin-password': sessionStorage.getItem('admin_session_key')
    };
}

function getEmailParam() {
    return `admin_email=${encodeURIComponent(sessionStorage.getItem('admin_email'))}`;
}

function handleAuthFail() {
    sessionStorage.clear();
    window.location.reload();
}

function loadAdminData() {
    fetchStats();
    fetchUsers();
    fetchLogs();
    fetchGrowthChart();
    fetchHealth();
    fetchModeration();
}

async function fetchStats() {
    try {
        const res = await fetch(`/api/admin/dashboard?${getEmailParam()}`, { headers: getHeaders() });
        if (res.status === 401) { handleAuthFail(); return; }

        const data = await res.json();
        if (data.success) {
            document.getElementById('statUsers').textContent = data.stats.users;
            document.getElementById('statMessages').textContent = data.stats.messages;

            const maint = data.stats.maintenance;
            const maintSpan = document.getElementById('statMaintenance');
            maintSpan.textContent = maint ? "Active" : "Off";
            maintSpan.style.color = maint ? "#ff4d4d" : "#00ff88";
            document.getElementById('maintenanceToggle').checked = maint;
        }
    } catch (e) { console.error("Stats error:", e); }
}

async function fetchHealth() {
    if (!document.getElementById('dashboard').classList.contains('active')) return;
    try {
        const res = await fetch(`/api/admin/system/health?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            const h = data.health;
            document.getElementById('cpuVal').textContent = h.cpu + "%";
            document.getElementById('cpuBar').style.width = h.cpu + "%";
            document.getElementById('ramVal').textContent = h.ram + "%";
            document.getElementById('ramBar').style.width = h.ram + "%";
            document.getElementById('diskVal').textContent = h.disk + "%";
            document.getElementById('diskBar').style.width = h.disk + "%";
        }
    } catch (e) { }
}

let growthChartInstance = null;
async function fetchGrowthChart() {
    try {
        const res = await fetch(`/api/admin/analytics/growth?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) renderChart(data.chartData);
    } catch (e) { }
}

function renderChart(data) {
    const ctx = document.getElementById('growthChart').getContext('2d');
    if (growthChartInstance) growthChartInstance.destroy();

    growthChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'New Signups',
                data: data.data,
                borderColor: '#8a63d2',
                backgroundColor: 'rgba(138, 99, 210, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#8a63d2'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' } },
                x: { grid: { display: false }, ticks: { color: '#aaa' } }
            }
        }
    });
}

async function fetchUsers() {
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '<tr><td colspan="7">Loading users...</td></tr>';

    try {
        const res = await fetch(`/api/admin/users?${getEmailParam()}`, { headers: getHeaders() });
        if (res.status === 401) { handleAuthFail(); return; }
        const data = await res.json();

        if (data.success) {
            tbody.innerHTML = '';
            data.users.forEach(u => {
                const bannedClass = u.is_banned ? 'banned-row' : '';
                const btnText = u.is_banned ? 'Unban' : 'Ban';
                const btnColor = u.is_banned ? 'btn-success' : 'btn-warning';

                const tr = document.createElement('tr');
                tr.className = bannedClass;
                tr.innerHTML = `
                    <td>${u.name}</td>
                    <td>${u.email}</td>
                    <td>${u.friend_id}</td>
                    <td>${u.subscription || 'free'}</td>
                    <td><span class="badge">Lvl ${u.level}</span></td>
                    <td>${u.is_banned ? '<span class="status-banned">Banned</span>' : '<span class="status-active">Active</span>'}</td>
                    <td>
                        <div class="action-group">
                            <button class="btn-icon ${btnColor}" onclick="window.toggleBan('${u.id}')" title="${btnText}"><i class='bx bxs-user-x'></i></button>
                            <button class="btn-icon btn-info" onclick="window.viewChats('${u.id}', '${u.name}')" title="View Chats"><i class='bx bxs-message-dots'></i></button>
                            <button class="btn-icon btn-primary" onclick="window.openEditUser('${u.id}', '${u.name}', ${u.level}, ${u.xp}, '${u.subscription}')" title="Edit"><i class='bx bxs-edit'></i></button>
                            <button class="btn-icon btn-danger" onclick="window.deleteUser('${u.id}')" title="Delete"><i class='bx bxs-trash'></i></button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="7">Error loading users.</td></tr>'; }
}

async function fetchModeration() {
    const tbody = document.getElementById('modTableBody');
    tbody.innerHTML = '<tr><td colspan="4">Loading queue...</td></tr>';
    try {
        const res = await fetch(`/api/admin/moderation/flagged?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            tbody.innerHTML = '';
            if (data.messages.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No flagged messages found. Good job!</td></tr>';
                return;
            }
            data.messages.forEach(m => {
                tbody.innerHTML += `
                    <tr>
                        <td>${m.time}</td>
                        <td>${m.sender}<br><small style="opacity:0.6">${m.email}</small></td>
                        <td><span class="badge status-banned">${m.reason}</span></td>
                        <td>${m.message}</td>
                    </tr>`;
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4">Error loading moderation.</td></tr>'; }
}

async function fetchLogs() {
    const tbody = document.getElementById('logsTableBody');
    tbody.innerHTML = '<tr><td colspan="4">Loading logs...</td></tr>';
    try {
        const res = await fetch(`/api/admin/logs?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            tbody.innerHTML = '';
            if (data.logs.length === 0) tbody.innerHTML = '<tr><td colspan="4">No logs found.</td></tr>';
            data.logs.forEach(l => {
                tbody.innerHTML += `
                    <tr>
                        <td>${l.time}</td>
                        <td>${l.admin}</td>
                        <td><strong>${l.action}</strong></td>
                        <td>${l.details}</td>
                    </tr>`;
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4">Error loading logs.</td></tr>'; }
}

async function searchMessages() {
    const query = document.getElementById('msgSearchInput').value.trim();
    if (!query) return;

    const tbody = document.getElementById('messagesTableBody');
    tbody.innerHTML = '<tr><td colspan="4">Searching...</td></tr>';

    try {
        const res = await fetch(`/api/admin/messages/search?query=${encodeURIComponent(query)}&${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();

        if (data.success) {
            tbody.innerHTML = '';
            if (data.messages.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No messages found matching query.</td></tr>';
                return;
            }
            data.messages.forEach(m => {
                tbody.innerHTML += `
                    <tr>
                        <td>${m.time}</td>
                        <td>${m.sender}<br><small>${m.email}</small></td>
                        <td>${m.message}</td>
                    </tr>`;
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4">Error searching.</td></tr>'; }
}

async function fetchFeedback() {
    const tbody = document.getElementById('feedbackTableBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';

    try {
        const res = await fetch(`/api/admin/feedback?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            tbody.innerHTML = '';
            if (data.feedback.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No feedback received yet.</td></tr>';
                return;
            }
            data.feedback.forEach(f => {
                tbody.innerHTML += `
                    <tr>
                        <td>${f.time}</td>
                        <td>${f.email}</td>
                        <td><span class="badge">${f.category}</span></td>
                        <td>${f.message}</td>
                        <td>${f.status}</td>
                    </tr>`;
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="5">Error loading feedback.</td></tr>'; }
}

window.toggleBan = async function (id) {
    try {
        const res = await fetch(`/api/admin/users/${id}/ban?${getEmailParam()}`, { method: 'POST', headers: getHeaders() });
        const data = await res.json();
        if (data.success) fetchUsers();
        else alert("Failed to change ban status");
    } catch (e) { alert("Network Error"); }
};

window.deleteUser = async function (id) {
    if (!confirm("Are you sure? This permanently deletes the user and all their chats.")) return;
    try {
        const res = await fetch(`/api/admin/users/${id}?${getEmailParam()}`, { method: 'DELETE', headers: getHeaders() });
        if ((await res.json()).success) fetchUsers();
        else alert("Failed to delete user");
    } catch (e) { alert("Network Error"); }
};

window.promoteUser = async function (id) {
    if (!confirm("Promote this user to Admin? They will have full access.")) return;
    try {
        const res = await fetch(`/api/admin/users/${id}/promote?${getEmailParam()}`, { method: 'POST', headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            alert("User promoted successfully!");
            fetchUsers();
        } else alert("Failed: " + (data.message || "Unknown error"));
    } catch (e) { alert("Network Error"); }
};

window.viewChats = async function (id, name) {
    document.getElementById('chatModal').style.display = 'block';
    const body = document.getElementById('chatModalBody');
    body.innerHTML = '<p>Loading chats...</p>';

    try {
        const res = await fetch(`/api/admin/users/${id}/chats?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            body.innerHTML = `<h3>Chat History: ${name}</h3>`;
            if (data.chats.length === 0) body.innerHTML += '<p>No messages found.</p>';

            data.chats.forEach(c => {
                const div = document.createElement('div');
                div.className = `chat-row ${c.sender === 'user' ? 'chat-user' : 'chat-bot'}`;
                div.innerHTML = `<strong>${c.sender === 'user' ? name : 'AI'}:</strong> ${c.message} <br><small style="font-size:0.7em; opacity:0.7">${c.time}</small>`;
                body.appendChild(div);
            });
        }
    } catch (e) { body.innerHTML = 'Error loading chats.'; }
};

window.openEditUser = function (id, name, level, xp, sub) {
    if (!document.getElementById('editUserId')) { console.warn('Edit modal elements missing'); return; }
    document.getElementById('editUserId').value = id;
    document.getElementById('editUserName').value = name;
    const passField = document.getElementById('editUserPassword');
    if (passField) passField.value = '';
    document.getElementById('editUserLevel').value = level;
    document.getElementById('editUserXP').value = xp;
    document.getElementById('editUserSub').value = sub || 'free';
    document.getElementById('editUserModal').style.display = 'block';
};

window.closeModal = function (id) {
    document.getElementById(id).style.display = 'none';
}

async function saveUserStats() {
    const id = document.getElementById('editUserId').value;
    const payload = {
        name: document.getElementById('editUserName').value,
        password: document.getElementById('editUserPassword').value,
        level: document.getElementById('editUserLevel').value,
        xp: document.getElementById('editUserXP').value,
        subscription: document.getElementById('editUserSub').value
    };

    try {
        const res = await fetch(`/api/admin/users/${id}/update?${getEmailParam()}`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });

        if ((await res.json()).success) {
            closeModal('editUserModal');
            fetchUsers();
        } else {
            alert("Failed to save changes.");
        }
    } catch (e) { alert("Error saving data."); }
}

async function sendBroadcast() {
    const text = document.getElementById('broadcastMsg').value.trim();
    if (!text) return;

    const targetType = document.querySelector('input[name="targetType"]:checked').value;
    const filters = {
        target_type: targetType,
        subscription: document.getElementById('filterSubscription').value,
        is_early_user: document.getElementById('filterEarlyUser').checked,
        email: document.getElementById('filterEmail').value.trim()
    };

    const status = document.getElementById('broadcastStatus');
    status.textContent = "Sending...";

    try {
        const res = await fetch(`/api/admin/broadcast`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                admin_email: sessionStorage.getItem('admin_email'),
                message: text,
                filters: filters
            })
        });
        const data = await res.json();
        status.textContent = data.success ? data.message : "Error: " + data.message;
    } catch (e) {
        status.textContent = "Network error";
    }
}

async function toggleMaintenance(e) {
    const active = e.target.checked;
    try {
        const res = await fetch(`/api/admin/system/maintenance?${getEmailParam()}`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify({ active })
        });
        const data = await res.json();
        if (data.success) fetchStats();
        else { alert("Failed to toggle maintenance"); e.target.checked = !active; }
    } catch (err) { alert("Network Error"); e.target.checked = !active; }
}

async function exportUsersCSV() {
    try {
        const res = await fetch(`/api/admin/export/users?${getEmailParam()}`, {
            headers: { 'x-admin-password': sessionStorage.getItem('admin_session_key') }
        });

        if (res.status === 401) return handleAuthFail();

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (e) { alert("Download failed."); }
}

function filterUsers(query) {
    document.querySelectorAll('#userTableBody tr').forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(query) ? '' : 'none';
    });
}

// --- ADMIN MANAGEMENT STUBS ---
async function fetchAdmins() {
    const tbody = document.getElementById('adminsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';

    try {
        const res = await fetch(`/api/admin/helpers?${getEmailParam()}`, { headers: getHeaders() });
        const data = await res.json();
        if (data.success) {
            tbody.innerHTML = '';
            data.admins.forEach(a => {
                const isMe = a.email === sessionStorage.getItem('admin_email');
                const btn = isMe ? '<span style="color:#aaa">Current</span>' :
                    `<button class="btn-icon btn-danger" onclick="deleteAdminHelper('${a.email}')"><i class='bx bxs-trash'></i></button>`;

                tbody.innerHTML += `
                    <tr>
                        <td>${a.email}</td>
                        <td>${a.role}</td>
                        <td>${a.created_at}</td>
                        <td>${btn}</td>
                    </tr>
                `;
            });
        }
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4">Error loading admins.</td></tr>'; }
}

async function createNewAdmin() {
    const email = document.getElementById('newAdminEmail').value.trim();
    const password = document.getElementById('newAdminPassword').value.trim();
    if (!email || !password) return alert("Fill all fields.");

    try {
        const res = await fetch(`/api/admin/helpers?${getEmailParam()}`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.success) {
            alert("Admin created!");
            document.getElementById('addAdminModal').style.display = 'none';
            fetchAdmins();
        } else {
            alert("Failed: " + (data.message || "Unknown error"));
        }
    } catch (e) { alert("Network Error"); }
}

window.deleteAdminHelper = async function (email) {
    if (!confirm(`Delete admin access for ${email}?`)) return;
    try {
        const res = await fetch(`/api/admin/helpers?${getEmailParam()}&email=${encodeURIComponent(email)}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        const data = await res.json();
        if (data.success) fetchAdmins();
        else alert(data.message || "Failed.");
    } catch (e) { alert("Network Error"); }
};