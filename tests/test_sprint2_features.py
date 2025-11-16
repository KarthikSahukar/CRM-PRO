import json
import pytest
from app import app
from unittest.mock import MagicMock, patch
from firebase_admin import firestore

# --- Fixtures ---
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Tests for Epic 4: Support Tickets (Kaveri) ---

def test_create_ticket_success(client):
    """Test POST /api/tickets - success"""
    mock_db = MagicMock()
    mock_ref = MagicMock()
    mock_ref.id = "ticket-123"
    mock_db.collection.return_value.document.return_value = mock_ref
    
    with patch('app.get_db', return_value=mock_db):
        data = {"customer_id": "cust-abc", "issue": "It's broken"}
        response = client.post('/api/tickets', json=data)
        
        assert response.status_code == 201
        assert response.json['success'] is True
        assert response.json['ticket_id'] == "ticket-123"

def test_create_ticket_missing_data(client):
    """Test POST /api/tickets - failure (400)"""
    mock_db = MagicMock()
    with patch('app.get_db', return_value=mock_db):
        data = {"issue": "It's broken"} # Missing customer_id
        response = client.post('/api/tickets', json=data)
        
        assert response.status_code == 400
        assert "Missing required fields" in response.json['error']

def test_get_tickets_success(client):
    """Test GET /api/tickets - success"""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.id = "ticket-abc"
    mock_doc.to_dict.return_value = {"issue": "It's broken", "status": "Open"}
    mock_db.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [mock_doc]
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/tickets')
        
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]['issue'] == "It's broken"

# --- Tests for Epic 5: Loyalty Program (Kaveri) ---

def test_get_loyalty_profile_success(client):
    """Test GET /api/loyalty/<id> - success"""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"tier": "Bronze", "points": 100}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/loyalty/cust-abc')
        
        assert response.status_code == 200
        assert response.json['tier'] == "Bronze"

def test_get_loyalty_profile_not_found(client):
    """Test GET /api/loyalty/<id> - failure (404)"""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/loyalty/cust-abc')
        
        assert response.status_code == 404
        assert "Loyalty profile not found" in response.json['error']

def test_redeem_points_success(client):
    """Test POST /api/loyalty/<id>/redeem - success"""
    mock_db = MagicMock()
    # We patch the transactional helper function directly
    with patch('app.redeem_transaction', return_value=50) as mock_redeem:
        with patch('app.get_db', return_value=mock_db):
            data = {"points_to_redeem": 50}
            response = client.post('/api/loyalty/cust-abc/redeem', json=data)
            
            assert response.status_code == 200
            assert response.json['new_points_balance'] == 50
            mock_redeem.assert_called_once()

def test_redeem_points_insufficient(client):
    """Test POST /api/loyalty/<id>/redeem - failure (400)"""
    mock_db = MagicMock()
    # Make the transaction raise a ValueError, just like in the app
    with patch('app.redeem_transaction', side_effect=ValueError("Insufficient points")):
        with patch('app.get_db', return_value=mock_db):
            data = {"points_to_redeem": 50000}
            response = client.post('/api/loyalty/cust-abc/redeem', json=data)
            
            assert response.status_code == 400
            assert "Insufficient points" in response.json['error']

def test_use_referral_code_success(client):
    """Test POST /api/loyalty/<id>/use-referral - success"""
    mock_db = MagicMock()
    mock_referrer_doc = MagicMock()
    mock_referrer_doc.id = "referrer-id"
    # Mock the query result
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_referrer_doc]
    
    with patch('app.get_db', return_value=mock_db):
        data = {"referral_code": "FRIEND-1234"}
        # The customer_id in the URL is the NEW user
        response = client.post('/api/loyalty/new-user-id/use-referral', json=data)
        
        assert response.status_code == 200
        assert "Referral applied" in response.json['message']

def test_use_referral_code_self(client):
    """Test POST /api/loyalty/<id>/use-referral - failure (400)"""
    mock_db = MagicMock()
    mock_referrer_doc = MagicMock()
    mock_referrer_doc.id = "same-user-id" # The referrer is the same as the user
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_referrer_doc]
    
    with patch('app.get_db', return_value=mock_db):
        data = {"referral_code": "MY-OWN-CODE"}
        response = client.post('/api/loyalty/same-user-id/use-referral', json=data)
        
        assert response.status_code == 400
        assert "Cannot refer yourself" in response.json['error']

def test_simulate_purchase_success(client):
    """Test POST /api/simulate-purchase - success"""
    mock_db = MagicMock()
    # Mock the helper function this endpoint calls
    mock_result = {"new_points": 150, "new_tier": "Bronze"}
    with patch('app.add_points_on_purchase', return_value=mock_result) as mock_add_points:
        with patch('app.get_db', return_value=mock_db):
            data = {"customer_id": "cust-abc", "amount": 150}
            response = client.post('/api/simulate-purchase', json=data)
            
            assert response.status_code == 200
            assert response.json['points_added'] == 150
            assert response.json['new_points_balance'] == 150
            mock_add_points.assert_called_with(mock_db, "cust-abc", 150)

def test_simulate_purchase_not_found(client):
    """Test POST /api/simulate-purchase - failure (404)"""
    mock_db = MagicMock()
    # Mock the helper function returning None (as if profile not found)
    with patch('app.add_points_on_purchase', return_value=None):
        with patch('app.get_db', return_value=mock_db):
            data = {"customer_id": "cust-abc", "amount": 150}
            response = client.post('/api/simulate-purchase', json=data)
            
            assert response.status_code == 404
            assert "Loyalty profile not found" in response.json['error']

# --- Tests for Epic 6: Dashboards (Kavana) ---

def test_get_sales_kpis_success(client):
    """Test GET /api/sales-kpis - success"""
    mock_db = MagicMock()
    
    # Create fake opportunity data
    mock_opp1 = MagicMock()
    mock_opp1.to_dict.return_value = {"stage": "Won", "amount": 1000}
    mock_opp2 = MagicMock()
    mock_opp2.to_dict.return_value = {"stage": "Lost", "amount": 500}
    mock_opp3 = MagicMock()
    mock_opp3.to_dict.return_value = {"stage": "Negotiation", "amount": 2000}
    
    # Mock the stream() call to return our fake data
    mock_db.collection.return_value.stream.return_value = [mock_opp1, mock_opp2, mock_opp3]
    
    with patch('app.get_db', return_value=mock_db):
        response = client.get('/api/sales-kpis')
        
        assert response.status_code == 200
        assert response.json['total_opportunities'] == 3
        assert response.json['won_opportunities'] == 1
        assert response.json['open_opportunities'] == 1
        assert response.json['total_revenue_won'] == 1000.0

def test_get_sales_kpis_500_error(client):
    """Test GET /api/sales-kpis - failure (503)"""
    with patch('app.get_db', side_effect=Exception("Simulated dashboard crash")):
        response = client.get('/api/sales-kpis')

        assert response.status_code == 503 # <--- THIS IS THE FIX
        assert "Database connection failed" in response.json['error'] # <--- THIS IS THE FIX

# --- Tests for new HTML routes ---

def test_customers_page_route(client):
    """Test that the /customers page loads."""
    response = client.get('/customers')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'

def test_tickets_page_route(client):
    """Test that the /tickets page loads."""
    response = client.get('/tickets')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'

def test_sales_page_route(client):
    """Test that the /sales page loads."""
    response = client.get('/sales')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'
# ... (existing tests)

# --- Tests for Epic 6: Dashboards & KPIs (Kavana) ---

# ... (Existing test_get_sales_kpis_success and test_get_sales_kpis_500_error)

def test_get_customer_kpis_success(client, mocker):
    """
    Test GET /api/customer-kpis - success, checking for total and new customers.
    Corresponds to Epic 6, Story 2: Show customer retention metrics.
    """
    mock_db = mocker.MagicMock()
    
    # Define a time 10 days ago (NEW customer) and 60 days ago (OLD customer)
    from datetime import datetime, timedelta, timezone
    
    # NOTE: Firestore timestamp objects usually don't have an explicit timezone,
    # so we mock them as naive datetime objects for simplicity in this test.
    now = datetime.now()
    ten_days_ago = now - timedelta(days=10)
    sixty_days_ago = now - timedelta(days=60)
    
    # Create fake customer data
    mock_cust1 = mocker.MagicMock(to_dict=lambda: {"name": "Old Customer", "createdAt": sixty_days_ago})
    mock_cust2 = mocker.MagicMock(to_dict=lambda: {"name": "New Customer 1", "createdAt": ten_days_ago})
    mock_cust3 = mocker.MagicMock(to_dict=lambda: {"name": "New Customer 2", "createdAt": ten_days_ago})
    mock_cust4 = mocker.MagicMock(to_dict=lambda: {"name": "Another Old", "createdAt": sixty_days_ago})
    
    mock_customer_data = [mock_cust1, mock_cust2, mock_cust3, mock_cust4]
    
    # Mock the stream() call to return our fake data
    mock_db.collection.return_value.stream.return_value = mock_customer_data
    mocker.patch('app.get_db', return_value=mock_db)
    
    response = client.get('/api/customer-kpis')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Expected calculations:
    # Total Customers: 4
    # New Customers (Last 30 Days): 2 (cust2, cust3)
    
    assert data['total_customers'] == 4
    assert data['new_customers_last_30_days'] == 2

def test_get_customer_kpis_database_failure(client, mocker):
    """Test GET /api/customer-kpis returns 503 on database failure."""
    mocker.patch('app.get_db', side_effect=Exception("DB connection failed for customers"))
    
    response = client.get('/api/customer-kpis')
    
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']
# File: tests/test_sprint2_features.py

# Import necessary modules
from datetime import datetime, timedelta

# Add this test to the end of your file:
def test_get_ticket_metrics_success(client, mocker):
    """Test GET /api/ticket-metrics returns correct average resolution time."""
    mock_db = mocker.MagicMock()

    # Define times for two resolved tickets:
    now = datetime.now()
    
    # Ticket 1: 5.5 hours resolution time (5.5 * 3600 seconds)
    created_at_1 = now - timedelta(hours=5, minutes=30)
    resolved_at_1 = now
    
    # Ticket 2: 10.5 hours resolution time
    created_at_2 = now - timedelta(hours=10, minutes=30)
    resolved_at_2 = now

    mock_ticket_data = [
        # Resolved ticket 1 (5.5 hours)
        mocker.MagicMock(to_dict=lambda: {
            'status': 'Closed', 
            'created_at': created_at_1, 
            'resolved_at': resolved_at_1
        }), 
        # Resolved ticket 2 (10.5 hours)
        mocker.MagicMock(to_dict=lambda: {
            'status': 'Closed', 
            'created_at': created_at_2, 
            'resolved_at': resolved_at_2
        }),
        # Open ticket (should be ignored)
        mocker.MagicMock(to_dict=lambda: {
            'status': 'Open', 
            'created_at': now, 
            'resolved_at': None
        }),
    ]

    mock_db.collection.return_value.stream.return_value = mock_ticket_data
    mocker.patch('app.get_db', return_value=mock_db)

    response = client.get('/api/ticket-metrics')
    
    assert response.status_code == 200
    data = response.get_json()

    # Calculation: (5.5 + 10.5) / 2 = 16 / 2 = 8.0 hours
    assert data['total_resolved'] == 2
    assert data['avg_resolution_hours'] == 8.0 # Rounded to one decimal

def test_get_ticket_metrics_database_failure(client, mocker):
    """Test GET /api/ticket-metrics returns 503 on database failure."""
    mocker.patch('app.get_db', side_effect=Exception("DB connection failed for tickets"))
    
    response = client.get('/api/ticket-metrics')
    
    assert response.status_code == 503
    assert "Database connection failed" in response.get_json()['error']
