// Wait for the DOM to be fully loaded before running scripts
document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. THEME TOGGLE (From Epic 10) ---
    const themeToggle = document.getElementById("theme-toggle");
    
    // Check for saved theme in localStorage and apply it
    const currentTheme = localStorage.getItem("theme");
    if (currentTheme === "dark") {
        // We apply the class to the <html> tag (document.documentElement)
        document.documentElement.classList.add("dark-mode");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            // Toggle the .dark-mode class on the <html> tag
            document.documentElement.classList.toggle("dark-mode");

            // Save the user's preference
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
            // We toggle a class on the <body> to show/hide the sidebar
            document.body.classList.toggle("sidebar-open");
        });
    }

    // --- 3. CUSTOMER PAGE LOGIC ---
    // Only run this code if we are on the customers page
    if (window.location.pathname === '/customers') {
        const addCustomerBtn = document.getElementById("add-customer-btn");
        const modal = document.getElementById("customer-modal");
        const modalCloseBtn = document.getElementById("modal-close-btn");
        const customerForm = document.getElementById("customer-form");
        const customersTableBody = document.getElementById("customers-table-body");
        const modalTitle = document.getElementById("modal-title");
        const customerIdField = document.getElementById("customer-id");

        // Function to open the modal
        const openModal = () => {
            modalTitle.textContent = "Add New Customer";
            customerForm.reset();
            customerIdField.value = ""; // Clear ID field
            modal.style.display = "flex";
        };

        // Function to close the modal
        const closeModal = () => {
            modal.style.display = "none";
        };

        // Event listeners for modal
        addCustomerBtn.addEventListener("click", openModal);
        modalCloseBtn.addEventListener("click", closeModal);
        
        // Close modal if user clicks on the overlay
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Function to load all customers into the table
        async function loadCustomers() {
            try {
                const response = await fetch('/api/customers');
                if (!response.ok) {
                    throw new Error('Failed to fetch customers');
                }
                const customers = await response.json();
                
                customersTableBody.innerHTML = ""; // Clear "Loading..."
                
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

        // Handle Customer Form (Create & Update)
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

            // If an ID exists, we are UPDATING (PUT), not creating (POST)
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
                    loadCustomers(); // Refresh the list
                } else {
                    const errorData = await response.json();
                    alert(`Error: ${errorData.error}`);
                }
            } catch (err) {
                console.error('Form submission error:', err);
                alert('An error occurred. Please try again.');
            }
        });

        // Handle Edit and Delete buttons (Event Delegation)
        customersTableBody.addEventListener('click', async (e) => {
            const target = e.target;
            const customerId = target.getAttribute('data-id');

            if (!customerId) return; // Not a button we care about

            // Handle DELETE
            if (target.classList.contains('delete-btn')) {
                if (!confirm('Are you sure you want to delete this customer?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/customer/${customerId}`, { method: 'DELETE' });
                    if (response.ok) {
                        alert('Customer deleted.');
                        loadCustomers(); // Refresh list
                    } else {
                        const errorData = await response.json();
                        alert(`Error: ${errorData.error}`);
                    }
                } catch (err) {
                    console.error('Delete error:', err);
                    alert('An error occurred.');
                }
            }

            // Handle EDIT
            if (target.classList.contains('edit-btn')) {
                // Fetch the customer's current data
                try {
                    const response = await fetch(`/api/customer/${customerId}`);
                    if (!response.ok) throw new Error('Customer not found');
                    
                    const customer = await response.json();
                    
                    // Populate the form
                    modalTitle.textContent = "Edit Customer";
                    customerIdField.value = customerId;
                    document.getElementById("cust-name").value = customer.name;
                    document.getElementById("cust-email").value = customer.email;
                    document.getElementById("cust-phone").value = customer.phone || '';
                    document.getElementById("cust-company").value = customer.company || '';
                    
                    // Show the modal
                    modal.style.display = "flex";
                    
                } catch (err) {
                    console.error('Edit error:', err);
                    alert('Could not load customer data.');
                }
            }
        });

        // Initial load of customers on page visit
        loadCustomers();
    }
    
    // --- 4. DASHBOARD PAGE LOGIC ---
    if (window.location.pathname === '/') {
        // Load customer count
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
    }

    // --- 5. UTILITY FUNCTION ---
    // Simple function to escape HTML to prevent XSS attacks
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