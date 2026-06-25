/* ═══════════════════════════════════════════════════════════════
   Admin Dashboard - Application Logic
   Full Integration with Backend APIs & Real-time Updates
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;
const BAR_COLORS = ['bar-purple', 'bar-blue', 'bar-green', 'bar-orange', 'bar-rose', 'bar-teal'];
let autoRefreshTimer = null;

// ═══════════════════ INITIALIZATION ═══════════════════

document.addEventListener('DOMContentLoaded', () => {
    updateTime();
    setInterval(updateTime, 60000);
    loadDashboard();

    // Auto-refresh every 30 seconds
    startAutoRefresh();
});

function updateTime() {
    const now = new Date();
    const el = document.getElementById('headerTime');
    if (el) {
        el.textContent = now.toLocaleString('en-IN', {
            weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }
}

function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(() => {
        const activeTab = document.querySelector('.sidebar-link.active');
        if (activeTab && activeTab.dataset.tab === 'dashboard') {
            loadDashboard();
        }
    }, 30000);
}

// ═══════════════════ TAB NAVIGATION ═══════════════════

function switchTab(tabName) {
    // Update sidebar
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.classList.toggle('active', link.dataset.tab === tabName);
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.toggle('active', tab.id === `tab-${tabName}`);
    });

    // Update title
    const titles = { dashboard: 'Dashboard', bookings: 'Bookings', exhibitions: 'Exhibitions', analytics: 'Analytics' };
    const titleEl = document.getElementById('pageTitle');
    if (titleEl) titleEl.textContent = titles[tabName] || 'Dashboard';

    // Load tab data
    switch (tabName) {
        case 'dashboard': loadDashboard(); break;
        case 'bookings': loadRecentBookings(); break;
        case 'exhibitions': loadExhibitionsAdmin(); break;
        case 'analytics': loadAnalytics(); break;
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

function refreshData() {
    const activeTab = document.querySelector('.sidebar-link.active');
    if (activeTab) {
        const tabName = activeTab.dataset.tab;
        // Show refresh animation
        const btn = document.querySelector('.header-refresh');
        if (btn) {
            btn.style.transform = 'rotate(360deg)';
            setTimeout(() => btn.style.transform = '', 500);
        }
        switchTab(tabName);
    }
}

// ═══════════════════ DASHBOARD ═══════════════════

async function loadDashboard() {
    try {
        // Load all dashboard data in parallel
        const [summary, ticketTypes, demographics, trends] = await Promise.all([
            fetchJSON('/api/admin/dashboard'),
            fetchJSON('/api/admin/analytics/ticket-types'),
            fetchJSON('/api/admin/analytics/demographics'),
            fetchJSON('/api/admin/analytics/trends?days=30'),
        ]);

        // Update metrics with animation
        animateValue('totalBookings', summary.total_bookings);
        const revenueEl = document.getElementById('totalRevenue');
        if (revenueEl) revenueEl.textContent = `₹${summary.total_revenue.toLocaleString()}`;
        animateValue('todayTickets', summary.tickets_today);
        animateValue('activeSessions', summary.active_sessions);

        // Update status counts
        const setContent = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setContent('confirmedCount', summary.confirmed_bookings);
        setContent('pendingCount', summary.pending_bookings);
        setContent('cancelledCount', summary.cancelled_bookings);

        // Today revenue
        setContent('todayRevenue', `₹${summary.revenue_today.toLocaleString()}`);
        const revenuePercent = summary.total_revenue > 0
            ? Math.min((summary.revenue_today / summary.total_revenue) * 100, 100)
            : 0;
        const barFill = document.getElementById('revenueBarFill');
        if (barFill) barFill.style.width = `${revenuePercent}%`;

        // Render charts
        renderBarChart('ticketTypeChart', ticketTypes, 'ticket_type', 'count');
        renderBarChart('demographicsChart', demographics, 'category', 'count');
        renderTrendChart('dailyTrendChart', trends);

    } catch (error) {
        console.error('Dashboard load error:', error);
    }
}

// ═══════════════════ CHARTS ═══════════════════

function renderBarChart(containerId, data, labelKey, valueKey) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!data || data.length === 0) {
        container.innerHTML = '<p class="chart-loading">No data available yet. Complete a booking via chat to see data.</p>';
        return;
    }

    const max = Math.max(...data.map(d => d[valueKey]));

    container.innerHTML = data.map((item, i) => {
        const pct = max > 0 ? (item[valueKey] / max * 100) : 0;
        const color = BAR_COLORS[i % BAR_COLORS.length];
        const label = (item[labelKey] || 'Unknown').replace(/_/g, ' ');
        const capitalLabel = label.charAt(0).toUpperCase() + label.slice(1);

        return `
            <div class="chart-bar-item">
                <span class="chart-bar-label" title="${capitalLabel}">${capitalLabel}</span>
                <div class="chart-bar-track">
                    <div class="chart-bar-fill ${color}" style="width:${Math.max(pct, 5)}%;">${item[valueKey]}</div>
                </div>
            </div>
        `;
    }).join('');
}

function renderTrendChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!data || data.length === 0) {
        container.innerHTML = '<p class="chart-loading">No trend data available yet. Book tickets to see trends.</p>';
        return;
    }

    const maxBookings = Math.max(...data.map(d => d.bookings), 1);

    container.innerHTML = data.map(day => {
        const height = (day.bookings / maxBookings) * 100;
        const dateShort = day.date ? day.date.slice(5) : '';
        return `<div class="trend-bar" style="height:${Math.max(height, 3)}%;" data-tooltip="${day.date}: ${day.bookings} bookings, ₹${day.revenue}" title="${day.date}: ${day.bookings} bookings, ₹${day.revenue}"></div>`;
    }).join('');
}

// ═══════════════════ BOOKINGS ═══════════════════

async function loadRecentBookings() {
    try {
        const bookings = await fetchJSON('/api/admin/bookings/recent?limit=50');
        const tbody = document.getElementById('bookingsTableBody');
        if (!tbody) return;

        if (!bookings || bookings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="table-empty">No bookings yet. Use the chatbot to create your first booking!</td></tr>';
            return;
        }

        tbody.innerHTML = bookings.map(b => {
            const statusClass = b.status || 'pending';
            const paymentClass = b.payment_status || 'pending';
            const ticketType = (b.ticket_type || '-').replace(/_/g, ' ');
            const capitalType = ticketType.charAt(0).toUpperCase() + ticketType.slice(1);

            return `
                <tr>
                    <td><code style="background:rgba(124,92,252,0.1);padding:2px 8px;border-radius:4px;font-size:0.85em;">${b.booking_id || '-'}</code></td>
                    <td>${b.visitor_name || '-'}</td>
                    <td>${capitalType}</td>
                    <td>${b.visit_date || '-'}</td>
                    <td style="text-align:center;">${b.num_tickets || 0}</td>
                    <td>₹${(b.total_price || 0).toLocaleString()}</td>
                    <td><span class="status-badge ${statusClass}">${(b.status || 'pending').toUpperCase()}</span></td>
                    <td><span class="status-badge ${paymentClass}">${(b.payment_status || 'pending').toUpperCase()}</span></td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Bookings load error:', error);
        const tbody = document.getElementById('bookingsTableBody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="table-empty">Error loading bookings. Please refresh.</td></tr>';
    }
}

// ═══════════════════ EXHIBITIONS ═══════════════════

async function loadExhibitionsAdmin() {
    try {
        const data = await fetchJSON('/api/tickets/exhibitions?active_only=false');
        const grid = document.getElementById('exhibitionsAdminGrid');
        if (!grid) return;

        if (!data.exhibitions || data.exhibitions.length === 0) {
            grid.innerHTML = '<p class="chart-loading">No exhibitions. Click "Add Exhibition" to create one.</p>';
            return;
        }

        grid.innerHTML = data.exhibitions.map(ex => `
            <div class="ex-admin-card ${!ex.is_active ? 'inactive' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:start;">
                    <h4>${escapeHtml(ex.name)}</h4>
                    <div style="display:flex;gap:6px;align-items:center;">
                        ${ex.is_special ? '<span style="color:var(--accent-gold);font-size:0.8rem;">✨ Special</span>' : ''}
                        <span class="status-badge ${ex.is_active ? 'confirmed' : 'cancelled'}" style="font-size:0.7rem;padding:2px 8px;">${ex.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                    </div>
                </div>
                <p>${escapeHtml(ex.description)}</p>
                <div class="ex-admin-meta">
                    <span>📅 ${ex.start_date} → ${ex.end_date}</span>
                    <span class="ex-admin-price">₹${ex.ticket_price}</span>
                </div>
                <div style="margin-top:8px;font-size:0.8rem;color:var(--text-muted);">
                    👥 Capacity: ${ex.daily_capacity}/day
                    ${ex.show_times ? ` | ⏰ Shows: ${ex.show_times.join(', ')}` : ''}
                </div>
                <div class="ex-admin-actions">
                    ${ex.is_active ? `<button class="ex-action-btn delete" onclick="deleteExhibition('${ex.exhibition_id}')">🗑️ Deactivate</button>` : '<span style="color:var(--text-muted);font-size:0.8rem;">Deactivated</span>'}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Exhibitions load error:', error);
    }
}

function showAddExhibition() {
    const form = document.getElementById('addExhibitionForm');
    if (form) form.style.display = 'block';
}

function hideAddExhibition() {
    const form = document.getElementById('addExhibitionForm');
    if (form) form.style.display = 'none';
}

async function createExhibition(e) {
    e.preventDefault();

    const showTimesStr = document.getElementById('exShowTimes').value;
    const showTimes = showTimesStr ? showTimesStr.split(',').map(s => s.trim()).filter(Boolean) : null;

    const body = {
        name: document.getElementById('exName').value,
        description: document.getElementById('exDescription').value,
        start_date: document.getElementById('exStartDate').value,
        end_date: document.getElementById('exEndDate').value,
        daily_capacity: parseInt(document.getElementById('exCapacity').value) || 500,
        ticket_price: parseFloat(document.getElementById('exPrice').value) || 0,
        show_times: showTimes,
        is_special: document.getElementById('exSpecial').checked,
    };

    try {
        const res = await fetch(`${API_BASE}/api/admin/exhibitions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (res.ok) {
            hideAddExhibition();
            loadExhibitionsAdmin();
            e.target.reset();
            showNotification('Exhibition created successfully!', 'success');
        } else {
            const err = await res.json();
            showNotification('Error: ' + (err.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showNotification('Error creating exhibition: ' + error.message, 'error');
    }
}

async function deleteExhibition(id) {
    if (!confirm('Deactivate this exhibition? It will no longer appear for booking.')) return;

    try {
        const res = await fetch(`${API_BASE}/api/admin/exhibitions/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadExhibitionsAdmin();
            showNotification('Exhibition deactivated', 'success');
        } else {
            showNotification('Error deactivating exhibition', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

// ═══════════════════ ANALYTICS ═══════════════════

async function loadAnalytics() {
    try {
        const [languages, exhibitions, hourly] = await Promise.all([
            fetchJSON('/api/admin/analytics/languages'),
            fetchJSON('/api/admin/analytics/exhibitions'),
            fetchJSON('/api/admin/analytics/hourly'),
        ]);

        renderBarChart('languageChart', languages, 'language', 'count');

        const exhData = exhibitions.map(e => ({
            exhibition_name: e.exhibition_name,
            tickets: e.tickets
        }));
        renderBarChart('exhibitionPopChart', exhData, 'exhibition_name', 'tickets');

        // Hourly chart
        const hourlyContainer = document.getElementById('hourlyChart');
        if (!hourlyContainer) return;

        if (hourly && hourly.length > 0) {
            const maxH = Math.max(...hourly.map(h => h.bookings), 1);
            // Create 24h array
            const hours = Array.from({ length: 24 }, (_, i) => {
                const found = hourly.find(h => h.hour === i);
                return { hour: i, bookings: found ? found.bookings : 0 };
            });

            hourlyContainer.innerHTML = hours.map(h => {
                const height = (h.bookings / maxH) * 100;
                return `<div class="trend-bar" style="height:${Math.max(height, 3)}%;" data-tooltip="${h.hour}:00 - ${h.bookings} bookings" title="${h.hour}:00 - ${h.bookings} bookings"></div>`;
            }).join('');
        } else {
            hourlyContainer.innerHTML = '<p class="chart-loading">No hourly data available yet</p>';
        }
    } catch (error) {
        console.error('Analytics load error:', error);
    }
}

// ═══════════════════ UTILITIES ═══════════════════

async function fetchJSON(url) {
    const response = await fetch(`${API_BASE}${url}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

function animateValue(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const current = parseInt(el.textContent.replace(/,/g, '')) || 0;
    if (current === target) return;

    const step = Math.ceil(Math.abs(target - current) / 30) || 1;
    let value = current;

    const timer = setInterval(() => {
        if (value < target) {
            value = Math.min(value + step, target);
        } else if (value > target) {
            value = Math.max(value - step, target);
        }

        el.textContent = value.toLocaleString();

        if (value === target) clearInterval(timer);
    }, 30);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 14px 24px;
        border-radius: 12px;
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 500;
        z-index: 10000;
        opacity: 0;
        transform: translateX(100px);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        backdrop-filter: blur(10px);
        border: 1px solid;
        ${type === 'success'
            ? 'background:rgba(34,197,94,0.15);color:#22c55e;border-color:rgba(34,197,94,0.3);'
            : 'background:rgba(239,68,68,0.15);color:#ef4444;border-color:rgba(239,68,68,0.3);'}
    `;
    notif.textContent = `${type === 'success' ? '✅' : '❌'} ${message}`;
    document.body.appendChild(notif);

    requestAnimationFrame(() => {
        notif.style.opacity = '1';
        notif.style.transform = 'translateX(0)';
    });

    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transform = 'translateX(100px)';
        setTimeout(() => notif.remove(), 400);
    }, 3000);
}
