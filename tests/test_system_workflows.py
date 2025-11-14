import json
import pytest
from app import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- System Test 1: Customer & Ticket Workflow (Epic 2 -> Epic 4) ---

def test_system_customer_to_ticket_workflow(client, mocker):
    """
    Tests creating a customer (Epic 2) and then creating a ticket (Epic 4) for them.
    This is a true System Test.
    """
    mock_db = mocker.MagicMock()
    mocker.patch('app.get_db', return_value=mock_db)
    
    # --- Mocking for Step 1: Create Customer (and Loyalty Profile) ---
    mock_cust_ref = mocker.MagicMock()
    mock_cust_ref.id = "new-cust-system-test"
    
    mock_loyalty_ref = mocker.MagicMock()
    mock_loyalty_ref.id = "loyalty-system-test"

    # Mock the two document() calls in create_customer
    def doc_side_effect(path=None):
        if path == "new-cust-system-test":
            return mock_cust_ref
        return mock_loyalty_ref if path is None else mock_cust_ref

    mock_db.collection('customers').document.return_value = mock_cust_ref
    mock_db.batch.return_value = mocker.MagicMock() # Mock the batch
    
    # === STEP 1: CREATE A NEW CUSTOMER (from Epic 2) ===
    customer_data = {'name': 'System Test User', 'email': 'system@test.com'}
    response_cust = client.post('/api/customer', json=customer_data)
    
    assert response_cust.status_code == 201
    new_customer_id = response_cust.json['id']
    assert new_customer_id == "new-cust-system-test"

    # --- Mocking for Step 2: Create Ticket ---
    mock_ticket_ref = mocker.MagicMock()
    mock_ticket_ref.id = "new-ticket-system-test"
    # We must reset the side_effect for the new mock
    mock_db.collection.return_value.document = mocker.MagicMock(return_value=mock_ticket_ref)

    # === STEP 2: CREATE A TICKET FOR THAT CUSTOMER (from Epic 4) ===
    ticket_data = {"customer_id": new_customer_id, "issue": "System Test Issue"}
    response_ticket = client.post('/api/tickets', json=ticket_data)
    
    assert response_ticket.status_code == 201
    assert response_ticket.json['ticket_id'] == "new-ticket-system-test"
    assert response_ticket.json['customer_id'] == new_customer_id