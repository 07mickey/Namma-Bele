// report_management.js
// Front‑end logic for the Admin "Report Management" page.
// -------------------------------------------------------
// 1. Demo data for farmers, appointments, and reports (clearly labelled).
// 2. Populate farmer & appointment dropdowns (appointments filtered by selected farmer).
// 3. Client‑side validation for the upload form:
//    - PDF MIME type only.
//    - File size ≤ 5 MB.
//    - Farmer and appointment must be selected.
// 4. On successful upload, a temporary report entry is added to the table.
// 5. Search box filters reports by Report ID or farmer name (case‑insensitive).
// 6. Actions per row: View (opens modal with details), Download (creates a temporary blob URL),
//    Replace (re‑upload PDF for that report).
// 7. All changes are local and marked as temporary – real backend integration will replace them.
// 8. Empty‑state handling when no reports match.
// 9. Placeholders where real API calls will be added later.
// -------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // ----- DEMO DATA (replace with real API data) -----
    const demoFarmers = [
        // DEMO DATA – will be replaced by backend response
        { id: 1, name: 'Alice Johnson' },
        { id: 2, name: 'Bob Smith' },
        { id: 3, name: 'Charlie Lee' },
    ];

    const demoAppointments = [
        // DEMO DATA – each linked to a farmer via farmerId
        { id: 101, farmerId: 1, date: '2024-10-05' },
        { id: 102, farmerId: 2, date: '2024-10-06' },
        { id: 103, farmerId: 3, date: '2024-10-07' },
    ];

    let demoReports = []; // Will hold objects for uploaded reports (temporary only)
    // ---------------------------------------------------

    // Elements
    const farmerSelect = document.getElementById('farmerSelect');
    const appointmentSelect = document.getElementById('appointmentSelect');
    const uploadForm = document.getElementById('uploadForm');
    const pdfInput = document.getElementById('pdfFile');
    const uploadMsg = document.getElementById('uploadMessage');
    const uploadBtn = document.getElementById('uploadBtn');
    const spinner = uploadBtn.querySelector('.spinner');
    const btnText = uploadBtn.querySelector('.btn-text');
    const reportTableBody = document.getElementById('reportTableBody');
    const searchInput = document.getElementById('reportSearch');
    const emptyState = document.getElementById('emptyState');
    const detailsModal = document.getElementById('detailsModal');
    const closeModalBtn = document.getElementById('closeModal');
    const detailsBody = document.getElementById('detailsBody');

    // Helper to show messages
    const showMessage = (msg, type = 'success') => {
        uploadMsg.textContent = msg;
        uploadMsg.className = `msg ${type}`;
    };
    const clearMessage = () => { uploadMsg.textContent = ''; uploadMsg.className = 'msg'; };

    // Populate farmer dropdown
    const populateFarmers = () => {
        demoFarmers.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = `${f.name} (ID:${f.id})`;
            farmerSelect.appendChild(opt);
        });
    };

    // Populate appointment dropdown – filtered by selected farmer
    const populateAppointments = (farmerId = null) => {
        appointmentSelect.innerHTML = '<option value="">-- Select Appointment --</option>';
        const filtered = farmerId ? demoAppointments.filter(a => a.farmerId === Number(farmerId)) : demoAppointments;
        filtered.forEach(a => {
            const farmerName = demoFarmers.find(f => f.id === a.farmerId)?.name || 'Unknown';
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = `#${a.id} – ${farmerName}`;
            appointmentSelect.appendChild(opt);
        });
    };

    // Initial population
    populateFarmers();
    populateAppointments();

    // When farmer changes, update appointments list
    farmerSelect.addEventListener('change', () => {
        const fid = farmerSelect.value;
        populateAppointments(fid);
    });

    // Render report table (accepts an array of report objects)
    const renderTable = (reports) => {
        reportTableBody.innerHTML = '';
        if (reports.length === 0) {
            emptyState.classList.remove('hidden');
            return;
        }
        emptyState.classList.add('hidden');
        reports.forEach(r => {
            const tr = document.createElement('tr');
            const farmerName = demoFarmers.find(f => f.id === r.farmerId)?.name || 'Unknown';
            tr.innerHTML = `
                <td>${r.id}</td>
                <td>${farmerName}</td>
                <td>${r.appointmentId}</td>
                <td>${r.fileName}</td>
                <td>${r.uploadDate}</td>
                <td class="actions-cell"></td>
            `;
            const actionsCell = tr.querySelector('.actions-cell');
            const viewBtn = document.createElement('button');
            viewBtn.textContent = 'View';
            viewBtn.className = 'action-btn view-btn';
            viewBtn.dataset.id = r.id;
            actionsCell.appendChild(viewBtn);

            const downloadBtn = document.createElement('button');
            downloadBtn.textContent = 'Download';
            downloadBtn.className = 'action-btn download-btn';
            downloadBtn.dataset.id = r.id;
            actionsCell.appendChild(downloadBtn);

            const replaceBtn = document.createElement('button');
            replaceBtn.textContent = 'Replace';
            replaceBtn.className = 'action-btn replace-btn';
            replaceBtn.dataset.id = r.id;
            actionsCell.appendChild(replaceBtn);

            reportTableBody.appendChild(tr);
        });
    };

    // Search / filter function
    const applyFilters = () => {
        const term = searchInput.value.trim().toLowerCase();
        const filtered = demoReports.filter(r => {
            const farmerName = demoFarmers.find(f => f.id === r.farmerId)?.name.toLowerCase() || '';
            return (
                term === '' ||
                r.id.toString().includes(term) ||
                farmerName.includes(term)
            );
        });
        renderTable(filtered);
    };

    searchInput.addEventListener('input', applyFilters);

    // Upload form handler with validation
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessage();
        const farmerId = farmerSelect.value;
        const appointmentId = appointmentSelect.value;
        const file = pdfInput.files[0];

        // Validation
        if (!farmerId) { showMessage('Please select a farmer.', 'error'); return; }
        if (!appointmentId) { showMessage('Please select an appointment.', 'error'); return; }
        if (!file) { showMessage('Please select a PDF file.', 'error'); return; }
        if (file.type !== 'application/pdf') { showMessage('Only PDF files are allowed.', 'error'); return; }
        if (file.size > 5 * 1024 * 1024) { showMessage('File size exceeds 5 MB limit.', 'error'); return; }

        // Show loading state
        uploadBtn.disabled = true;
        spinner.classList.remove('hidden');
        btnText.textContent = 'Uploading…';

        // Simulate async upload – in real code replace with fetch to backend
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Create a temporary report entry (DEM0 DATA)
        const newReport = {
            id: Date.now(), // simple unique id for demo
            farmerId: Number(farmerId),
            appointmentId: Number(appointmentId),
            fileName: file.name,
            uploadDate: new Date().toLocaleDateString(),
            fileBlob: file, // keep the actual File object for temporary download
        };
        demoReports.push(newReport);
        showMessage('Report uploaded successfully (temporary demo entry).', 'success');

        // Reset form UI
        uploadForm.reset();
        populateAppointments(farmerSelect.value); // reset appointment list

        // Refresh table
        applyFilters();

        // Reset button state
        uploadBtn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = 'Upload';
    });

    // Event delegation for row actions
    reportTableBody.addEventListener('click', (e) => {
        if (!e.target.matches('button')) return;
        const btn = e.target;
        const reportId = Number(btn.dataset.id);
        const report = demoReports.find(r => r.id === reportId);
        if (!report) return;

        if (btn.classList.contains('view-btn')) {
            const farmerName = demoFarmers.find(f => f.id === report.farmerId)?.name || 'Unknown';
            detailsBody.innerHTML = `
                <p><strong>Report ID:</strong> ${report.id}</p>
                <p><strong>Farmer:</strong> ${farmerName}</p>
                <p><strong>Appointment ID:</strong> ${report.appointmentId}</p>
                <p><strong>File Name:</strong> ${report.fileName}</p>
                <p><strong>Upload Date:</strong> ${report.uploadDate}</p>
                <p><em>Note: This is a temporary demo record – real data will come from the backend.</em></p>
            `;
            detailsModal.classList.remove('hidden');
            return;
        }

        if (btn.classList.contains('download-btn')) {
            // Create a temporary Blob URL for the stored File object
            const url = URL.createObjectURL(report.fileBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = report.fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            alert('Download initiated (temporary demo file).');
            return;
        }

        if (btn.classList.contains('replace-btn')) {
            // Prompt user to select a new file
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'application/pdf';
            fileInput.onchange = async () => {
                const newFile = fileInput.files[0];
                if (!newFile) return;
                if (newFile.type !== 'application/pdf') { alert('Only PDF files are allowed.'); return; }
                if (newFile.size > 5 * 1024 * 1024) { alert('File exceeds 5 MB limit.'); return; }
                if (confirm('Replace this report with the selected PDF? This change is temporary until backend integration.')) {
                    // Simulate async replace
                    await new Promise(r => setTimeout(r, 500));
                    report.fileName = newFile.name;
                    report.fileBlob = newFile;
                    report.uploadDate = new Date().toLocaleDateString();
                    alert('Report replaced (temporary demo update).');
                    applyFilters();
                }
            };
            fileInput.click();
            return;
        }
    });

    // Modal close handling
    closeModalBtn.addEventListener('click', () => detailsModal.classList.add('hidden'));
    detailsModal.addEventListener('click', (e) => { if (e.target === detailsModal) detailsModal.classList.add('hidden'); });

    // ----- Future API integration placeholder -----
    // Example to fetch farmers & appointments:
    // fetch('/api/admin/farmers', { headers: { Authorization: `Bearer ${token}` } })
    //   .then(r => r.json())
    //   .then(data => { demoFarmers = data; populateFarmers(); })
    //   .catch(err => console.error('Failed to load farmers', err));
    // Similar calls for appointments and existing reports would replace the demo arrays.
});
