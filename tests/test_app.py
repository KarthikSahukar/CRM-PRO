import json
import pytest
from app import app, add_points_transaction, add_points_on_purchase
from unittest.mock import MagicMock, patch
from firebase_admin import firestore


# Test 1: Test customer creation SUCCESS
def test_create_customer_success(client):
    """Test the create_customer function succeeds."""
    mock_db = MagicMock()
    mock_ref = MagicMock()
    mock_ref.id = "new-cust-123"
    mock_db.collection.return_value.document.return_value = mock_ref
    
    with patch('app.get_db', return_value=mock_db):
        customer_data = {'name': 'Test User', 'email': 'test@example.com'}
        response = client.post('/api/customer', json=customer_data)
        
        assert response.status_code == 201
        assert response.json['success'] is True
        assert response.json['id'] == "new-cust-123"

# Test 2: Test customer creation FAILURE (missing name)
def test_create_customer_missing_name(client):
    """Test the create_customer function fails validation."""
    mock_db = MagicMock()
    with patch('app.get_db', return_value=mock_db):
        customer_data = {'email': 'test@example.com'}
        response = client.post('/api/customer', json=customer_data)
    
        assert response.status_code == 400
        assert 'Name and email are required' in response.json['error']

# Test 3: Test get_customers SUCCESS
def test_get_customers_success(client):
    """Test the get_customers function succeeds."""
    mock_db = MagicMock()
    mock_doc1 = MagicMock()
    mock_doc1.id = "cust_1"
    mock_doc1.to_dict.return_value = {'name': 'Customer A'}
    mock_doc2 = MagicMock()
    mock_doc2.id = "cust_2"
    mock_doc2.to_dict.return_value = {'name': 'Customer B'}
    mock_stream = [mock_doc1, mock_doc2]
    mock_db.collection.return_value.stream.return_value = mock_stream

    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/customers')
        
        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]['name'] == 'Customer A'

# Test 4: Test the dashboard route (/)
def test_dashboard_route(client):
    """Test that the dashboard page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'

# Test 5: Test the login route (/login)
def test_login_route(client):
    """Test that the login page loads."""
    response = client.get('/login')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'
    
    # ✅ FIX: Look for the NEW text on your page
    assert b"Welcome Back" in response.data 
    assert b"Dashboard Overview" not in response.data

# Test 6: Test create_customer endpoint for 500 error
def test_create_customer_500_error(client):
    """Test the create_customer function for a generic 500 error."""
    # This is where the bug was. customer_data must be defined.
    customer_data = {'name': 'Test User', 'email': 'test@example.com'}
    
    with patch('app.get_db', side_effect=Exception("Simulated database crash")):
        
        response = client.post('/api/customer', json=customer_data)
        
        assert response.status_code == 503
        assert "Database connection failed" in response.json['error']

# Test 7: Test get_customers endpoint for 500 error
def test_get_customers_500_error(client):
    """Test the get_customers function for a generic 500 error."""
    with patch('app.get_db', side_effect=Exception("Simulated database crash")):
        
        response = client.get('/api/customers')
        
        assert response.status_code == 503
        assert "Database connection failed" in response.json['error']

# Test 8: Test get_db for FileNotFoundError
def test_get_db_file_not_found_error(client):
    """Test the get_db function for a FileNotFoundError."""
    
    # We mock get_db to return None, which is what our app.py now does
    with patch('app.get_db', return_value=None):
        
        response = client.get('/api/customers')
        
        # The app should now correctly return a 503 error
        assert response.status_code == 503
        assert "Database connection failed" in response.json['error']

# Add these new tests to the end of tests/test_app.py

def test_get_customer_details_success(client):
    """Test getting a single customer's details."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"name": "Test User", "email": "test@example.com"}
    
    # This line mocks the .get() call
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/customer/some-id')
        
        assert response.status_code == 200
        assert response.json['name'] == "Test User"

def test_get_customer_details_not_found(client):
    """Test getting a customer that does not exist."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False # Simulate a customer not being found
    
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/customer/some-id')
        
        assert response.status_code == 404
        assert "Customer not found" in response.json['error']
        
# Add these new tests to the end of tests/test_app.py

def test_update_customer_success(client):
    """Test updating a customer's details."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True # Make the document exist
    
    # Mock the .get() call
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {"name": "New Name", "phone": "123456"}
        response = client.put('/api/customer/some-id', json=update_data)

        assert response.status_code == 200
        assert response.json['success'] is True

def test_update_customer_not_found(client):
    """Test updating a customer that does not exist."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False # Make the document NOT exist
    
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {"name": "New Name"}
        response = client.put('/api/customer/some-id', json=update_data)

        assert response.status_code == 404
        assert "Customer not found" in response.json['error']

def test_update_customer_bad_request(client):
    """Test updating a customer with no data."""
    mock_db = MagicMock() # This test shouldn't even reach the db
    
    with patch('app.get_db', return_value=mock_db):
        # Send an empty JSON object
        response = client.put('/api/customer/some-id', json={})

        assert response.status_code == 400
        assert "No update data provided" in response.json['error']

# Add these new tests to the end of tests/test_app.py

def test_delete_customer_success(client):
    """Test deleting a customer successfully."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True # Make the document exist
    
    # Mock the .get() call
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.delete('/api/customer/some-id')
        
        assert response.status_code == 200
        assert response.json['success'] is True

def test_delete_customer_not_found(client):
    """Test deleting a customer that does not exist."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False # Make the document NOT exist
    
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.delete('/api/customer/some-id')
        
        assert response.status_code == 404
        assert "Customer not found" in response.json['error']
# --- Tests for Epic 3.1: Capture new leads ---

def test_capture_lead_success(client):
    """Test the capture_lead function succeeds."""
    mock_db = MagicMock()
    mock_ref = MagicMock()
    mock_ref.id = "new-lead-456"
    # Note: Use document().set() in app.py, so we mock the doc reference
    mock_db.collection.return_value.document.return_value = mock_ref 

    with patch('app.get_db', return_value=mock_db):
        lead_data = {'name': 'Test Lead', 'email': 'lead@example.com', 'source': 'Web Form'}
        response = client.post('/api/lead', json=lead_data)

        assert response.status_code == 201
        assert response.json['success'] is True
        assert response.json['id'] == "new-lead-456"
        
def test_capture_lead_missing_data(client):
    """Test the capture_lead function fails validation."""
    mock_db = MagicMock()
    with patch('app.get_db', return_value=mock_db):
        # Missing 'source'
        lead_data = {'name': 'Test Lead', 'email': 'lead@example.com'}
        response = client.post('/api/lead', json=lead_data)
    
        assert response.status_code == 400
        assert 'Name, email, and source are required' in response.json['error']

def test_capture_lead_500_error(client):
    """Test the capture_lead function for a generic 500 error."""
    lead_data = {'name': 'Test Lead', 'email': 'lead@example.com', 'source': 'Web Form'}
    
    with patch('app.get_db', side_effect=Exception("Simulated lead database crash")):
        
        response = client.post('/api/lead', json=lead_data)
        
        assert response.status_code == 503
        assert "Database connection failed" in response.json['error']
# --- Tests for Epic 3.2: Convert lead to opportunity ---

def test_convert_lead_success(client):
    """Test the convert_lead_to_opportunity function succeeds."""
    # Use from unittest.mock import MagicMock, patch if needed here, but it's already imported at the top
    mock_db = MagicMock()

    # Mock the existing lead document
    mock_lead_doc = MagicMock()
    mock_lead_doc.exists = True
    mock_lead_doc.to_dict.return_value = {
        'name': 'Convert Lead',
        'email': 'convert@example.com',
        'source': 'Web Form',
        'status': 'New'
    }

    # Mock Firestore document references
    lead_ref_mock = MagicMock(id='lead-to-convert', get=lambda: mock_lead_doc, update=MagicMock())
    opp_ref_mock = MagicMock(id='new-opp-789', set=MagicMock())

    # Simulate multiple .document() calls dynamically
    def document_side_effect(doc_id=None):
        if doc_id == 'lead-to-convert':
            return lead_ref_mock
        else:
            return opp_ref_mock

    mock_db.collection.return_value.document.side_effect = document_side_effect

    with patch('app.get_db', return_value=mock_db):
        response = client.post('/api/lead/lead-to-convert/convert')

        assert response.status_code == 200
        assert response.json['success'] is True
        assert "converted" in response.json['message']
        assert response.json['opportunity_id'] == "new-opp-789"

        # Verify the lead was updated with the correct fields
        lead_ref_mock.update.assert_called_once_with({
            'status': 'Converted',
            'convertedAt': firestore.SERVER_TIMESTAMP 
        })
        opp_ref_mock.set.assert_called_once()


def test_convert_lead_not_found(client):
    """Test the convert_lead_to_opportunity function fails if lead is missing."""
    mock_db = MagicMock()
    mock_lead_doc = MagicMock()
    mock_lead_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_lead_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.post('/api/lead/non-existent-lead/convert')
        
        assert response.status_code == 404
        assert 'Lead not found' in response.json['error']

def test_convert_lead_500_error(client):
    """Test the convert_lead_to_opportunity function for a generic 500 error."""
    with patch('app.get_db', side_effect=Exception("Simulated conversion crash")):
        response = client.post('/api/lead/any-id/convert')
        
        assert response.status_code == 503
        assert "Database connection failed" in response.json['error']
# --- Tests for Epic 3.3: Assign lead to sales rep ---

def test_assign_lead_success(client):
    """Test the assign_lead function succeeds."""
    mock_db = MagicMock()
    mock_lead_doc = MagicMock()
    mock_lead_doc.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = mock_lead_doc
    
    with patch('app.get_db', return_value=mock_db):
        assignment_data = {'rep_id': 'sales-rep-1', 'rep_name': 'Alice Smith'}
        response = client.put('/api/lead/lead-to-assign/assign', json=assignment_data)
        
        assert response.status_code == 200
        assert response.json['success'] is True
        assert "assigned to Alice Smith" in response.json['message']
        
        # Verify the lead was updated with the correct data
        mock_db.collection.return_value.document.return_value.update.assert_called_once_with({
            'assigned_to_id': 'sales-rep-1',
            'assigned_to_name': 'Alice Smith',
            'assignedAt': firestore.SERVER_TIMESTAMP 
        })
        
def test_assign_lead_missing_rep_id(client):
    """Test the assign_lead function fails if rep_id is missing."""
    mock_db = MagicMock()
    
    with patch('app.get_db', return_value=mock_db):
        assignment_data = {'rep_name': 'Alice Smith'} 
        response = client.put('/api/lead/lead-to-assign/assign', json=assignment_data)
    
        assert response.status_code == 400
        assert 'Sales rep ID (rep_id) is required' in response.json['error']

def test_assign_lead_not_found(client):
    """Test the assign_lead function fails if lead is missing."""
    mock_db = MagicMock()
    mock_lead_doc = MagicMock()
    mock_lead_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_lead_doc
    
    with patch('app.get_db', return_value=mock_db):
        assignment_data = {'rep_id': 'sales-rep-1'}
        response = client.put('/api/lead/non-existent-lead/assign', json=assignment_data)
        
        assert response.status_code == 404
        assert 'Lead not found' in response.json['error']
# --- Tests for Epic 3.4: Track opportunity status (Open, Won, Lost) ---

def test_update_opportunity_status_success(client):
    """Test updating the status of an opportunity to a valid stage."""
    mock_db = MagicMock()
    mock_opp_doc = MagicMock()
    mock_opp_doc.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = mock_opp_doc
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {'stage': 'Negotiation'}
        response = client.put('/api/opportunity/opp-123/status', json=update_data)
        
        assert response.status_code == 200
        assert response.json['success'] is True
        assert "Negotiation" in response.json['message']
        
        # Verify the update call includes the stage and updated timestamp
        mock_db.collection.return_value.document.return_value.update.assert_called_once_with({
            'stage': 'Negotiation',
            'updatedAt': firestore.SERVER_TIMESTAMP 
        })

def test_update_opportunity_status_won_closure(client):
    """Test updating the status to 'Won' includes the closedAt timestamp."""
    mock_db = MagicMock()
    mock_opp_doc = MagicMock()
    mock_opp_doc.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = mock_opp_doc
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {'stage': 'Won'}
        client.put('/api/opportunity/opp-123/status', json=update_data)
        
        # Verify the update call includes both the stage and closedAt timestamp
        mock_db.collection.return_value.document.return_value.update.assert_called_once_with({
            'stage': 'Won',
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'closedAt': firestore.SERVER_TIMESTAMP 
        })

def test_update_opportunity_status_invalid(client):
    """Test updating the status with an invalid stage fails with 400."""
    mock_db = MagicMock() 
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {'stage': 'Black Hole'}
        response = client.put('/api/opportunity/opp-123/status', json=update_data)
        
        assert response.status_code == 400
        assert 'Invalid stage provided' in response.json['error']

def test_update_opportunity_status_not_found(client):
    """Test updating the status fails if the opportunity is missing."""
    mock_db = MagicMock()
    mock_opp_doc = MagicMock()
    mock_opp_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_opp_doc
    
    with patch('app.get_db', return_value=mock_db):
        update_data = {'stage': 'Lost'}
        response = client.put('/api/opportunity/non-existent-opp/status', json=update_data)
        
        assert response.status_code == 404
        assert 'Opportunity not found' in response.json['error']

# --- Tests for Epic 4 & 5 helper endpoints ---

def test_get_loyalty_profile_success(client):
    """Loyalty profile retrieval returns profile data."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {'points': 200, 'tier': 'Silver'}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/loyalty/customer-123')

    assert response.status_code == 200
    assert response.json['tier'] == 'Silver'


def test_get_loyalty_profile_not_found(client):
    """Loyalty profile retrieval returns 404 when missing."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/loyalty/customer-unknown')

    assert response.status_code == 404
    assert "Loyalty profile not found" in response.json['error']


def test_redeem_points_success(client):
    """Redeeming points returns updated balance."""
    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value = MagicMock()
    mock_db.transaction.return_value = MagicMock()

    with patch('app.get_db', return_value=mock_db), \
         patch('app.redeem_transaction', return_value=80):
        response = client.post('/api/loyalty/customer-123/redeem', json={'points_to_redeem': 20})

    assert response.status_code == 200
    assert response.json['new_points_balance'] == 80


def test_redeem_points_insufficient(client):
    """Redeeming with insufficient points surfaces 400."""
    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value = MagicMock()
    mock_db.transaction.return_value = MagicMock()

    with patch('app.get_db', return_value=mock_db), \
         patch('app.redeem_transaction', side_effect=ValueError("Insufficient points")):
        response = client.post('/api/loyalty/customer-123/redeem', json={'points_to_redeem': 200})

    assert response.status_code == 400
    assert "Insufficient points" in response.json['error']


def test_use_referral_success(client):
    """Referral usage awards points to referrer."""
    mock_db = MagicMock()
    loyalty_collection = MagicMock()
    mock_db.collection.return_value = loyalty_collection

    referrer_doc = MagicMock()
    referrer_doc.id = 'referrer-1'
    loyalty_collection.where.return_value.limit.return_value.stream.return_value = [referrer_doc]

    referrer_ref = MagicMock()
    loyalty_collection.document.return_value = referrer_ref

    with patch('app.get_db', return_value=mock_db):
        response = client.post('/api/loyalty/new-user/use-referral', json={'referral_code': 'CODE123'})

    assert response.status_code == 200
    referrer_ref.update.assert_called_once_with({'points': firestore.Increment(100)})


def test_use_referral_invalid_code(client):
    """Invalid referral code returns 404."""
    mock_db = MagicMock()
    loyalty_collection = MagicMock()
    mock_db.collection.return_value = loyalty_collection
    loyalty_collection.where.return_value.limit.return_value.stream.return_value = []

    with patch('app.get_db', return_value=mock_db):
        response = client.post('/api/loyalty/new-user/use-referral', json={'referral_code': 'CODE123'})

    assert response.status_code == 404
    assert "Invalid referral code" in response.json['error']


def test_simulate_purchase_success(client):
    """Simulate purchase awards points and reports tier."""
    mock_db = MagicMock()

    with patch('app.get_db', return_value=mock_db), \
         patch('app.add_points_on_purchase', return_value={"new_points": 120, "new_tier": "Silver"}):
        response = client.post('/api/simulate-purchase', json={'customer_id': 'cust-1', 'amount': 50})

    assert response.status_code == 200
    assert response.json['new_points_balance'] == 120
    assert response.json['new_tier'] == "Silver"


def test_simulate_purchase_profile_missing(client):
    """Simulated purchase returns 404 when loyalty profile is missing."""
    mock_db = MagicMock()

    with patch('app.get_db', return_value=mock_db), \
         patch('app.add_points_on_purchase', return_value=None):
        response = client.post('/api/simulate-purchase', json={'customer_id': 'cust-1', 'amount': 10})

    assert response.status_code == 404
    assert "Loyalty profile not found" in response.json['error']


def test_referral_code_generation():
    """
    Test the helper function directly to boost coverage.
    """
    from app import generate_referral_code

    code1 = generate_referral_code("Kaveri Sharma")
    assert code1.startswith("KAVER")
    assert "-" in code1

    code2 = generate_referral_code("")
    assert code2.startswith("CRM-")


def test_redeem_points_missing_payload(client):
    """Redeem endpoint returns 400 when payload missing."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/loyalty/cust-1/redeem', json={})
    assert response.status_code == 400
    assert "points_to_redeem" in response.json['error']


def test_simulate_purchase_invalid_amount(client):
    """Simulated purchase rejects non-numeric amount."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/simulate-purchase', json={'customer_id': 'cust-1', 'amount': 'abc'})
    assert response.status_code == 400
    assert "amount must be a number" in response.json['error']


def test_simulate_purchase_missing_customer(client):
    """Simulated purchase requires customer_id."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/simulate-purchase', json={'amount': 10})
    assert response.status_code == 400
    assert "customer_id is required" in response.json['error']


def test_use_referral_self_error(client):
    """Referral endpoint blocks self-referral."""
    mock_db = MagicMock()
    loyalty_collection = MagicMock()
    mock_db.collection.return_value = loyalty_collection

    mock_doc = MagicMock()
    mock_doc.id = 'cust-1'
    loyalty_collection.where.return_value.limit.return_value.stream.return_value = [mock_doc]

    with patch('app.get_db', return_value=mock_db):
        response = client.post('/api/loyalty/cust-1/use-referral', json={'referral_code': 'CODE123'})

    assert response.status_code == 400
    assert "Cannot refer yourself" in response.json['error']


def test_redeem_points_invalid_integer(client):
    """Redeem points requires positive integer."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/loyalty/cust-1/redeem', json={'points_to_redeem': -10})
    assert response.status_code == 400
    assert "positive integer" in response.json['error']


def test_simulate_purchase_negative_amount(client):
    """Simulated purchase rejects non-positive amounts."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/simulate-purchase', json={'customer_id': 'cust-1', 'amount': 0})
    assert response.status_code == 400
    assert "greater than zero" in response.get_json()['error']


def test_simulate_purchase_database_failure(client):
    """Simulated purchase propagates database failure as 503."""
    with patch('app.get_db', side_effect=Exception("firestore down")):
        response = client.post('/api/simulate-purchase', json={'customer_id': 'cust-1', 'amount': 10})
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


def test_use_referral_missing_code(client):
    """Referral endpoint requires code in payload."""
    with patch('app.get_db', return_value=MagicMock()):
        response = client.post('/api/loyalty/cust-2/use-referral', json={})
    assert response.status_code == 400
    assert "Referral code required" in response.get_json()['error']


def test_add_points_on_purchase_upgrade_and_exception():
    """Directly exercise add_points_on_purchase helper for coverage."""
    mock_db = MagicMock()
    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    mock_transaction = MagicMock()
    mock_db.transaction.return_value = mock_transaction

    with patch('app.add_points_transaction', return_value={"new_points": 1200, "new_tier": "Silver"}):
        result = add_points_on_purchase(mock_db, "cust-1", 100)
    assert result['new_tier'] == "Silver"

    with patch('app.add_points_transaction', side_effect=Exception("boom")):
        result = add_points_on_purchase(mock_db, "cust-2", 50)
    assert result is None


def test_convert_lead_db_failure(client):
    """DB failure during convert results in 503."""
    with patch('app.get_db', side_effect=Exception("db down")):
        response = client.post('/api/lead/lead-1/convert')
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


def test_assign_lead_db_failure(client):
    """DB failure during assign returns 503."""
    with patch('app.get_db', side_effect=Exception("db down")):
        response = client.put('/api/lead/lead-1/assign', json={'rep_id': '123'})
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


def test_update_opportunity_db_failure(client):
    """DB failure during opportunity update returns 503."""
    with patch('app.get_db', side_effect=Exception("db down")):
        response = client.put('/api/opportunity/opp-1/status', json={'stage': 'Won'})
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


def test_loyalty_profile_db_failure(client):
    """DB failure while fetching loyalty profile returns 503."""
    with patch('app.get_db', side_effect=Exception("db down")):
        response = client.get('/api/loyalty/cust-1')
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


def test_tickets_db_failure(client):
    """DB failure when fetching tickets returns 503."""
    with patch('app.get_db', side_effect=Exception("db down")):
        response = client.get('/api/tickets')
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


# --- NEW TESTS TO BOOST COVERAGE TO 75% ---

def test_tier_upgrade_logic(client):
    """
    Test the specific branches for Silver and Gold upgrades.
    Hits the 'elif' blocks in add_points_transaction.
    """
    from app import add_points_transaction

    mock_transaction = MagicMock()
    mock_ref = MagicMock()

    mock_snapshot_silver = MagicMock()
    mock_snapshot_silver.exists = True
    mock_snapshot_silver.to_dict.return_value = {'points': 0, 'tier': 'Bronze'}
    mock_ref.get.return_value = mock_snapshot_silver

    add_points_transaction(mock_transaction, mock_ref, 600)
    mock_transaction.update.assert_called_with(mock_ref, {'points': 600, 'tier': 'Silver'})

    mock_snapshot_gold = MagicMock()
    mock_snapshot_gold.exists = True
    mock_snapshot_gold.to_dict.return_value = {'points': 1900, 'tier': 'Silver'}
    mock_ref.get.return_value = mock_snapshot_gold

    add_points_transaction(mock_transaction, mock_ref, 200)
    mock_transaction.update.assert_called_with(mock_ref, {'points': 2100, 'tier': 'Gold'})


def test_opportunity_closure_logic(client):
    """
    Ensure 'closedAt' timestamp is added for terminal stages.
    FIXED: We verify the calls sequentially so we don't mix up arguments.
    """
    mock_db = MagicMock()
    mock_opp = MagicMock()
    mock_opp.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = mock_opp

    with patch('app.get_db', return_value=mock_db):
        client.put('/api/opportunity/opp-1/status', json={'stage': 'Won'})

        update_mock = mock_db.collection.return_value.document.return_value.update
        assert update_mock.called
        args, kwargs = update_mock.call_args
        data = args[0] if args else kwargs
        assert data['stage'] == 'Won'
        assert 'closedAt' in data

        client.put('/api/opportunity/opp-1/status', json={'stage': 'Negotiation'})

        args, kwargs = update_mock.call_args
        data = args[0] if args else kwargs
        assert data['stage'] == 'Negotiation'
        assert 'closedAt' not in data


def test_html_routes_rendering(client):
    """
    Cover the HTML render routes.
    """
    response_login = client.get('/login')
    assert response_login.status_code == 200
    assert b"<h2>CRM Login</h2>" in response_login.data
    assert b"Dashboard Overview" not in response_login.data # Check dashboard content is NOT rendered

    response_cust = client.get('/customers')
    assert response_cust.status_code == 200

# --- NEW TESTS FOR EPIC 6: Dashboards & KPIs ---

def test_get_sales_kpis_success(client, mocker):
    """Test the get_sales_kpis function returns correct aggregation."""
    mock_db = mocker.MagicMock()

    # Create mock opportunities data
    mock_opportunity_data = [
        # Won, $100.00
        mocker.MagicMock(to_dict=lambda: {'stage': 'Won', 'amount': 100.00}), 
        # Lost, $50.00
        mocker.MagicMock(to_dict=lambda: {'stage': 'Lost', 'amount': 50.00}), 
        # Negotiation, $25.00 (Open)
        mocker.MagicMock(to_dict=lambda: {'stage': 'Negotiation', 'amount': 25.00}), 
        # Won, $15.50
        mocker.MagicMock(to_dict=lambda: {'stage': 'Won', 'amount': 15.50}),
        # Qualification, $0.00 (Open)
        mocker.MagicMock(to_dict=lambda: {'stage': 'Qualification', 'amount': 0.00}),
    ]

    mock_db.collection.return_value.stream.return_value = mock_opportunity_data
    mocker.patch('app.get_db', return_value=mock_db)

    response = client.get('/api/sales-kpis')

    assert response.status_code == 200
    data = response.get_json()

    # Expected calculations:
    # Total Opps: 5
    # Won Opps: 2
    # Lost Opps: 1
    # Open Opps: 5 - (2 + 1) = 2
    # Total Revenue Won: 100.00 + 15.50 = 115.50

    assert data['total_opportunities'] == 5
    assert data['won_opportunities'] == 2
    assert data['open_opportunities'] == 2
    assert data['total_revenue_won'] == 115.50

def test_get_sales_kpis_database_failure(client, mocker):
    """Test the get_sales_kpis function returns 503 on database failure."""
    mocker.patch('app.get_db', side_effect=Exception("DB connection failed"))
    
    response = client.get('/api/sales-kpis')
    
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']


# --- Additional test cases to increase coverage above 75% ---

def test_generate_referral_code():
    """Test the generate_referral_code function."""
    from app import generate_referral_code
    code = generate_referral_code("Alice")
    assert code.startswith("ALICE-")
    assert len(code.split("-")[1]) == 4


def test_add_points_on_purchase_tier_upgrade(monkeypatch):
    """Test add_points_on_purchase with tier upgrade."""
    from app import add_points_on_purchase

    class FakeRef:
        pass

    class FakeDB:
        def collection(self, *_):
            return self
        def document(self, *_):
            return FakeRef()
        def transaction(self): 
            return None

    def fake_add_points_transaction(tx, ref, pts):
        return {"new_points": 600, "new_tier": "Silver"}

    monkeypatch.setattr("app.add_points_transaction", fake_add_points_transaction)

    result = add_points_on_purchase(FakeDB(), "cust-1", 600)
    assert result["new_tier"] == "Silver"


def test_ticket_metrics_non_datetime(monkeypatch, client):
    """Test ticket metrics with non-datetime timestamps."""
    from app import app
    from datetime import datetime, timezone

    class FakeDoc:
        def to_dict(self):
            class FakeTS:
                def astimezone(self, *_): 
                    return datetime(2024, 1, 1, tzinfo=timezone.utc)
            return {
                "status": "Closed",
                "created_at": FakeTS(),
                "resolved_at": FakeTS(),
            }

    class FakeDB:
        def collection(self, *_): 
            return self
        def stream(self): 
            return [FakeDoc()]

    monkeypatch.setattr("app.get_db_or_raise", lambda: FakeDB())
    response = client.get("/api/ticket-metrics")
    assert response.status_code == 200
