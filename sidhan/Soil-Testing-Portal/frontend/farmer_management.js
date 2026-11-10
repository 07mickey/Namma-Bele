// farmer_management.js
// Front‑end logic for the Admin "Farmer Management" page.
// ------------------------------------------------------
// 1. Load demo farmer data (clearly labeled) and render the table.
// 2. Implement client‑side search that filters by name or email.
// 3. Show a modal with farmer details when "View" is clicked.
// 4. Display an empty‑state message when no rows match the filter.
// 5. Mark where real API calls should replace the demo data.
// ------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // ----- Demo data (replace with real API) -----
    const demoFarmers = [
        // DEMO DATA – replace with backend response
        { id: 1, name: 'Alice Johnson', email: 'alice@example.com', phone: '555‑1234', regDate: '2023-04-12', address: '123 Farm Lane' },
        { id: 2, name: 'Bob Smith', email: 'bob@example.com', phone: '555‑5678', regDate: '2022-11-03', address: '' },
        { id: 3, name: 'Charlie Lee', email: 'charlie@example.com', phone: '555‑9012', regDate: '2024-01-20', address: '789 Rural Rd' },
    ];

    const tableBody = document.getElementById('farmerTableBody');
    const searchInput = document.getElementById('farmerSearch');
    const emptyState = document.getElementById('emptyState');
    const modal = document.getElementById('detailsModal');
    const closeModalBtn = document.getElementById('closeModal');
    const detailsBody = document.getElementById('detailsBody');

    // Render the table rows from an array of farmer objects
    const renderTable = (farmers) => {
        tableBody.innerHTML = '';
        if (farmers.length === 0) {
            emptyState.classList.remove('hidden');
        } else {
            emptyState.classList.add('hidden');
            farmers.forEach(f => {
                const tr = document.createElement('tr');
                // Safer DOM construction to avoid XSS
                const tr = document.createElement('tr');
                const tdId = document.createElement('td'); tdId.textContent = f.id;
                const tdName = document.createElement('td'); tdName.textContent = f.name;
                const tdEmail = document.createElement('td'); tdEmail.textContent = f.email;
                const tdPhone = document.createElement('td'); tdPhone.textContent = f.phone;
                const tdReg = document.createElement('td'); tdReg.textContent = f.regDate;
                const tdAction = document.createElement('td');
                const viewBtn = document.createElement('button');
                viewBtn.className = 'action-btn view-btn';
                viewBtn.dataset.id = f.id;
                viewBtn.textContent = 'View';
                tdAction.appendChild(viewBtn);
                tr.append(tdId, tdName, tdEmail, tdPhone, tdReg, tdAction);
                tableBody.appendChild(tr);
                tableBody.appendChild(tr);
            });
        }
    };

    // Initial render with demo data
    renderTable(demoFarmers);

    // Search filter – matches name or email (case‑insensitive)
    searchInput.addEventListener('input', () => {
        const term = searchInput.value.trim().toLowerCase();
        const filtered = demoFarmers.filter(f =>
            f.name.toLowerCase().includes(term) || f.email.toLowerCase().includes(term)
        );
        renderTable(filtered);
    });

    // Handle View button clicks (event delegation)
    tableBody.addEventListener('click', (e) => {
        if (e.target && e.target.matches('button.view-btn')) {
            const farmerId = Number(e.target.dataset.id);
            const farmer = demoFarmers.find(f => f.id === farmerId);
            if (farmer) {
                // Populate modal content
                detailsBody.innerHTML = `
                    <p><strong>Name:</strong> ${farmer.name}</p>
                    <p><strong>Email:</strong> ${farmer.email}</p>
                    <p><strong>Phone:</strong> ${farmer.phone}</p>
                    <p><strong>Address:</strong> ${farmer.address || 'N/A'}</p>
                    <p><strong>Registration Date:</strong> ${farmer.regDate}</p>
                    <p><strong>Related Appointments:</strong> (demo – to be loaded from backend)</p>
                `;
                modal.classList.remove('hidden');
            }
        }
    });

    // Close modal
    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    // Clicking outside modal content also closes it
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    // ----- Future API integration -----
    // Example placeholder for fetching real farmer list:
    // fetch('/api/admin/farmers', { headers: { Authorization: `Bearer ${token}` } })
    //     .then(res => res.json())
    //     .then(data => { demoFarmers = data; renderTable(demoFarmers); })
    //     .catch(err => console.error('Failed to load farmers', err));
});
