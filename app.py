"""Main Flask application for the CRM - Team Kryptonite."""
# pylint: disable=no-member,broad-exception-caught,too-many-return-statements
import logging
import sys
from datetime import datetime, timedelta, timezone
import secrets
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
    """Initialize Firebase only once and return Firestore client safely."""
    try:
        # If already initialized, return client
        if len(firebase_admin._apps) > 0:
            return firestore.client()

        # Initialize Firebase app only once
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return firestore.client()

    except FileNotFoundError:
        logger.error("FATAL ERROR: serviceAccountKey.json not found.")
        raise

    except ValueError as e:
        # If initialization happened from another thread/process, reuse it
        if "already exists" in str(e):
            logger.warning("Firebase already initialized elsewhere. Reusing existing app.")
            return firestore.client()
        raise

    except Exception as e:
        logger.exception("Failed to initialize Firebase")
        raise e



def get_db():
    """Public accessor for the DB client."""
    try:
        return _init_firestore_client()
    except Exception:
        return None

def get_db_or_raise():
    """
    Returns a Firestore client or raises RuntimeError with a consistent message.
    Ensures callers see a "Database connection failed" message rather than raw exceptions.
    """
    try:
        db_conn = get_db()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Database access failure")
        raise RuntimeError("Database connection failed") from exc

    if db_conn is None:
        raise RuntimeError("Database connection failed")
    return db_conn

def generate_referral_code(name=""):
    """Generates a simple, human-readable referral code."""
    prefix = name.upper().replace(" ", "")[:5] or "CRM"
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"{prefix}-{suffix}"

# --- HTML Rendering Routes ---
@app.route('/')
def dashboard():
    """Render the dashboard page."""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Render the login page."""
    return render_template('login.html')

@app.route('/customers')
def customers_page():
    """Render the customers page."""
    return render_template('customers.html')

@app.route('/tickets')
def tickets_page():
    """Render the tickets page."""
    return render_template('tickets.html')

# --- API Routes (Epic 2: Customer CRUD) ---

@app.route('/api/customer', methods=['POST'])
def create_customer():
    """
    Creates a new customer AND their loyalty profile in one atomic batch.
    Integration of Epic 2 (Karthik) and Epic 5 (Kaveri).
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

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

    except Exception:
        logger.exception("Create Customer Failed")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Gets all customers for dropdowns."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503
        customers = []
        docs = db_conn.collection('customers').stream()
        for doc in docs:
            customer = doc.to_dict()
            customer['id'] = doc.id
            customers.append(customer)
        return jsonify(customers), 200
    except Exception:
        logger.exception("Error fetching customers")
        return jsonify({"error": "Internal Server Error"}), 500

# --- Additional Customer CRUD operations ---

@app.route('/api/customer/<string:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    """Gets a single customer's details by their ID."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        customer_ref = db_conn.collection('customers').document(customer_id)
        customer = customer_ref.get()
        if not customer.exists:
            return jsonify({"error": "Customer not found"}), 404
        return jsonify(customer.to_dict() or {}), 200
    except Exception:
        logger.exception("Error getting customer details for %s", customer_id)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/customer/<string:customer_id>', methods=['PUT'])
def update_customer_details(customer_id):
    """Updates a customer's details by their ID."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        data = request.get_json(silent=True) or {}
        updatable_fields = ('name', 'email', 'phone', 'company')
        if not data or not any(field in data for field in updatable_fields):
            return jsonify({"error": "No update data provided"}), 400

        customer_ref = db_conn.collection('customers').document(customer_id)
        if not customer_ref.get().exists:
            return jsonify({"error": "Customer not found"}), 404

        customer_ref.set(data, merge=True)
        return jsonify({"success": True, "id": customer_id}), 200
    except Exception:
        logger.exception("Error updating customer %s", customer_id)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/customer/<string:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Deletes a customer by their ID."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        customer_ref = db_conn.collection('customers').document(customer_id)
        if not customer_ref.get().exists:
            return jsonify({"error": "Customer not found"}), 404

        customer_ref.delete()
        return jsonify({"success": True, "id": customer_id}), 200
    except Exception:
        logger.exception("Error deleting customer %s", customer_id)
        return jsonify({"error": "Internal Server Error"}), 500

# --- API Routes (Epic 3: Leads & Opportunities) ---

@app.route('/api/lead', methods=['POST'])
def capture_lead():
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503
        data = request.get_json(silent=True)

        if not data or not data.get('name') or not data.get('email') or not data.get('source'):
            return jsonify({'success': False, 'error': 'Name, email, and source are required'}), 400

        lead_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'source': data.get('source'),
            'status': 'New',
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        doc_ref = db_conn.collection('leads').document()
        doc_ref.set(lead_data)
        return jsonify({'success': True, 'id': doc_ref.id}), 201
    except Exception:
        logger.exception("Capture Lead Failed")
        return jsonify({'success': False, 'error': 'Internal Server Error'}), 500

@app.route('/api/lead/<string:lead_id>/convert', methods=['POST'])
def convert_lead_to_opportunity(lead_id):
    """Converts an existing lead into a sales opportunity."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        lead_ref = db_conn.collection('leads').document(lead_id)
        lead_doc = lead_ref.get()

        if not lead_doc.exists:
            return jsonify({"error": "Lead not found"}), 404

        lead_data = lead_doc.to_dict() or {}

        lead_ref.update({
            'status': 'Converted',
            'convertedAt': firestore.SERVER_TIMESTAMP
        })

        opportunity_ref = db_conn.collection('opportunities').document()
        opportunity_data = {
            'lead_id': lead_id,
            'name': lead_data.get('name'),
            'email': lead_data.get('email'),
            'source': lead_data.get('source'),
            'stage': 'Qualification',
            'amount': 0.0,
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        opportunity_ref.set(opportunity_data)

        return jsonify({
            "success": True,
            "message": f"Lead {lead_id} converted to Opportunity.",
            "opportunity_id": opportunity_ref.id
        }), 200
    except Exception:
        logger.exception("Error converting lead %s", lead_id)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/lead/<string:lead_id>/assign', methods=['PUT'])
def assign_lead(lead_id):
    """Assigns an existing lead to a specified sales representative."""
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        data = request.get_json(silent=True) or {}
        rep_id = data.get('rep_id')
        rep_name = data.get('rep_name', 'Unspecified')

        if not rep_id:
            return jsonify({"error": "Sales rep ID (rep_id) is required"}), 400

        lead_ref = db_conn.collection('leads').document(lead_id)
        lead_doc = lead_ref.get()
        if not lead_doc.exists:
            return jsonify({"error": "Lead not found"}), 404

        lead_ref.update({
            'assigned_to_id': rep_id,
            'assigned_to_name': rep_name,
            'assignedAt': firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "message": f"Lead {lead_id} assigned to {rep_name} ({rep_id})"
        }), 200
    except Exception:
        logger.exception("Error assigning lead %s", lead_id)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/opportunity/<string:opportunity_id>/status', methods=['PUT'])
def update_opportunity_status(opportunity_id):
    """Updates the stage/status of an existing sales opportunity."""
    allowed_stages = ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost']

    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        data = request.get_json(silent=True) or {}
        new_stage = data.get('stage')

        if not new_stage:
            return jsonify({"error": "Stage is required in the request body"}), 400

        if new_stage not in allowed_stages:
            return jsonify({
                "error": "Invalid stage provided"
            }), 400

        opportunity_ref = db_conn.collection('opportunities').document(opportunity_id)
        opportunity_doc = opportunity_ref.get()

        if not opportunity_doc.exists:
            return jsonify({"error": "Opportunity not found"}), 404

        update_data = {
            'stage': new_stage,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        if new_stage in ['Won', 'Lost']:
            update_data['closedAt'] = firestore.SERVER_TIMESTAMP

        opportunity_ref.update(update_data)

        return jsonify({
            "success": True,
            "message": f"Opportunity {opportunity_id} status updated to {new_stage}"
        }), 200

    except Exception:
        logger.exception("Error updating opportunity %s", opportunity_id)
        return jsonify({"error": "Internal Server Error"}), 500

# --- API Routes (Epic 4: Support Tickets - Kaveri) ---

@app.route('/api/tickets', methods=['GET', 'POST'])
def tickets_endpoint():
    """
    Support ticket endpoints.
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

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

        logger.info("Ticket created: %s", ticket_ref.id)

        return jsonify({
            "success": True,
            "ticket_id": ticket_ref.id,
            "customer_id": ticket_data['customer_id'],
            "sla_deadline": ticket_data['sla_deadline'],
            "status": ticket_data['status'],
            "priority": ticket_data['priority']
        }), 201

    except Exception:
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
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        loyalty_ref = db_conn.collection('loyalty_profiles').document(customer_id)
        profile_doc = loyalty_ref.get()

        if not profile_doc.exists:
            return jsonify({"error": "Loyalty profile not found"}), 404

        return jsonify(profile_doc.to_dict()), 200

    except Exception:
        logger.exception("Error fetching loyalty profile for %s", customer_id)
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
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

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
        logger.exception("Redeem error for %s", customer_id)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/loyalty/<string:customer_id>/use-referral', methods=['POST'])
def use_referral_code(customer_id):
    """
    Applies referral code. The 'customer_id' in URL is the NEW user.
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        data = request.get_json(silent=True)
        code_used = data.get('referral_code') if data else None

        if not code_used:
            return jsonify({"error": "Referral code required"}), 400

        # Find the referrer
        query = (
            db_conn.collection('loyalty_profiles')
            .where('referral_code', '==', code_used)
            .limit(1)
        )
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
            logger.info("Tier Check: %s is now %s", customer_id, result['new_tier'])

        return result
    except Exception:
        logger.exception("Error in add_points_on_purchase")
        return None

@app.route('/api/simulate-purchase', methods=['POST'])
def simulate_purchase():
    """
    Temporary helper endpoint to simulate a purchase and award loyalty points.
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

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


# --- API Routes (Epic 6: Dashboards & KPIs - Kavana) ---

@app.route('/api/sales-kpis', methods=['GET'])
def get_sales_kpis():
    """
    Calculates key sales performance indicators (KPIs) from opportunities.
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        opportunities_ref = db_conn.collection('opportunities')
        all_opportunities = opportunities_ref.stream()

        total_opportunities = 0
        total_won = 0
        total_lost = 0
        total_revenue_won = 0.0

        for doc in all_opportunities:
            opportunity = doc.to_dict()
            total_opportunities += 1
            amount = opportunity.get('amount', 0.0)

            if opportunity.get('stage') == 'Won':
                total_won += 1
                total_revenue_won += amount
            elif opportunity.get('stage') == 'Lost':
                total_lost += 1
        
        open_opportunities = total_opportunities - (total_won + total_lost)

        return jsonify({
            "total_opportunities": total_opportunities,
            "open_opportunities": open_opportunities,
            "won_opportunities": total_won,
            "total_revenue_won": round(total_revenue_won, 2)
        }), 200
        
    except Exception:
        logger.exception("Error calculating sales KPIs")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/customer-kpis', methods=['GET'])
def get_customer_kpis():
    """
    Calculates key customer-related performance indicators (KPIs) like retention metrics.
    Corresponds to Epic 6, Story 2: Show customer retention metrics.
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        customers_ref = db_conn.collection('customers')
        all_customers = customers_ref.stream()

        total_customers = 0
        new_customers_last_30_days = 0
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # NOTE: A more efficient solution for large datasets would be a Firestore query 
        # using a range filter on 'createdAt' for the 30-day calculation, but
        # iterating is acceptable for smaller-to-medium collections.

        for doc in all_customers:
            total_customers += 1
            customer = doc.to_dict()
            
            # Check for new customers in the last 30 days
            created_at = customer.get('createdAt')
            if created_at and isinstance(created_at, datetime):
                # Ensure the datetime object has timezone information for comparison
                created_at_utc = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
                
                if created_at_utc >= thirty_days_ago:
                    new_customers_last_30_days += 1
            # Handle Firestore server timestamp objects, which might be retrieved as
            # firebase_admin.firestore.server_timestamp.ServerTimestamp in some mock/test contexts
            # but usually as datetime in live environments.

        return jsonify({
            "total_customers": total_customers,
            "new_customers_last_30_days": new_customers_last_30_days,
        }), 200
        
    except Exception:
        logger.exception("Error calculating customer KPIs")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/sales')
def sales_page():
    """Render the sales performance dashboard."""
    return render_template('sales.html')
# File: app.py

# ============================
# DYNAMIC TICKET METRICS ROUTE
# ============================

@app.route('/api/ticket-metrics', methods=['GET'])
def get_ticket_metrics():
    """
    Calculates:
    - average resolution time (hours)
    - last 4-week resolution trend for chart
    """
    try:
        try:
            db_conn = get_db_or_raise()
        except RuntimeError as err:
            return jsonify({"error": str(err)}), 503

        tickets_ref = db_conn.collection('tickets')
        all_tickets = tickets_ref.stream()

        total_resolved_count = 0
        total_resolution_seconds = 0

        # For weekly trend
        today = datetime.utcnow()
        weekly_buckets = {
            "Week 1": [],
            "Week 2": [],
            "Week 3": [],
            "Week 4": []
        }

        for doc in all_tickets:
            ticket = doc.to_dict()

            created_at = ticket.get('created_at')
            resolved_at = ticket.get('resolved_at')

            if ticket.get('status') == 'Closed' and created_at and resolved_at:

                # Convert to datetime
                if not isinstance(created_at, datetime):
                    created_at = created_at.astimezone(timezone.utc)
                if not isinstance(resolved_at, datetime):
                    resolved_at = resolved_at.astimezone(timezone.utc)

                resolution_duration = resolved_at - created_at
                hours = resolution_duration.total_seconds() / 3600

                total_resolution_seconds += resolution_duration.total_seconds()
                total_resolved_count += 1

                # Assign to weekly bucket
                for i in range(4):
                    start = today - timedelta(days=(i + 1) * 7)
                    end = today - timedelta(days=i * 7)

                    if start <= resolved_at <= end:
                        weekly_buckets[f"Week {4 - i}"].append(hours)

        # AVG RESOLUTION HOURS
        avg_resolution_hours = (
            round((total_resolution_seconds / total_resolved_count) / 3600, 1)
            if total_resolved_count > 0
            else 0
        )

        # WEEKLY TREND ARRAY
        trend_labels = list(weekly_buckets.keys())
        trend_values = [
            round(sum(bucket) / len(bucket), 2) if len(bucket) > 0 else 0
            for bucket in weekly_buckets.values()
        ]

        return jsonify({
            "total_resolved": total_resolved_count,
            "avg_resolution_hours": avg_resolution_hours,
            "trend_labels": trend_labels,
            "trend_values": trend_values
        }), 200

    except Exception:
        logger.exception("Error calculating ticket resolution metrics")
        return jsonify({"error": "Internal Server Error"}), 500

# File: app.py

# ... (Existing HTML Rendering Routes) ...


@app.route('/report/kpis')
def kpi_report_page():
    """
    Renders a dedicated, print-optimized page for exporting all KPIs as a PDF.
    Fulfills Epic 6, Story 4: Export KPIs as PDF.
    """
    return render_template('kpi_report.html')
# --- END NEW ROUTE ---


if __name__ == "__main__":
    app.run()