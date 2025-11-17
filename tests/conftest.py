import pytest
from app import app
from flask_jwt_extended import create_access_token 

@pytest.fixture
def client():
    """
    Global Test Fixture.
    This automatically logs in the test robot as an Admin for ALL test files.
    """
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret-key' 
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False 
    
    with app.test_client() as client:
        with app.app_context():
            # Create the Admin Token
            access_token = create_access_token(
                identity="admin@crm.com", 
                additional_claims={"role": "Admin"}
            )
        
        # Attach the token to the cookie so the robot can pass the security guard
        client.set_cookie('localhost', 'access_token_cookie', access_token)
        
        yield client