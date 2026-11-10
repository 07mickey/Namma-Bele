// admin_dashboard.js
// Front‑end logic for the Admin Dashboard (static layout with placeholder data).
// -----------------------------------------------------------------------
// 1. Populate statistic cards with temporary placeholder values.
// 2. Render a short list of recent appointments (static rows).
// 3. Provide a logout button handler (currently just redirects to login page).
// 4. Mark clearly where real API calls should be added once the Flask backend is ready.
// -----------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // ----- Placeholder data ----- //
    const stats = {
        totalFarmers: 42,
        pendingAppts: 5,
        approvedAppts: 12,
        completedAppts: 30,
        totalReports: 28,
    };

    const recentAppointments = [
        { id: 101, farmer: 'Alice Johnson', date: '2024-09-15', status: 'Pending' },
        { id: 102, farmer: 'Bob Smith', date: '2024-09-14', status: 'Approved' },
        { id: 103, farmer: 'Charlie Lee', date: '2024-09-13', status: 'Completed' },
        { id: 104, farmer: 'Dana Patel', date: '2024-09-12', status: 'Pending' },
        { id: 105, farmer: 'Evan Wu', date: '2024-09-11', status: 'Approved' },
    ];

    // ----- Populate statistic cards ----- //
    document.getElementById('totalFarmers').textContent = stats.totalFarmers;
    document.getElementById('pendingAppts').textContent = stats.pendingAppts;
    document.getElementById('approvedAppts').textContent = stats.approvedAppts;
    document.getElementById('completedAppts').textContent = stats.completedAppts;
    document.getElementById('totalReports').textContent = stats.totalReports;

    // ----- Populate recent appointments table ----- //
    const tbody = document.getElementById('appointmentsBody');
    recentAppointments.forEach(app => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${app.id}</td>
            <td>${app.farmer}</td>
            <td>${app.date}</td>
            <td>${app.status}</td>
        `;
        tbody.appendChild(tr);
    });

    // ----- Logout button ----- //
    const logoutBtn = document.getElementById('logoutBtn');
    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        // Future: call backend logout endpoint, clear token/cookies.
        // For now, simply redirect to the login page.
        window.location.href = 'admin_login.html';
    });

    // ----- Future API integration points ----- //
    // Example (to be replaced later):
    // fetch('/api/admin/stats', { headers: { Authorization: `Bearer ${token}` } })
    //     .then(res => res.json())
    //     .then(data => { /* update DOM with real numbers */ })
    //     .catch(err => console.error('Failed to load stats', err));
});
