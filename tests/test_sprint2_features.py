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