// Wait for the DOM to be fully loaded before running scripts
document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. THEME TOGGLE (From Epic 10) ---
    const themeToggle = document.getElementById("theme-toggle");
    
    // Check for saved theme in localStorage and apply it
    const currentTheme = localStorage.getItem("theme");
    if (currentTheme === "dark") {
        document.documentElement.classList.add("dark-mode");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            document.documentElement.classList.toggle("dark-mode");
            let theme = "light";
            if (document.documentElement.classList.contains("dark-mode")) {
                theme = "dark";
            }
            localStorage.setItem("theme", theme);
        });
    }

    // --- 2. MOBILE SIDEBAR TOGGLE ---
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", () => {
            document.body.classList.toggle("sidebar-open");
        });
    }

    // --- 3. CUSTOMER PAGE LOGIC ---
    if (window.location.pathname === '/customers') {
        const addCustomerBtn = document.getElementById("add-customer-btn");
        const modal = document.getElementById("customer-modal");
        const modalCloseBtn = document.getElementById("modal-close-btn");
        const customerForm = document.getElementById("customer-form");
        const customersTableBody = document.getElementById("customers-table-body");
        const modalTitle = document.getElementById("modal-title");
        const customerIdField = document.getElementById("customer-id");

        const openModal = () => {
            modalTitle.textContent = "Add New Customer";
            customerForm.reset();
            customerIdField.value = "";
            modal.style.display = "flex";
        };

        const closeModal = () => {
            modal.style.display = "none";
        };

        addCustomerBtn.addEventListener("click", openModal);
        modalCloseBtn.addEventListener("click", closeModal);
        
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        async function loadCustomers() {
            try {
                const response = await fetch('/api/customers');
                if (!response.ok) throw new Error('Failed to fetch customers');
                const customers = await response.json();
                
                customersTableBody.innerHTML = ""; 
                
                if (customers.length === 0) {
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
            
            const customerData = {
                name: document.getElementById("cust-name").value,
                email: document.getElementById("cust-email").value,
                phone: document.getElementById("cust-phone").value,
                company: document.getElementById("cust-company").value,
            };
            
            const customerId = customerIdField.value;
            let url = '/api/customer';
            let method = 'POST';

            if (customerId) {
                url = `/api/customer/${customerId}`;
                method = 'PUT';
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(customerData)
                });

                if (response.ok) {
                    alert(customerId ? 'Customer updated!' : 'Customer created!');
                    customerForm.reset();
                    closeModal();
                    loadCustomers();
                } else {
                    const errorData = await response.json();
                    alert(`Error: ${errorData.error}`);
                }
            } catch (err) {
                console.error('Form submission error:', err);
                alert('An error occurred. Please try again.');
            }
        });

        customersTableBody.addEventListener('click', async (e) => {
            const target = e.target;
            const customerId = target.getAttribute('data-id');

            if (!customerId) return; 

            if (target.classList.contains('delete-btn')) {
                if (!confirm('Are you sure you want to delete this customer?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/customer/${customerId}`, { method: 'DELETE' });
                    if (response.ok) {
                        alert('Customer deleted.');
                        loadCustomers();
                    } else {
                        const errorData = await response.json();
                        alert(`Error: ${errorData.error}`);
                    }
                } catch (err) {
                    console.error('Delete error:', err);
                    alert('An error occurred.');
                }
            }

            if (target.classList.contains('edit-btn')) {
                try {
                    const response = await fetch(`/api/customer/${customerId}`);
                    if (!response.ok) throw new Error('Customer not found');
                    
                    const customer = await response.json();
                    
                    modalTitle.textContent = "Edit Customer";
                    customerIdField.value = customerId;
                    document.getElementById("cust-name").value = customer.name;
                    document.getElementById("cust-email").value = customer.email;
                    document.getElementById("cust-phone").value = customer.phone || '';
                    document.getElementById("cust-company").value = customer.company || '';
                    
                    modal.style.display = "flex";
                    
                } catch (err) {
                    console.error('Edit error:', err);
                    alert('Could not load customer data.');
                }
            }
        });

        loadCustomers();
    }
    
    // --- 4. PAGE-SPECIFIC LOGIC ---
    if (window.location.pathname === '/') {
        const statTotalCustomers = document.getElementById('stat-total-customers');
        if (statTotalCustomers) {
            fetch('/api/customers')
                .then(res => res.json())
                .then(customers => {
                    statTotalCustomers.textContent = customers.length;
                })
                .catch(err => {
                    console.error('Error loading customer stat:', err);
                    statTotalCustomers.textContent = 'N/A';
                });
        }
        
        // --- Fetch Sales KPIs (Epic 6, Story 1) ---
        const statTotalOpportunities = document.getElementById('stat-total-opportunities');
        const statWonOpportunities = document.getElementById('stat-won-opportunities');
        const statTotalRevenue = document.getElementById('stat-total-revenue');

        if (statTotalOpportunities) {
            fetch('/api/sales-kpis')
                .then(res => {
                    if (!res.ok) {
                        throw new Error(`HTTP error! status: ${res.status}`);
                    }
                    return res.json();
                })
                .then(kpis => {
                    statTotalOpportunities.textContent = kpis.total_opportunities;
                    statWonOpportunities.textContent = kpis.won_opportunities;
                    // Format revenue as currency
                    statTotalRevenue.textContent = `$${kpis.total_revenue_won.toFixed(2)}`;
                })
                .catch(err => {
                    console.error('Error loading sales KPIs:', err);
                    if (statTotalOpportunities) statTotalOpportunities.textContent = 'Err';
                    if (statWonOpportunities) statWonOpportunities.textContent = 'Err';
                    if (statTotalRevenue) statTotalRevenue.textContent = 'Err';
                });
        }
        // --- End Sales KPIs Logic ---
    }

    if (window.location.pathname === '/customers') {
        const loyaltyOutput = document.getElementById('loyalty-output');
        const showLoyaltyResult = (message, isError = false) => {
            if (!loyaltyOutput) return;
            loyaltyOutput.innerHTML = `<pre${isError ? ' class="error"' : ''}>${message}</pre>`;
        };

        const loyaltyProfileForm = document.getElementById('loyalty-profile-form');
        if (loyaltyProfileForm) {
            loyaltyProfileForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const customerId = document.getElementById('loyalty-profile-customer').value.trim();
                if (!customerId) return;
                try {
                    const response = await fetch(`/api/loyalty/${encodeURIComponent(customerId)}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Failed to fetch profile');
                    }
                    const data = await response.json();
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
                        body: JSON.stringify({
                            customer_id: customerId,
                            amount: amountValue
                        })
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to simulate purchase');
                    }
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
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to redeem points');
                    }
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
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to apply referral');
                    }
                    showLoyaltyResult(JSON.stringify(data, null, 2));
                } catch (err) {
                    console.error('Apply referral failed:', err);
                    showLoyaltyResult(err.message, true);
                }
            });
        }
    }

    if (window.location.pathname === '/tickets') {
        const ticketForm = document.getElementById('ticket-form');
        const customerSelect = document.getElementById('ticket-customer-select');
        const issueInput = document.getElementById('ticket-issue');
        const prioritySelect = document.getElementById('ticket-priority');
        const ticketStatus = document.getElementById('ticket-status');
        const ticketList = document.getElementById('ticket-list');

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
                const response = await fetch('/api/customers');
                if (!response.ok) {
                    throw new Error('Failed to load customers');
                }
                const customers = await response.json();
                if (!customers.length) {
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
            if (!ticketList) return;
            ticketList.innerHTML = '<li>Loading tickets...</li>';
            try {
                const response = await fetch('/api/tickets');
                if (!response.ok) {
                    throw new Error('Failed to load tickets');
                }
                const tickets = await response.json();
                if (!tickets.length) {
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
                const customerId = customerSelect.value;
                const issue = issueInput.value.trim();
                const priority = prioritySelect.value || 'Medium';

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
                    const response = await fetch('/api/tickets', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            customer_id: customerId,
                            issue,
                            priority
                        })
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to create ticket');
                    }
                    setTicketStatus(`Ticket created! ID: ${data.ticket_id}`);
                    ticketForm.reset();
                    prioritySelect.value = 'Medium';
                    await loadTickets();
                } catch (err) {
                    console.error('Error creating ticket:', err);
                    setTicketStatus(`Error creating ticket: ${err.message}`, true);
                }
            });
        }

        populateCustomers();
        loadTickets();
    }

    // --- 5. LEAD FORM LOGIC (FROM TEAMMATE) ---
    // The lead form is currently not rendered in the main UI, but the logic is here for completeness.
    const leadForm = document.getElementById("lead-form");
    if (leadForm) {
        leadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const leadData = {
                name: document.getElementById("lead-name").value,
                email: document.getElementById("lead-email").value,
                source: document.getElementById("lead-source").value,
                status: "New" // Default status
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
    // --- END TEAMMATE'S LOGIC ---


    // --- 6. UTILITY FUNCTION ---
    function escapeHTML(str) {
        return str.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[m];
        });
    }

});