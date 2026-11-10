// appointment_management.js
// Front‑end logic for the Admin "Appointment Management" page.
// -----------------------------------------------------------
// 1. Uses DEMO DATA (clearly labeled) to populate the table.
// 2. Implements client‑side search (by ID or farmer name/email).
// 3. Implements status filter (All, Pending, Approved, Rejected, Completed).
// 4. Provides actions: View, Approve, Reject, Mark Completed.
//    - Actions are only enabled according to the business rules.
//    - Each action asks for user confirmation via window.confirm.
//    - On confirmation, the demo data is updated and the UI refreshed.
//    - A notice is shown that changes are temporary until backend integration.
// 5. Shows appropriate empty‑state messages.
// 6. Marks where real API calls will replace the demo data.
// -----------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // ----- DEMO DATA (replace with real API) -----
    let demoAppointments = [
        // DEMO DATA – each record will be mutated only in this session
        {
            id: 2001,
            farmerName: 'Alice Johnson',
            farmerEmail: 'alice@example.com',
            date: '2024-10-05',
            time: '09:30',
            status: 'Pending'
        },
        {
            id: 2002,
            farmerName: 'Bob Smith',
            farmerEmail: 'bob@example.com',
            date: '2024-10-06',
            time: '14:00',
            status: 'Approved'
        },
        {
            id: 2003,
            farmerName: 'Charlie Lee',
            farmerEmail: 'charlie@example.com',
            date: '2024-10-07',
            time: '11:15',
            status: 'Rejected'
        },
        {
            id: 2004,
            farmerName: 'Dana Patel',
            farmerEmail: 'dana@example.com',
            date: '2024-10-08',
            time: '13:45',
            status: 'Completed'
        },
    ];

    const tbody = document.getElementById('appointmentTableBody');
    const searchInput = document.getElementById('appointmentSearch');
    const statusSelect = document.getElementById('statusFilter');
    const emptyState = document.getElementById('emptyState');
    const modal = document.getElementById('detailsModal');
    const closeModalBtn = document.getElementById('closeModal');
    const detailsBody = document.getElementById('detailsBody');

    // Render rows based on provided appointment array
    const renderTable = (appointments) => {
        tbody.innerHTML = '';
        if (appointments.length === 0) {
            emptyState.classList.remove('hidden');
        } else {
            emptyState.classList.add('hidden');
            appointments.forEach(app => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${app.id}</td>
                    <td>${app.farmerName}</td>
                    <td>${app.farmerEmail}</td>
                    <td>${app.date}</td>
                    <td>${app.time}</td>
                    <td class="status-cell">${app.status}</td>
                    <td class="actions-cell"></td>
                `;
                // Build actions according to status rules
                const actionsCell = tr.querySelector('.actions-cell');
                // View button (always available)
                const viewBtn = document.createElement('button');
                viewBtn.textContent = 'View';
                viewBtn.className = 'action-btn view-btn';
                viewBtn.dataset.id = app.id;
                actionsCell.appendChild(viewBtn);

                // Conditional buttons
                if (app.status === 'Pending') {
                    const approveBtn = document.createElement('button');
                    approveBtn.textContent = 'Approve';
                    approveBtn.className = 'action-btn approve-btn';
                    approveBtn.dataset.id = app.id;
                    actionsCell.appendChild(approveBtn);

                    const rejectBtn = document.createElement('button');
                    rejectBtn.textContent = 'Reject';
                    rejectBtn.className = 'action-btn reject-btn';
                    rejectBtn.dataset.id = app.id;
                    actionsCell.appendChild(rejectBtn);
                } else if (app.status === 'Approved') {
                    const completeBtn = document.createElement('button');
                    completeBtn.textContent = 'Mark Completed';
                    completeBtn.className = 'action-btn complete-btn';
                    completeBtn.dataset.id = app.id;
                    actionsCell.appendChild(completeBtn);
                }
                tbody.appendChild(tr);
            });
        }
    };

    // Initial render
    renderTable(demoAppointments);

    // Filtering logic
    const applyFilters = () => {
        const term = searchInput.value.trim().toLowerCase();
        const statusFilter = statusSelect.value;
        const filtered = demoAppointments.filter(app => {
            const matchesSearch = term === '' ||
                app.id.toString().includes(term) ||
                app.farmerName.toLowerCase().includes(term) ||
                app.farmerEmail.toLowerCase().includes(term);
            const matchesStatus = statusFilter === 'All' || app.status === statusFilter;
            return matchesSearch && matchesStatus;
        });
        renderTable(filtered);
    };

    searchInput.addEventListener('input', applyFilters);
    statusSelect.addEventListener('change', applyFilters);

    // Event delegation for action buttons
    tbody.addEventListener('click', (e) => {
        if (!e.target.matches('button')) return;
        const btn = e.target;
        const id = Number(btn.dataset.id);
        const appointment = demoAppointments.find(a => a.id === id);
        if (!appointment) return;

        // View details
        if (btn.classList.contains('view-btn')) {
            detailsBody.innerHTML = `
                <p><strong>Appointment ID:</strong> ${appointment.id}</p>
                <p><strong>Farmer:</strong> ${appointment.farmerName} (${appointment.farmerEmail})</p>
                <p><strong>Date:</strong> ${appointment.date}</p>
                <p><strong>Time:</strong> ${appointment.time}</p>
                <p><strong>Status:</strong> ${appointment.status}</p>
                <p><em>Note: Details are demo data and will be replaced by real backend information.</em></p>
            `;
            modal.classList.remove('hidden');
            return;
        }

        // Approve
        if (btn.classList.contains('approve-btn')) {
            if (confirm('Approve this appointment? This change is temporary until the backend is integrated.')) {
                appointment.status = 'Approved';
                alert('Appointment approved (temporary).');
                applyFilters();
            }
            return;
        }
        // Reject
        if (btn.classList.contains('reject-btn')) {
            if (confirm('Reject this appointment? This change is temporary until the backend is integrated.')) {
                appointment.status = 'Rejected';
                alert('Appointment rejected (temporary).');
                applyFilters();
            }
            return;
        }
        // Mark Completed
        if (btn.classList.contains('complete-btn')) {
            if (confirm('Mark this appointment as Completed? This change is temporary until the backend is integrated.')) {
                appointment.status = 'Completed';
                alert('Appointment marked completed (temporary).');
                applyFilters();
            }
            return;
        }
    });

    // Modal close handling
    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.add('hidden'); });

    // ----- Future API integration placeholder -----
    // Example: fetch('/api/admin/appointments', { headers: { Authorization: `Bearer ${token}` } })
    //   .then(r => r.json())
    //   .then(data => { demoAppointments = data; applyFilters(); })
    //   .catch(err => console.error('Failed to load appointments', err));
});
