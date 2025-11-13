// static/js/script.js
// Clean, merged, safe version of the CRM front-end logic
// Preserves all existing functionality and adds ticket metrics + chart rendering
// Dynamically loads Chart.js only when needed to avoid adding separate files

/* =========================
   Utility helpers & config
   ========================= */

function toggleTheme() {
    const html = document.documentElement;
    html.classList.toggle('dark-mode');
    const theme = html.classList.contains('dark-mode') ? 'dark' : 'light';
    localStorage.setItem("theme", theme);
}

function displayError(endpoint) {
    console.error(`Error fetching data from ${endpoint}`);
    const elements = document.querySelectorAll('.stat-card p');
    elements.forEach(el => {
        if (el.textContent === 'Loading...' || el.textContent === '0') {
            el.textContent = 'Err';
        }
    });
}

function escapeHTML(str = '') {
    return String(str).replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[m];
    });
}

/* =========================
   Chart loader utility
   ========================= */

/**
 * Loads Chart.js from CDN only when needed.
 * Returns a Promise that resolves when Chart is available.
 */
function loadChartJsIfNeeded() {
    return new Promise((resolve, reject) => {
        if (window.Chart) return resolve(window.Chart);

        const script = document.createElement('script');
        // Use a reliable CDN; version can be changed safely later
        script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
        script.defer = true;
        script.onload = () => {
            if (window.Chart) resolve(window.Chart);
            else reject(new Error("Chart loaded but window.Chart is not available"));
        };
        script.onerror = () => reject(new Error("Failed to load Chart.js library"));
        document.head.appendChild(script);
    });
}

/* =========================
   KPI Fetchers (Dashboard)
   ========================= */

async function fetchCustomerKPIs() {
    try {
        const response = await fetch('/api/customer-kpis');
        if (!response.ok) throw new Error('Failed to fetch customer KPIs: ' + response.statusText);
        const data = await response.json();

        const totalCustomersElement = document.getElementById('stat-total-customers');
        if (totalCustomersElement) {
            // API returns total_customers
            totalCustomersElement.textContent = data.total_customers ?? 0;
        }

        const newCustomersElement = document.getElementById('stat-new-customers-30d');
        if (newCustomersElement) {
            newCustomersElement.textContent = data.new_customers_last_30_days ?? 0;
        }
    } catch (err) {
        console.error("Error loading Customer KPIs:", err);
        const newCustomersElement = document.getElementById('stat-new-customers-30d');
        if (newCustomersElement) newCustomersElement.textContent = 'Error';
    }
}

async function fetchOpenTickets() {
    try {
        const response = await fetch('/api/tickets');
        if (!response.ok) throw new Error("Failed to fetch tickets");
        const tickets = await response.json();

        const openTickets = Array.isArray(tickets) ? tickets.filter(t => t.status === 'Open').length : 0;
        const openTicketsElement = document.getElementById('stat-open-tickets');
        if (openTicketsElement) openTicketsElement.textContent = openTickets;
    } catch (err) {
        console.error("Error loading Open Tickets:", err);
        const openTicketsElement = document.getElementById('stat-open-tickets');
        if (openTicketsElement) openTicketsElement.textContent = 'Error';
    }
}

/* =========================
   Ticket Metrics & Chart
   ========================= */

let _resolutionChartInstance = null;

// Draw the Resolution Time Trend Chart (Dynamic)
function renderResolutionChart(labels, values) {
    const canvas = document.getElementById('resolution-chart');
    if (!canvas) return;

    // Destroy previous chart (important when re-loading)
    if (window.resolutionChart) {
        window.resolutionChart.destroy();
    }

    const ctx = canvas.getContext("2d");

    window.resolutionChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Avg Resolution (hrs)",
                data: values,
                borderWidth: 3,
                tension: 0.3,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,   // <-- makes graph smaller
        }
    });
}


async function fetchTicketMetrics() {
    const avgResolutionElement = document.getElementById('stat-avg-resolution');

    try {
        const response = await fetch('/api/ticket-metrics');
        const data = await response.json();

        if (avgResolutionElement)
            avgResolutionElement.textContent = `${data.avg_resolution_hours.toFixed(1)} hrs`;

        // Render dynamic chart
        renderResolutionChart(data.trend_labels, data.trend_values);

    } catch (err) {
        console.error("Metrics error:", err);
        if (avgResolutionElement) avgResolutionElement.textContent = 'Err';
    }
}

  

function initCustomersPage() {
    // Guard elements (some may not exist if not on page)
    const addCustomerBtn = document.getElementById("add-customer-btn");
    const modal = document.getElementById("customer-modal");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const customerForm = document.getElementById("customer-form");
    const customersTableBody = document.getElementById("customers-table-body");
    const modalTitle = document.getElementById("modal-title");
    const customerIdField = document.getElementById("customer-id");

    if (!customerForm || !customersTableBody) {
        // Nothing to init
        return;
    }

    const openModal = () => {
        if (modalTitle) modalTitle.textContent = "Add New Customer";
        customerForm.reset();
        if (customerIdField) customerIdField.value = "";
        if (modal) modal.style.display = "flex";
    };

    const closeModal = () => {
        if (modal) modal.style.display = "none";
    };

    if (addCustomerBtn) addCustomerBtn.addEventListener("click", openModal);
    if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeModal);
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeModal();
        });
    }

    async function loadCustomers() {
        try {
            const response = await fetch('/api/customers');
            if (!response.ok) throw new Error('Failed to fetch customers');
            const customers = await response.json();

            customersTableBody.innerHTML = "";
            if (!Array.isArray(customers) || customers.length === 0) {
                customersTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No customers found.</td></tr>';
                return;
            }

            customers.forEach(cust => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHTML(cust.name)}</td>
                    <td>${escapeHTML(cust.email)}</td>
                    <td>${escapeHTML(cust.phone || '')}</td>
                    <td>${escapeHTML(cust.company || '')}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm action-btn edit-btn" data-id="${cust.id}">Edit</button>
                        <button class="btn btn-danger btn-sm action-btn delete-btn" data-id="${cust.id}">Delete</button>
                    </td>
                `;
                customersTableBody.appendChild(row);
            });
        } catch (err) {
            console.error(err);
            customersTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Error loading customers.</td></tr>`;
        }
    }

    customerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById("cust-name").value,
            email: document.getElementById("cust-email").value,
            phone: document.getElementById("cust-phone").value,
            company: document.getElementById("cust-company").value
        };

        const customerId = customerIdField ? customerIdField.value : "";
        let url = '/api/customer';
        let method = 'POST';
        if (customerId) {
            url = `/api/customer/${customerId}`;
            method = 'PUT';
        }

        try {
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (resp.ok) {
                alert(customerId ? 'Customer updated!' : 'Customer created!');
                customerForm.reset();
                closeModal();
                await loadCustomers();
            } else {
                const errorData = await resp.json();
                alert(`Error: ${errorData.error || resp.statusText}`);
            }
        } catch (err) {
            console.error('Form submission error:', err);
            alert('An error occurred. Please try again.');
        }
    });

    customersTableBody.addEventListener('click', async (e) => {
        const target = e.target;
        const customerId = target.getAttribute && target.getAttribute('data-id');
        if (!customerId) return;

        if (target.classList.contains('delete-btn')) {
            if (!confirm('Are you sure you want to delete this customer?')) return;
            try {
                const r = await fetch(`/api/customer/${customerId}`, { method: 'DELETE' });
                if (r.ok) {
                    alert('Customer deleted.');
                    await loadCustomers();
                } else {
                    const err = await r.json();
                    alert(`Error: ${err.error}`);
                }
            } catch (err) {
                console.error('Delete error:', err);
                alert('An error occurred.');
            }
        }

        if (target.classList.contains('edit-btn')) {
            try {
                const r = await fetch(`/api/customer/${customerId}`);
                if (!r.ok) throw new Error('Customer not found');
                const customer = await r.json();
                if (modalTitle) modalTitle.textContent = "Edit Customer";
                if (customerIdField) customerIdField.value = customerId;
                document.getElementById("cust-name").value = customer.name || '';
                document.getElementById("cust-email").value = customer.email || '';
                document.getElementById("cust-phone").value = customer.phone || '';
                document.getElementById("cust-company").value = customer.company || '';
                if (modal) modal.style.display = "flex";
            } catch (err) {
                console.error('Edit error:', err);
                alert('Could not load customer data.');
            }
        }
    });

    // initial load
    loadCustomers();
}

/* =========================
   Tickets page logic
   ========================= */

function initTicketsPage() {
    const ticketForm = document.getElementById('ticket-form');
    const customerSelect = document.getElementById('ticket-customer-select');
    const issueInput = document.getElementById('ticket-issue');
    const prioritySelect = document.getElementById('ticket-priority');
    const ticketStatus = document.getElementById('ticket-status');
    const ticketList = document.getElementById('ticket-list');

    if (!ticketList) return;

    const setTicketStatus = (message, isError = false) => {
        if (!ticketStatus) return;
        ticketStatus.innerHTML = '';
        const span = document.createElement('span');
        span.textContent = message;
        span.style.color = isError ? 'red' : 'inherit';
        ticketStatus.appendChild(span);
    };

    const populateCustomers = async () => {
        if (!customerSelect) return;
        customerSelect.innerHTML = '<option value="">Loading customers...</option>';
        try {
            const r = await fetch('/api/customers');
            if (!r.ok) throw new Error('Failed to load customers');
            const customers = await r.json();
            if (!Array.isArray(customers) || customers.length === 0) {
                customerSelect.innerHTML = '<option value="">No customers found</option>';
                return;
            }
            customerSelect.innerHTML = '<option value="">Select a customer</option>';
            customers.forEach(customer => {
                const option = document.createElement('option');
                option.value = customer.id;
                option.textContent = customer.name || 'Unnamed';
                customerSelect.appendChild(option);
            });
        } catch (err) {
            console.error('Failed to populate customers:', err);
            customerSelect.innerHTML = '<option value="">Error loading customers</option>';
        }
    };

    const loadTickets = async () => {
        ticketList.innerHTML = '<li>Loading tickets...</li>';
        try {
            const r = await fetch('/api/tickets');
            if (!r.ok) throw new Error('Failed to load tickets');
            const tickets = await r.json();
            if (!Array.isArray(tickets) || tickets.length === 0) {
                ticketList.innerHTML = '<li>No recent tickets found.</li>';
                return;
            }
            ticketList.innerHTML = '';
            tickets.forEach(ticket => {
                const item = document.createElement('li');
                const issue = ticket.issue || 'No issue description';
                const customer = ticket.customer_id || 'Unknown customer';
                const priority = ticket.priority || 'Medium';
                const status = ticket.status || 'Open';
                item.textContent = `${issue} — Customer: ${customer} • Priority: ${priority} • Status: ${status}`;
                ticketList.appendChild(item);
            });
        } catch (err) {
            console.error('Failed to load tickets:', err);
            ticketList.innerHTML = '<li style="color: red;">Error loading tickets.</li>';
        }
    };

    if (ticketForm) {
        ticketForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const customerId = customerSelect ? customerSelect.value : '';
            const issue = issueInput ? issueInput.value.trim() : '';
            const priority = prioritySelect ? prioritySelect.value : 'Medium';

            if (!customerId) {
                setTicketStatus('Please select a customer.', true);
                return;
            }
            if (!issue) {
                setTicketStatus('Issue description is required.', true);
                return;
            }

            setTicketStatus('Creating ticket...');
            try {
                const resp = await fetch('/api/tickets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ customer_id: customerId, issue, priority })
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Failed to create ticket');
                setTicketStatus(`Ticket created! ID: ${data.ticket_id}`);
                ticketForm.reset();
                if (prioritySelect) prioritySelect.value = 'Medium';
                await loadTickets();
            } catch (err) {
                console.error('Error creating ticket:', err);
                setTicketStatus(`Error creating ticket: ${err.message}`, true);
            }
        });
    }

    // initial
    populateCustomers();
    loadTickets();
}

/* =========================
   Leads & Loyalty handlers
   (kept intact from original)
   ========================= */

function initLeadsAndLoyalty() {
    const leadForm = document.getElementById("lead-form");
    if (leadForm) {
        leadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const leadData = {
                name: document.getElementById("lead-name").value,
                email: document.getElementById("lead-email").value,
                source: document.getElementById("lead-source").value,
                status: "New"
            };

            const response = await fetch('/api/lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(leadData)
            });

            if (response.ok) {
                alert('New Lead captured!');
                leadForm.reset();
            } else {
                const errorData = await response.json();
                alert(`Error capturing lead: ${errorData.error || response.statusText}`);
            }
        });
    }

    // customers page loyalty forms
    const loyaltyProfileForm = document.getElementById('loyalty-profile-form');
    const loyaltyOutput = document.getElementById('loyalty-output');

    const showLoyaltyResult = (message, isError = false) => {
        if (!loyaltyOutput) return;
        loyaltyOutput.innerHTML = `<pre${isError ? ' class="error"' : ''}>${message}</pre>`;
    };

    if (loyaltyProfileForm) {
        loyaltyProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const customerId = document.getElementById('loyalty-profile-customer').value.trim();
            if (!customerId) return;
            try {
                const resp = await fetch(`/api/loyalty/${encodeURIComponent(customerId)}`);
                if (!resp.ok) {
                    const errorData = await resp.json();
                    throw new Error(errorData.error || 'Failed to fetch profile');
                }
                const data = await resp.json();
                showLoyaltyResult(JSON.stringify(data, null, 2));
            } catch (err) {
                console.error('Loyalty profile fetch failed:', err);
                showLoyaltyResult(err.message, true);
            }
        });
    }

    const loyaltyPurchaseForm = document.getElementById('loyalty-purchase-form');
    if (loyaltyPurchaseForm) {
        loyaltyPurchaseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const customerId = document.getElementById('purchase-customer').value.trim();
            const amountValue = document.getElementById('purchase-amount').value;
            if (!customerId || !amountValue) return;
            try {
                const response = await fetch('/api/simulate-purchase', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ customer_id: customerId, amount: amountValue })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to simulate purchase');
                showLoyaltyResult(JSON.stringify(data, null, 2));
            } catch (err) {
                console.error('Simulate purchase failed:', err);
                showLoyaltyResult(err.message, true);
            }
        });
    }

    const loyaltyRedeemForm = document.getElementById('loyalty-redeem-form');
    if (loyaltyRedeemForm) {
        loyaltyRedeemForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const customerId = document.getElementById('redeem-customer').value.trim();
            const points = document.getElementById('redeem-points').value;
            if (!customerId || !points) return;
            try {
                const response = await fetch(`/api/loyalty/${encodeURIComponent(customerId)}/redeem`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ points_to_redeem: Number(points) })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to redeem points');
                showLoyaltyResult(JSON.stringify(data, null, 2));
            } catch (err) {
                console.error('Redeem points failed:', err);
                showLoyaltyResult(err.message, true);
            }
        });
    }

    const loyaltyReferralForm = document.getElementById('loyalty-referral-form');
    if (loyaltyReferralForm) {
        loyaltyReferralForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const customerId = document.getElementById('referral-customer').value.trim();
            const referralCode = document.getElementById('referral-code').value.trim();
            if (!customerId || !referralCode) return;
            try {
                const response = await fetch(`/api/loyalty/${encodeURIComponent(customerId)}/use-referral`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ referral_code: referralCode })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to apply referral');
                showLoyaltyResult(JSON.stringify(data, null, 2));
            } catch (err) {
                console.error('Apply referral failed:', err);
                showLoyaltyResult(err.message, true);
            }
        });
    }
}

/* =========================
   Main initialization
   ========================= */

document.addEventListener("DOMContentLoaded", async () => {
    // Theme toggling initialization
    const themeToggle = document.getElementById("theme-toggle");
    const storedTheme = localStorage.getItem("theme");
    if (storedTheme === "dark") {
        document.documentElement.classList.add("dark-mode");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            toggleTheme();
        });
    }

    // Mobile sidebar toggle
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", () => {
            document.body.classList.toggle("sidebar-open");
        });
    }

    // Page-specific initializers
    const path = window.location.pathname;

    // Dashboard root
    if (path === "/") {
        // Run KPI fetchers in parallel (non-blocking)
        fetchCustomerKPIs();
        fetchOpenTickets();

        // Ticket metrics (chart) - fetch and then (if chart element exists) load Chart.js before rendering
        // Kick it off but don't await blocking UI
        fetchTicketMetrics().catch(err => console.warn("Ticket metrics failed:", err));
    }

    // Customers page
    if (path === "/customers") {
        initCustomersPage();
    }

    // Tickets page
    if (path === "/tickets") {
        initTicketsPage();
    }

    // Always initialize leads & loyalty handlers if their forms are present
    initLeadsAndLoyalty();
});
