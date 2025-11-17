import pytest
import os
from unittest.mock import MagicMock, patch
from app import app, generate_referral_code, get_db

# --- TEST 1: Helper Functions ---
def test_generate_referral_code_logic():
    code = generate_referral_code("Khushi")
    assert "KHUSH" in code
    assert "-" in code
    code_empty = generate_referral_code("")
    assert "CRM-" in code_empty

def test_get_db_helpers(mocker):
    mocker.patch('app._init_firestore_client', return_value="MockDB")
    # Call twice to check caching
    db1 = get_db()
    db2 = get_db()
    assert db1 == "MockDB"

# --- TEST 2: System Monitor ---
def test_monitor_routes(client, mocker):
    # 1. Normal load
    resp = client.get('/monitor')
    assert resp.status_code == 200
    
    # 2. Log file exists
    with patch('os.path.exists', return_value=True):
        # Mock opening the file
        mock_open = mocker.mock_open(read_data="Line 1\nLine 2")
        with patch('builtins.open', mock_open):
            resp = client.get('/api/logs')
            assert resp.status_code == 200
            assert "Line 1" in str(resp.data)

    # 3. Log file missing
    with patch('os.path.exists', return_value=False):
        resp = client.get('/api/logs')
        assert resp.status_code == 200
        assert resp.json['logs'] == []

# --- TEST 3: Middleware Logic (The Safe Way) ---
def test_middleware_logic(client, mocker):
    """
    We temporarily disable Testing Mode to force the 
    Authentication Middleware to actually run and fail.
    """
    # 1. Save the original setting
    original_testing = app.config['TESTING']
    
    try:
        # 2. Turn OFF Test Mode -> This activates the Security Guard
        app.config['TESTING'] = False

        # Scenario A: Access protected page WITHOUT token
        # This triggers the 'except' block in check_auth -> Redirects to login
        response = client.get('/customers')
        assert response.status_code == 302  # Redirect found!
        
        # Scenario B: Simulate a "User" role loading
        # We mock the internals so we don't need a real cookie
        mocker.patch('app.verify_jwt_in_request', return_value=None) # Pass check
        mocker.patch('app.get_jwt', return_value={"role": "TestUser"})
        
        # Hitting login (public page) runs 'load_user_role' but skips 'check_auth'
        client.get('/login')

    finally:
        # 3. IMPORTANT: Restore Test Mode so other tests don't break
        app.config['TESTING'] = original_testing