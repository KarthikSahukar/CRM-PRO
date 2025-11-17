import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    """
    Global Test Fixture.
    Mocks the Authentication system so tests don't need valid cookies.
    """
    app.config['TESTING'] = True
    
    # 1. Mock 'verify_jwt_in_request' so the middleware doesn't block us
    # 2. Mock 'get_jwt' so the RBAC middleware sees us as an "Admin"
    with patch('flask_jwt_extended.view_decorators.verify_jwt_in_request'), \
         patch('flask_jwt_extended.utils.get_jwt', return_value={"role": "Admin"}), \
         patch('app.verify_jwt_in_request'): # Patch it in app.py namespace too just in case
        
        with app.test_client() as client:
            yield client