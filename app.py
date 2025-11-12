"""Main Flask application for the CRM - Team Kryptonite."""
import logging
import sys
from datetime import datetime, timedelta, timezone
import random
import string
from functools import lru_cache
import os

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize Flask App
app = Flask(__name__)

# --- Firebase Initialization (Robust Pattern) ---

@lru_cache(maxsize=1)
def _init_firestore_client():
    """
    Internal function to initialize and cache the client only on success.
    """
    try:
        # Check if app is already initialized to avoid double-init errors
        return firestore.client()
    except ValueError:
        pass # Not initialized yet

    try:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return firestore.client()
    except FileNotFoundError:
        logger.error("FATAL ERROR: serviceAccountKey.json not found.")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise

def get_db():
    """Public accessor for the DB client."""
    try:
        return _init_firestore_client()
    except Exception:
        return None

def generate_referral_code(name=""):
    """Generates a simple, human-readable referral code."""
    prefix = name.upper().replace(" ", "")[:5] or "CRM"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{suffix}"

# --- HTML Rendering Routes ---
@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/customers')
def customers_page():
    return render_template('customers.html')

@app.route('/tickets')
def tickets_page():
    return render_template('tickets.html')

# --- API Routes (Epic 2: Customer CRUD) ---

@app.route('/api/customer', methods=['POST'])
def create_customer():
    """
    Creates a new customer AND their loyalty profile in one atomic batch.
    Integration of Epic 2 (Karthik) and Epic 5 (Kaveri).
    """
    try:
        db_conn = get_db()
        if db_conn is None:
            return jsonify({"error": "Database connection failed"}), 503
        
        data = request.get_json(silent=True)
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({"error": "Name and email are required"}), 400

        # Use a batch to ensure both documents are created, or neither is.
        batch = db_conn.batch()
        
        # 1. Prepare Customer Doc
        customer_ref = db_conn.collection('customers').document()
        customer_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'phone': data.get('phone', ''),
            'company': data.get('company', ''),
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        batch.set(customer_ref, customer_data)

        # 2. Prepare Loyalty Profile (Epic 5)
        referral_code = generate_referral_code(customer_data['name'])
        loyalty_ref = db_conn.collection('loyalty_profiles').document(customer_ref.id)
        loyalty_data = {
            'customer_id': customer_ref.id,
            'points': 0,
            'tier': 'Bronze',
            'referral_code': referral_code,
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        batch.set(loyalty_ref, loyalty_data)
        
        # 3. Commit the batch
        batch.commit()

        # Update customer with loyalty ref (Low risk separate operation)
        customer_ref.update({'loyalty_profile_id': loyalty_ref.id})

        return jsonify({"success": True, "id": customer_ref.id}), 201

    except Exception as e:
        logger.exception("Create Customer Failed")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Gets all customers for dropdowns."""
    try:
        db_conn = get_db()
        if db_conn is None: return jsonify({"error": "Database failed"}), 503
        customers = []
        docs = db_conn.collection('customers').stream()
        for doc in docs:
            customer = doc.to_dict()
            customer['id'] = doc.id
            customers.append(customer)
        return jsonify(customers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API Routes (Epic 3: Leads & Opportunities) ---

@app.route('/api/lead', methods=['POST'])
def capture_lead():
    try:
        db_conn = get_db()
        if not db_conn: return jsonify({"error": "Database failed"}), 503
        data = request.get_json(silent=True)
        
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'error': 'Name and email required'}), 400

        lead_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'source': data.get('source', 'Web'),
            'status': 'New',
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        doc_ref = db_conn.collection('leads').document()
        doc_ref.set(lead_data)
        return jsonify({'success': True, 'id': doc_ref.id}), 201
    except Exception as e:
        logger.exception("Capture Lead Failed")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- API Routes (Epic 4: Support Tickets - Kaveri) ---

@app.route('/api/tickets', methods=['GET', 'POST'])
def tickets_endpoint():
    """
    Support ticket endpoints.
    """
    try:
        db_conn = get_db()
        if db_conn is None:
            return jsonify({"error": "Database unavailable"}), 503

        if request.method == 'GET':
            tickets = []
            ticket_query = (
                db_conn.collection('tickets')
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(20)
            )
            for doc in ticket_query.stream():
                ticket = doc.to_dict()
                ticket['id'] = doc.id
                tickets.append(ticket)
            return jsonify(tickets), 200

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        if 'customer_id' not in data or 'issue' not in data:
            return jsonify({"error": "Missing required fields: customer_id, issue"}), 400

        now_utc = datetime.now(timezone.utc)
        ticket_data = {
            "customer_id": data['customer_id'],
            "issue": data['issue'],
            "status": "Open",
            "priority": data.get("priority", "Medium"),
            "created_at": firestore.SERVER_TIMESTAMP,
            "sla_deadline": (now_utc + timedelta(hours=24)).isoformat()
        }

        ticket_ref = db_conn.collection('tickets').document()
        ticket_ref.set(ticket_data)

        logger.info(f"Ticket created: {ticket_ref.id}")

        return jsonify({
            "success": True,
            "ticket_id": ticket_ref.id,
            "sla_deadline": ticket_data['sla_deadline']
        }), 201

    except Exception as e:
        logger.exception("Error creating support ticket")
        return jsonify({"error": "Internal Server Error"}), 500


# --- API Routes (Epic 5: Loyalty Program - Kaveri) ---

TIER_LEVELS = {
    "Bronze": 0,
    "Silver": 500,
    "Gold": 2000
}

@app.route('/api/loyalty/<string:customer_id>', methods=['GET'])
def get_loyalty_profile(customer_id):
    try:
        db_conn = get_db()
        if not db_conn: return jsonify({"error": "Database unavailable"}), 503

        loyalty_ref = db_conn.collection('loyalty_profiles').document(customer_id)
        profile_doc = loyalty_ref.get()

        if not profile_doc.exists:
            return jsonify({"error": "Loyalty profile not found"}), 404

        return jsonify(profile_doc.to_dict()), 200

    except Exception:
        logger.exception(f"Error fetching loyalty profile for {customer_id}")
        return jsonify({"error": "Internal Server Error"}), 500

# --- TRANSACTIONAL HELPERS (For Epic 5 Safety) ---

@firestore.transactional
def redeem_transaction(transaction, ref, points_to_redeem):
    snapshot = ref.get(transaction=transaction)
    if not snapshot.exists:
        raise ValueError("Profile not found")
    
    current_points = snapshot.get('points')
    if current_points < points_to_redeem:
        raise ValueError("Insufficient points")
    
    new_balance = current_points - points_to_redeem
    transaction.update(ref, {'points': new_balance})
    return new_balance

@firestore.transactional
def add_points_transaction(transaction, ref, points_earned):
    snapshot = ref.get(transaction=transaction)
    if not snapshot.exists:
        return None
    
    data = snapshot.to_dict()
    current_points = data.get('points', 0)
    new_total = current_points + points_earned
    
    updates = {'points': new_total}
    
    # Calculate Tier
    new_tier = data.get('tier', 'Bronze')
    if new_total >= TIER_LEVELS["Gold"]:
        new_tier = "Gold"
    elif new_total >= TIER_LEVELS["Silver"]:
        new_tier = "Silver"
        
    if new_tier != data.get('tier', 'Bronze'):
        updates['tier'] = new_tier
        
    transaction.update(ref, updates)
    return {"new_points": new_total, "new_tier": new_tier}

# --- LOYALTY ACTIONS ---

@app.route('/api/loyalty/<string:customer_id>/redeem', methods=['POST'])
def redeem_points(customer_id):
    """
    Redeems points using a Transaction to prevent race conditions.
    """
    try:
        db_conn = get_db()
        if not db_conn: return jsonify({"error": "Database unavailable"}), 503

        data = request.get_json(silent=True)
        if not data or 'points_to_redeem' not in data:
            return jsonify({"error": "points_to_redeem required"}), 400

        points = data['points_to_redeem']
        if not isinstance(points, int) or points <= 0:
            return jsonify({"error": "Points must be a positive integer"}), 400

        loyalty_ref = db_conn.collection('loyalty_profiles').document(customer_id)
        
        try:
            transaction = db_conn.transaction()
            new_balance = redeem_transaction(transaction, loyalty_ref, points)
            return jsonify({
                "success": True,
                "message": "Redemption successful",
                "new_points_balance": new_balance
            }), 200
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
            
    except Exception:
        logger.exception(f"Redeem error for {customer_id}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/loyalty/<string:customer_id>/use-referral', methods=['POST'])
def use_referral_code(customer_id):
    """
    Applies referral code. The 'customer_id' in URL is the NEW user.
    """
    try:
        db_conn = get_db()
        if not db_conn: return jsonify({"error": "Database unavailable"}), 503

        data = request.get_json(silent=True)
        code_used = data.get('referral_code') if data else None
        
        if not code_used:
            return jsonify({"error": "Referral code required"}), 400

        # Find the referrer
        query = db_conn.collection('loyalty_profiles').where('referral_code', '==', code_used).limit(1)
        referrers = list(query.stream())

        if not referrers:
            return jsonify({"error": "Invalid referral code"}), 404

        referrer_doc = referrers[0]
        referrer_id = referrer_doc.id

        if referrer_id == customer_id:
            return jsonify({"error": "Cannot refer yourself"}), 400

        # Atomic increment for referrer (No need for full transaction if just incrementing)
        referrer_ref = db_conn.collection('loyalty_profiles').document(referrer_id)
        referrer_ref.update({
            'points': firestore.Increment(100)
        })

        return jsonify({
            "success": True,
            "message": f"Referral applied. 100 points sent to {referrer_id}."
        }), 200

    except Exception:
        logger.exception("Referral error")
        return jsonify({"error": "Internal Server Error"}), 500

def add_points_on_purchase(db_conn, customer_id, purchase_amount):
    """
    Service function called by Payment hooks.
    Uses transaction for atomicity.
    """
    try:
        loyalty_ref = db_conn.collection('loyalty_profiles').document(customer_id)
        transaction = db_conn.transaction()
        result = add_points_transaction(transaction, loyalty_ref, int(purchase_amount))
        
        if result and result['new_tier'] != 'Bronze':
             logger.info(f"Tier Check: {customer_id} is now {result['new_tier']}")
             
        return result
    except Exception as e:
        logger.error(f"Error in add_points_on_purchase: {e}")
        return None

@app.route('/api/simulate-purchase', methods=['POST'])
def simulate_purchase():
    """
    Temporary helper endpoint to simulate a purchase and award loyalty points.
    """
    try:
        db_conn = get_db()
        if not db_conn:
            return jsonify({"error": "Database unavailable"}), 503

        data = request.get_json(silent=True) or {}
        customer_id = data.get('customer_id')
        amount = data.get('amount')

        if not customer_id:
            return jsonify({"error": "customer_id is required"}), 400
        if amount is None:
            return jsonify({"error": "amount is required"}), 400

        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            return jsonify({"error": "amount must be a number"}), 400

        if amount_value <= 0:
            return jsonify({"error": "amount must be greater than zero"}), 400

        # Convert to integer points (1 point per currency unit for now)
        points_to_add = int(amount_value)
        if points_to_add <= 0:
            points_to_add = 1

        result = add_points_on_purchase(db_conn, customer_id, points_to_add)

        if result is None:
            return jsonify({"error": "Loyalty profile not found"}), 404

        response_payload = {
            "success": True,
            "customer_id": customer_id,
            "points_added": points_to_add,
            "new_points_balance": result.get('new_points'),
            "new_tier": result.get('new_tier')
        }
        return jsonify(response_payload), 200
    except Exception:
        logger.exception("Error simulating purchase")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    # Allow overriding the port via environment variable, default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
