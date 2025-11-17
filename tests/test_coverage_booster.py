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
    db1 = get_db()
    db2 = get_db()
    assert db1 == "MockDB"

# --- TEST 2: System Monitor ---
def test_monitor_routes(client, mocker):
    resp = client.get('/monitor')
    assert resp.status_code == 200
    
    with patch('os.path.exists', return_value=True):
        mock_open = mocker.mock_open(read_data="Log Entry 1")
        with patch('builtins.open', mock_open):
            resp = client.get('/api/logs')
            assert resp.status_code == 200

    with patch('os.path.exists', return_value=False):
        resp = client.get('/api/logs')
        assert resp.status_code == 200

# --- TEST 3: Middleware (The Safer Way) ---
def test_middleware_natural_trigger(client, mocker):
    """
    Instead of mocking internals, we disable testing mode 
    and hit a real URL to force middleware to run.
    """
    # 1. Define a temporary route to hit
    @app.route('/coverage_test_route')
    def coverage_test():
        return "OK"

    # 2. Temporarily turn off TESTING so middleware actually runs
    # (We use a try/finally block to ensure we reset it)
    original_testing = app.config['TESTING']
    app.config['TESTING'] = False

    try:
        # Mock the JWT verifier to fail (Triggering the 'except' block in middleware)
        mocker.patch('app.verify_jwt_in_request', side_effect=Exception("Force Fail"))
        
        # This request will trigger 'check_auth', fail verification, and redirect
        client.get('/coverage_test_route')

        # Now Mock get_jwt to return data (Triggering 'load_user_role' logic)
        mocker.patch('app.verify_jwt_in_request', return_value=None) # Success now
        mocker.patch('app.get_jwt', return_value={"role": "User"})
        
        client.get('/coverage_test_route')

    finally:
        # ALWAYS restore testing mode so other tests don't break
        app.config['TESTING'] = original_testing