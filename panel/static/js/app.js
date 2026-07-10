// ============================================================
//  Haji Panel - Panel Frontend Logic
// ============================================================

// Sidebar toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.querySelector('.menu-btn');
    
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Auto-refresh server status
async function updateServerStatus() {
    try {
        const res = await fetch('/api/status');
        if (res.ok) {
            const dot = document.getElementById('serverStatus');
            const text = document.getElementById('statusText');
            if (dot) {
                dot.style.background = 'var(--success)';
                dot.style.boxShadow = '0 0 8px var(--success)';
            }
            if (text) text.textContent = 'آنلاین';
        }
    } catch (e) {
        const dot = document.getElementById('serverStatus');
        const text = document.getElementById('statusText');
        if (dot) {
            dot.style.background = 'var(--danger)';
            dot.style.boxShadow = '0 0 8px var(--danger)';
        }
        if (text) text.textContent = 'آفلاین';
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateServerStatus();
    setInterval(updateServerStatus, 10000);
});
