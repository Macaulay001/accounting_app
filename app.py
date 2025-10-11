"""
Ponmo Business Manager - Refactored Main Application
Following standard accounting practices and clean architecture
"""

from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from datetime import datetime, timedelta
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import wraps
from dotenv import load_dotenv

# Import our new modular structure
from src.services.accounting_service import AccountingService
from src.models.customer import Customer
from src.models.vendor import Vendor
from src.models.product import Product
from src.models.journal_entry import JournalEntry
from src.models.inventory_batch import InventoryBatch
from src.models.vendor_payment import VendorPayment
from src.models.customer_deposit import CustomerDeposit

load_dotenv()

app = Flask(__name__)

# Set secret key for session management
app.secret_key = os.getenv('SECRET_KEY', 'ponmo-accounting-app-secret-key-2025')

# ----------------------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------------------

@app.route('/healthz')
def health_check():
    """Health check endpoint for Docker and Kubernetes"""
    return "OK", 200

# ----------------------------------------------------------------------
# Custom Filters
# ----------------------------------------------------------------------

@app.template_filter('currency')
def currency_filter(value):
    """Format number as currency with commas and ₦ symbol"""
    try:
        if value is None:
            return "₦0.00"
        num = float(value)
        return f"₦{num:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"

@app.template_filter('number')
def number_filter(value):
    """Format number with commas"""
    try:
        if value is None:
            return "0"
        num = float(value)
        return f"{num:,.0f}"
    except (ValueError, TypeError):
        return "0"

@app.template_filter('decimal')
def decimal_filter(value, decimals=2):
    """Format number with commas and specified decimal places"""
    try:
        if value is None:
            return "0.00"
        num = float(value)
        return f"{num:,.{decimals}f}"
    except (ValueError, TypeError):
        return "0.00"

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Firebase Admin SDK and Firestore client
import json

# Get Firebase credentials from environment variable
firebase_auth_json = os.getenv('FIREBASE_AUTH_JSON')
if firebase_auth_json:
    # Parse JSON string from environment variable
    firebase_creds = json.loads(firebase_auth_json)
    cred = credentials.Certificate(firebase_creds)
else:
    # Fallback to file (for local development)
    cred = credentials.Certificate("firebase-auth.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# ----------------------------------------------------------------------
# Authentication Decorator
# ----------------------------------------------------------------------
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def get_accounting_service():
    """Get accounting service instance for current user"""
    user_id = session["user"]["uid"]
    return AccountingService(db, user_id)

def get_models():
    """Get model instances for current user"""
    user_id = session["user"]["uid"]
    return {
        'customer': Customer(db, user_id),
        'vendor': Vendor(db, user_id),
        'product': Product(db, user_id),
        'journal_entry': JournalEntry(db, user_id),
        'inventory_batch': InventoryBatch(db, user_id),
        'vendor_payment': VendorPayment(db, user_id),
        'customer_deposit': CustomerDeposit(db, user_id)
    }

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            # Authenticate user with Firebase
            user_record = auth.get_user_by_email(email)
            user_id = user_record.uid

            # Fetch user details from Firestore
            user_doc = db.collection("users").document(user_id).get()

            if not user_doc.exists:
                flash("Account not found. Please sign up.", "danger")
                return redirect(url_for("signup"))

            user_data = user_doc.to_dict()

            # Ensure business details are set
            if not user_data.get("business_name") or not user_data.get("phone_number"):
                session["pending_user"] = {"uid": user_id, "email": email}
                return redirect(url_for("setup_business"))

            # Store user in session
            session["user"] = {
                "uid": user_id,
                "email": email,
                "business_name": user_data["business_name"],
                "phone_number": user_data["phone_number"],
            }

            return redirect(url_for('dashboard'))

        except Exception as e:
            flash("Invalid login credentials. Please try again.", "danger")
            return redirect(url_for("login"))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    try:
        email = request.form.get("email")
        password = request.form.get("password")
        business_name = request.form.get("business_name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()

        if not email or not password or not business_name or not phone_number:
            flash("All fields are required.", "danger")
            return redirect(url_for("signup"))

        # Create user in Firebase Authentication
        user_record = auth.create_user(email=email, password=password)
        user_id = user_record.uid

        # Save user details in Firestore
        db.collection("users").document(user_id).set({
            "email": email,
            "business_name": business_name,
            "phone_number": phone_number,
            "created_at": datetime.utcnow()
        })

        # Initialize accounting structure for new user
        accounting_ref = db.collection(f"user_data_{user_id}").document("accounting")
        accounting_ref.set({
            "initialized_at": datetime.utcnow(),
            "chart_of_accounts_version": "1.0"
        })

        # Store user in session
        session["user"] = {
            "uid": user_id,
            "email": email,
            "business_name": business_name,
            "phone_number": phone_number
        }

        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard"))

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("signup"))

@app.route('/dashboard')
@auth_required
def dashboard():
    """Dashboard with accounting overview"""
    accounting_service = get_accounting_service()
    models = get_models()
    
    # Get inventory batch data first
    inventory_batches = models['inventory_batch'].get_all()
    
    # Calculate financial metrics from journal entries and inventory data
    cash_balance = accounting_service.get_account_balance("1000") + accounting_service.get_account_balance("1100")
    receivables = accounting_service.get_account_balance("1200")
    
    # Calculate total revenue from sales journal entries
    total_revenue = accounting_service.get_account_balance("4000")  # Revenue account
    
    # Calculate outstanding payables (what we owe vendors)
    accounts_payable = accounting_service.get_account_balance("2000")
    
    # Calculate actual outstanding payables by comparing total purchases vs payments
    total_purchases = sum(batch.get('purchase_cost', 0) for batch in inventory_batches)
    
    # Calculate total payments across all vendors
    all_payments = models['vendor_payment'].get_all()
    total_payments = sum(payment.get('payment_amount', 0) for payment in all_payments)
    
    outstanding_payables = max(0, total_purchases - total_payments)
    
    # Calculate inventory value (current remaining inventory at cost)
    total_inventory_value = 0
    for batch in inventory_batches:
        remaining_pieces = batch.get('current_pieces', 0)
        total_pieces = batch.get('total_pieces', 1)
        cost_per_piece = batch.get('purchase_cost', 0) / total_pieces if total_pieces > 0 else 0
        total_inventory_value += remaining_pieces * cost_per_piece
    
    # Get recent transactions from journal entries (created by inventory batches and sales)
    all_entries = models['journal_entry'].get_all(order_by='created_at')
    
    # Convert journal entries to display format
    formatted_entries = []
    for entry in all_entries:
        description = entry.get('description', '')
        total_debits = sum(line.get('debit', 0) for line in entry.get('entries', []))
        total_credits = sum(line.get('credit', 0) for line in entry.get('entries', []))
        
        # Determine transaction type and amount
        if 'Sale to customer' in description:
            transaction_type = 'sale'
            amount = total_credits
        elif 'Purchase of raw materials' in description and 'Batch' in description:
            transaction_type = 'purchase'
            amount = total_debits
        else:
            transaction_type = 'other'
            amount = max(total_debits, total_credits)
        
        formatted_entries.append({
            'id': entry['id'],
            'date': entry.get('date', entry.get('created_at')),
            'created_at': entry.get('created_at', datetime.min),
            'type': transaction_type,
            'description': description,
            'amount': amount,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'status': 'posted',
            'reference': entry.get('reference', '')
        })
    
    # Sort by created_at (most recent first) for accurate chronological order
    formatted_entries.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    recent_entries = formatted_entries[:10]
    
    return render_template("dashboard_accounting.html", 
                         user=session["user"],
                         cash_balance=cash_balance,
                         receivables=receivables,
                         total_revenue=total_revenue,
                         payables=outstanding_payables,
                         inventory_value=total_inventory_value,
                         recent_entries=recent_entries,
                         current_date=datetime.now())

@app.route('/sales', methods=['GET', 'POST'])
@auth_required
def sales_route():
    """Record sales with proper double-entry bookkeeping"""
    models = get_models()
    accounting_service = get_accounting_service()
    
    if request.method == 'POST':
        try:
            # Get form data
            date_str = request.form.get('date')
            customer_id = request.form.get('customer')
            batch_id = request.form.get('batch_id')
            ile_number = int(request.form.get('ile_number', 1))
            sales_amount = float(request.form.get('total_amount', 0))
            cost_of_goods = float(request.form.get('cost_of_goods', 0))
            invoice_number = request.form.get('invoice_number', f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            payment_received = float(request.form.get('amount_paid', 0))
            payment_method = request.form.get('payment_method', 'cash')
            
            # Validate date
            sale_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Calculate total pieces sold from quantities
            total_pieces_sold = 0
            for i, product in enumerate(request.form.getlist('product[]')):
                quantity_wholesale = float(request.form.getlist('quantity_wholesale[]')[i] or 0)
                quantity_retail = float(request.form.getlist('quantity_retail[]')[i] or 0)
                total_pieces_sold += quantity_wholesale + quantity_retail
            
            # Update inventory batch to track sales
            if batch_id and ile_number and total_pieces_sold > 0:
                success = models['inventory_batch'].record_sale(
                    batch_id=batch_id,
                    ile_number=ile_number,
                    pieces_sold=total_pieces_sold,
                    sales_date=sale_date
                )
                
                if not success:
                    flash("Failed to update inventory batch.", "danger")
                    return redirect(url_for('sales_route'))
            
            # Record the sale using accounting service (without COGS for now)
            journal_entry_id = accounting_service.record_sale(
                customer_id=customer_id,
                date=sale_date,
                sales_amount=sales_amount,
                cost_of_goods_sold=0,  # No COGS calculation for now
                invoice_number=invoice_number,
                payment_received=payment_received
            )
            
            # Auto-apply available deposit against remaining due (server-side authority)
            try:
                _dep_info = models['customer_deposit'].get_customer_balance(customer_id)
                if isinstance(_dep_info, dict):
                    deposit_balance = float(_dep_info.get('current_balance', 0) or 0)
                else:
                    deposit_balance = float(_dep_info or 0)
            except Exception:
                deposit_balance = 0.0
            amount_due_after_cash = max(0.0, float(sales_amount) - float(payment_received))
            auto_deposit_applied = max(0.0, min(float(deposit_balance), float(amount_due_after_cash)))
            if auto_deposit_applied > 0 and customer_id:
                try:
                    accounting_service.record_customer_deposit_usage(
                        customer_id=customer_id,
                        amount=auto_deposit_applied,
                        date=sale_date,
                        reference=f"INV-{invoice_number}"
                    )
                    # Track usage in deposits model for reporting
                    models['customer_deposit'].record_deposit_usage(
                        customer_id=customer_id,
                        amount=auto_deposit_applied,
                        date=sale_date,
                        reference=f"INV-{invoice_number}",
                        notes="Applied to sale"
                    )
                except Exception as e:
                    print(f"Warning: failed to record deposit usage: {e}")
            
            flash(f"Sale recorded successfully. Journal Entry: {journal_entry_id}", "success")
            return redirect(url_for('sales_route'))
            
        except Exception as e:
            flash(f"Error processing sale: {str(e)}", "danger")
    
    # Get data for form
    customers = models['customer'].get_all()
    products = models['product'].get_active_products()
    batches = models['inventory_batch'].get_all()
    
    return render_template('sales_accounting.html', 
                         customers=customers, 
                         products=products,
                         batches=batches,
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/api/batch/<batch_id>/ile-groups')
@auth_required
def get_batch_ile_groups(batch_id):
    """Get ile groups for a specific batch"""
    models = get_models()
    
    try:
        batch = models['inventory_batch'].get_by_id(batch_id)
        if not batch:
            return jsonify({'success': False, 'error': 'Batch not found'})
        
        ile_groups = batch.get('ile_groups', [])
        
        # Format ile groups for the dropdown
        formatted_ile_groups = []
        for ile_group in ile_groups:
            formatted_ile_groups.append({
                'ile_number': ile_group.get('ile_number'),
                'remaining_pieces': ile_group.get('remaining_pieces', 0),
                'status': ile_group.get('status', 'raw_material')
            })
        
        return jsonify({
            'success': True,
            'ile_groups': formatted_ile_groups
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/customer/<customer_id>/balances')
@auth_required
def get_customer_balances(customer_id):
    """Return customer's deposit balance and AR balance"""
    models = get_models()
    try:
        # print(f"[DEBUG] get_customer_balances called for customer_id={customer_id}")
        # Deposit balance from CustomerDeposit model
        deposit_info = models['customer_deposit'].get_customer_balance(customer_id)
        if isinstance(deposit_info, dict):
            deposit_balance = float(deposit_info.get('current_balance', 0) or 0)
        else:
            deposit_balance = float(deposit_info or 0)
        # print(f"[DEBUG] Deposit balance fetched: raw={deposit_info} parsed={deposit_balance}")
        
        # Compute per-customer Accounts Receivable by parsing journal entries
        all_entries = models['journal_entry'].get_all()
        # print(f"[DEBUG] Total journal entries fetched: {len(all_entries) if all_entries else 0}")
        ar_debits = 0.0
        ar_credits = 0.0
        needle = f"customer {customer_id}".lower()
        matched = 0
        for je in all_entries:
            description = (je.get('description') or '').lower()
            if needle in description:
                matched += 1
                for line in je.get('entries', []):
                    if line.get('account_code') == '1200':
                        ar_debits += float(line.get('debit', 0) or 0)
                        ar_credits += float(line.get('credit', 0) or 0)
        # print(f"[DEBUG] Matched entries for customer: {matched}")
        # print(f"[DEBUG] AR debits sum: {ar_debits}, AR credits sum: {ar_credits}")
        ar_balance = max(0.0, ar_debits - ar_credits)
        print(f"[DEBUG] Computed AR balance: {ar_balance}")
        
        customer_balance = deposit_balance - ar_balance
        print(f"[DEBUG] Computed customer balance (deposit - AR): {customer_balance}")
        
        return jsonify({
            'success': True,
            'deposit_balance': deposit_balance,
            'accounts_receivable': ar_balance,
            'customer_balance': customer_balance
        })
    except Exception as e:
        print(f"[DEBUG] Error in get_customer_balances: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/production', methods=['GET', 'POST'])
@auth_required
def production_route():
    """Record production process with inventory tracking"""
    models = get_models()
    accounting_service = get_accounting_service()
    
    if request.method == 'POST':
        try:
            # Get form data
            production_date_str = request.form.get('production_date')
            batch_id = request.form.get('batch_id')
            ile_number = int(request.form.get('ile_number', 1))
            pieces_processed = int(request.form.get('pieces_processed', 0))
            processing_cost = float(request.form.get('processing_cost', 0))
            reference = request.form.get('reference', f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            
            # Validate date
            if not production_date_str:
                flash("Production date is required.", "danger")
                return redirect(url_for('production_route'))
            
            production_date = datetime.strptime(production_date_str, '%Y-%m-%d')
            
            # Validate pieces processed
            if pieces_processed <= 0:
                flash("Pieces processed must be greater than 0.", "danger")
                return redirect(url_for('production_route'))
            
            # Get batch information
            batch = models['inventory_batch'].get_by_id(batch_id)
            if not batch:
                flash("Inventory batch not found.", "danger")
                return redirect(url_for('production_route'))
            
            # Check if ile group exists and has enough pieces
            ile_group = None
            for ig in batch.get('ile_groups', []):
                if ig['ile_number'] == ile_number:
                    ile_group = ig
                    break
            
            if not ile_group:
                flash(f"Ile group {ile_number} not found in batch.", "danger")
                return redirect(url_for('production_route'))
            
            if ile_group['remaining_pieces'] < pieces_processed:
                flash(f"Not enough pieces in Ile group {ile_number}. Available: {ile_group['remaining_pieces']}", "danger")
                return redirect(url_for('production_route'))
            
            # Update inventory batch - record production
            success = models['inventory_batch'].record_production(
                batch_id=batch_id,
                ile_number=ile_number,
                pieces_processed=pieces_processed,
                production_date=production_date,
                processing_cost=processing_cost
            )
            
            if not success:
                flash("Failed to update inventory batch.", "danger")
                return redirect(url_for('production_route'))
            
            # Calculate raw materials cost (proportional to pieces processed)
            total_pieces = batch.get('total_pieces', 1)
            total_cost = batch.get('purchase_cost', 0)
            raw_materials_cost = (pieces_processed / total_pieces) * total_cost
            
            # Record the production using accounting service
            # Include processing cost in the finished goods value
            total_finished_goods_value = raw_materials_cost + processing_cost
            journal_entry_id = accounting_service.record_production(
                date=production_date,
                raw_materials_used=raw_materials_cost,
                processing_cost=processing_cost,  # Include actual processing cost
                finished_goods_value=total_finished_goods_value,  # Total cost including processing
                reference=reference
            )
            
            flash(f"Production recorded successfully! Processed {pieces_processed} pieces from Ile {ile_number}. Journal Entry: {journal_entry_id}", "success")
            return redirect(url_for('production_route'))
            
        except Exception as e:
            flash(f"Error processing production: {str(e)}", "danger")
    
    # Get data for form
    batches = models['inventory_batch'].get_all()
    
    # Get recent production records from inventory batches
    production_records = []
    for batch in batches:
        for ile_group in batch.get('ile_groups', []):
            for production_record in ile_group.get('production_records', []):
                production_records.append({
                    'batch_id': batch['id'],
                    'vendor_name': batch['vendor_name'],
                    'ile_number': ile_group['ile_number'],
                    'production_date': production_record.get('production_date'),
                    'pieces_processed': production_record.get('pieces_processed', 0),
                    'processing_cost': production_record.get('processing_cost', 0),
                    'recorded_at': production_record.get('recorded_at')
                })
    
    # Sort by recorded_at date (most recent first) and take last 10
    production_records.sort(key=lambda x: x.get('recorded_at', datetime.min), reverse=True)
    production_records = production_records[:10]
    
    return render_template('production.html', 
                         batches=batches,
                         production_records=production_records,
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/delete-production-record/<batch_id>/<int:ile_number>', methods=['POST'])
@auth_required
def delete_production_record(batch_id, ile_number):
    """Delete a production record from an inventory batch"""
    models = get_models()
    
    try:
        # Get the batch
        batch = models['inventory_batch'].get_by_id(batch_id)
        if not batch:
            flash("Inventory batch not found.", "danger")
            return redirect(url_for('production_route'))
        
        # Find the ile group
        ile_group_found = False
        for i, ile_group in enumerate(batch.get('ile_groups', [])):
            if ile_group['ile_number'] == ile_number:
                ile_group_found = True
                # Remove the last production record from this ile group
                if ile_group.get('production_records'):
                    # Get the last production record
                    last_record = ile_group['production_records'][-1]
                    pieces_processed = last_record.get('pieces_processed', 0)
                    
                    # Remove the last production record
                    ile_group['production_records'].pop()
                    
                    # Restore the pieces to remaining_pieces
                    ile_group['remaining_pieces'] += pieces_processed
                    
                    # Update the batch
                    batch['ile_groups'][i] = ile_group
                    batch['current_pieces'] = sum(ig['remaining_pieces'] for ig in batch['ile_groups'])
                    batch['updated_at'] = datetime.now()
                    
                    # Update the batch in the database
                    success = models['inventory_batch'].update(batch_id, batch)
                    
                    if success:
                        flash(f"Production record deleted successfully. {pieces_processed} pieces restored to Ile {ile_number}.", "success")
                    else:
                        flash("Failed to delete production record.", "danger")
                else:
                    flash("No production records found for this ile group.", "warning")
                break
        
        if not ile_group_found:
            flash(f"Ile group {ile_number} not found in batch.", "danger")
            
    except Exception as e:
        flash(f"Error deleting production record: {str(e)}", "danger")
    
    return redirect(url_for('production_route'))

@app.route('/customer-deposits', methods=['GET', 'POST'])
@auth_required
def customer_deposits_route():
    """Handle customer deposits and advance payments"""
    models = get_models()
    accounting_service = get_accounting_service()
    
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            amount = float(request.form.get('amount', 0))
            deposit_date_str = request.form.get('deposit_date')
            payment_method = request.form.get('payment_method', 'cash')
            reference = request.form.get('reference', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not customer_id or not amount or not deposit_date_str:
                flash('Customer, amount, and date are required', 'error')
                return redirect(url_for('customer_deposits_route'))
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'error')
                return redirect(url_for('customer_deposits_route'))
            
            # Parse date
            try:
                deposit_date = datetime.strptime(deposit_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format', 'error')
                return redirect(url_for('customer_deposits_route'))
            
            # Create deposit record
            deposit_id = models['customer_deposit'].create_deposit(
                customer_id=customer_id,
                amount=amount,
                deposit_date=deposit_date,
                payment_method=payment_method,
                reference=reference,
                notes=notes
            )
            
            # Record accounting entry
            journal_entry_id = accounting_service.record_customer_deposit(
                customer_id=customer_id,
                amount=amount,
                date=deposit_date,
                payment_method=payment_method,
                reference=reference
            )
            
            flash(f'Customer deposit of {amount:,.2f} recorded successfully', 'success')
            return redirect(url_for('customer_deposits_route'))
            
        except Exception as e:
            print(f"Error processing customer deposit: {e}")
            flash(f'Error processing deposit: {str(e)}', 'error')
            return redirect(url_for('customer_deposits_route'))
    
    # GET request - show form and recent deposits
    try:
        # Get all customers
        customers = models['customer'].get_all()
        
        # Get customer balances
        customer_balances = models['customer_deposit'].get_all_customer_balances()
        
        # Get recent deposits (last 20)
        recent_deposits = []
        all_deposits = models['customer_deposit'].get_all()
        if all_deposits:
            # Sort by created_at (most recent first)
            all_deposits.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            recent_deposits = all_deposits[:20]
        
        return render_template('customer_deposits.html',
                             customers=customers,
                             customer_balances=customer_balances,
                             recent_deposits=recent_deposits,
                             user=session["user"],
                             current_date=datetime.now())
        
    except Exception as e:
        print(f"Error loading customer deposits: {e}")
        flash(f'Error loading customer deposits: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/use-customer-deposit', methods=['POST'])
@auth_required
def use_customer_deposit_route():
    """Use customer deposit for a sale transaction"""
    models = get_models()
    accounting_service = get_accounting_service()
    
    try:
        # Get form data
        customer_id = request.form.get('customer_id')
        sale_amount = float(request.form.get('sale_amount', 0))
        invoice_number = request.form.get('invoice_number', '').strip()
        sale_date_str = request.form.get('sale_date')
        
        # Validate required fields
        if not customer_id or not sale_amount or not sale_date_str:
            flash('Customer, sale amount, and date are required', 'error')
            return redirect(url_for('customer_deposits_route'))
        
        if sale_amount <= 0:
            flash('Sale amount must be greater than zero', 'error')
            return redirect(url_for('customer_deposits_route'))
        
        # Parse date
        try:
            sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('customer_deposits_route'))
        
        # Check customer deposit balance
        customer_balance = models['customer_deposit'].get_customer_balance(customer_id)
        if customer_balance['current_balance'] < sale_amount:
            flash(f"Insufficient customer deposit balance. Available: {customer_balance['current_balance']:,.2f}, Required: {sale_amount:,.2f}", "error")
            return redirect(url_for('customer_deposits_route'))
        
        # Generate invoice number if not provided
        if not invoice_number:
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Record the sale with full payment from deposit
        journal_entry_id = accounting_service.record_sale(
            customer_id=customer_id,
            date=sale_date,
            sales_amount=sale_amount,
            cost_of_goods_sold=0,  # No COGS calculation for now
            invoice_number=invoice_number,
            payment_received=sale_amount  # Full payment from deposit
        )
        
        # Record the deposit usage (debit customer deposits, credit cash)
        deposit_usage_id = accounting_service.record_customer_deposit_usage(
            customer_id=customer_id,
            amount=sale_amount,
            date=sale_date,
            reference=f"Used for sale {invoice_number}"
        )
        
        # Also record the usage in the customer deposit model
        models['customer_deposit'].record_deposit_usage(
            customer_id=customer_id,
            amount=sale_amount,
            usage_date=sale_date,
            reference=f"Used for sale {invoice_number}"
        )
        
        flash(f"Sale recorded successfully using customer deposit of {sale_amount:,.2f}. Invoice: {invoice_number}", "success")
        return redirect(url_for('customer_deposits_route'))
        
    except Exception as e:
        print(f"Error using customer deposit: {e}")
        flash(f'Error processing deposit usage: {str(e)}', 'error')
        return redirect(url_for('customer_deposits_route'))


@app.route('/vendor-payments', methods=['GET', 'POST'])
@auth_required
def vendor_payments_route():
    """Record vendor payments for inventory batches and prepayments"""
    models = get_models()
    accounting_service = get_accounting_service()
    
    if request.method == 'POST':
        try:
            # Get form data
            batch_id = request.form.get('batch_id')
            payment_amount = float(request.form.get('payment_amount', 0))
            payment_date_str = request.form.get('payment_date')
            payment_method = request.form.get('payment_method', 'cash')
            reference = request.form.get('reference', '')
            notes = request.form.get('notes', '')
            
            # Validate date
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
            
            # Validate amount
            if payment_amount <= 0:
                flash("Payment amount must be greater than 0.", "danger")
                return redirect(url_for('vendor_payments_route'))
            
            # Get batch information
            batch = models['inventory_batch'].get_by_id(batch_id)
            if not batch:
                flash("Inventory batch not found.", "danger")
                return redirect(url_for('vendor_payments_route'))
            
            vendor_id = batch.get('vendor_id')
            if not vendor_id:
                flash("Vendor information not found for this batch.", "danger")
                return redirect(url_for('vendor_payments_route'))
            
            # Record the payment
            payment_id = models['vendor_payment'].create_payment(
                batch_id=batch_id,
                vendor_id=vendor_id,
                payment_amount=payment_amount,
                payment_date=payment_date,
                payment_method=payment_method,
                reference=reference,
                notes=notes
            )
            
            # Create journal entry for the payment
            journal_entry_id = accounting_service.record_vendor_payment(
                vendor_id=vendor_id,
                date=payment_date,
                amount=payment_amount,
                payment_method=payment_method,
                reference=reference
            )
            
            flash(f"Payment recorded successfully! Payment ID: {payment_id}, Journal Entry: {journal_entry_id}", "success")
            
            return redirect(url_for('vendor_payments_route'))
            
        except Exception as e:
            flash(f"Error recording payment: {str(e)}", "danger")
    
    # Get data for form
    batches = models['inventory_batch'].get_all()
    vendors = models['vendor'].get_all()
    
    # Get recent payments (most recent first)
    recent_payments = models['vendor_payment'].get_recent_payments(20)
    
    # Calculate payment status for each batch
    batch_payment_status = []
    for batch in batches:
        total_paid = models['vendor_payment'].get_total_paid_for_batch(batch['id'])
        purchase_cost = batch.get('purchase_cost', 0)
        outstanding_balance = max(0, purchase_cost - total_paid)
        
        batch_payment_status.append({
            'batch': batch,
            'total_paid': total_paid,
            'outstanding_balance': outstanding_balance,
            'payment_percentage': (total_paid / purchase_cost * 100) if purchase_cost > 0 else 0,
            'is_fully_paid': outstanding_balance == 0
        })
    
    return render_template('vendor_payments.html', 
                         batches=batches,
                         vendors=vendors,
                         recent_payments=recent_payments,
                         batch_payment_status=batch_payment_status,
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/reports')
@auth_required
def reports_route():
    """Main reports page with inventory batch and vendor-based reporting"""
    models = get_models()
    
    # Get report parameters
    report_type = request.args.get('report_type', '')
    vendor_id = request.args.get('vendor_id', '')
    batch_id = request.args.get('batch_id', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # Parse dates
    start_date = None
    end_date = None
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "warning")
    
    # Get all vendors, batches, and customers for dropdowns
    vendors = models['vendor'].get_all()
    batches = models['inventory_batch'].get_all()
    customers = models['customer'].get_all()
    
    context = {
        'report_type': report_type,
        'vendor_id': vendor_id,
        'batch_id': batch_id,
        'start_date': start_date,
        'end_date': end_date,
        'vendors': vendors,
        'batches': batches,
        'customers': customers,
        'user': session["user"]
    }
    
    # Generate specific reports based on type
    if report_type == 'vendor_summary' and vendor_id:
        context.update(generate_vendor_summary_report(models, vendor_id, start_date, end_date))
    elif report_type == 'batch_detail' and batch_id:
        context.update(generate_batch_detail_report(models, batch_id))
    elif report_type == 'inventory_status':
        context.update(generate_inventory_status_report(models))
    elif report_type == 'production_summary':
        context.update(generate_production_summary_report(models, start_date, end_date))
    elif report_type == 'sales_summary':
        context.update(generate_sales_summary_report(models, start_date, end_date))
    elif report_type == 'customer_summary':
        customer_id = request.args.get('customer_id', '')
        context.update(generate_customer_summary_report(models, start_date, end_date, customer_id))
    
    return render_template('reports_accounting.html', **context)

def _compare_dates(record_date, start_date, end_date):
    """Safely compare dates that might be offset-naive or offset-aware"""
    try:
        # Convert all dates to naive datetimes for comparison
        if record_date.tzinfo is not None:
            record_date = record_date.replace(tzinfo=None)
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        return start_date <= record_date <= end_date
    except (AttributeError, TypeError):
        # If any date is None or not a datetime, skip the comparison
        return False

def generate_vendor_summary_report(models, vendor_id, start_date, end_date):
    """Generate comprehensive vendor summary report"""
    vendor = models['vendor'].get_by_id(vendor_id)
    if not vendor:
        return {'error': 'Vendor not found'}
    
    # Get all batches for this vendor
    vendor_batches = models['inventory_batch'].get_batches_by_vendor(vendor_id)
    
    # Calculate totals
    total_purchases = sum(batch.get('purchase_cost', 0) for batch in vendor_batches)
    total_pieces = sum(batch.get('total_pieces', 0) for batch in vendor_batches)
    remaining_pieces = sum(batch.get('current_pieces', 0) for batch in vendor_batches)
    processed_pieces = total_pieces - remaining_pieces
    
    # Calculate payment information
    total_paid = models['vendor_payment'].get_total_paid_to_vendor(vendor_id)
    outstanding_balance = max(0, total_purchases - total_paid)
    
    
    # Get production records for this vendor
    production_records = []
    for batch in vendor_batches:
        for ile_group in batch.get('ile_groups', []):
            for prod_record in ile_group.get('production_records', []):
                production_records.append({
                    'batch_id': batch['id'],
                    'ile_number': ile_group['ile_number'],
                    'date': prod_record.get('production_date'),
                    'pieces_processed': prod_record.get('pieces_processed', 0),
                    'processing_cost': prod_record.get('processing_cost', 0)
                })
    
    # Filter by date range if provided
    if start_date and end_date:
        production_records = [
            record for record in production_records 
            if record['date'] and _compare_dates(record['date'], start_date, end_date)
        ]
    
    total_processing_cost = sum(record['processing_cost'] for record in production_records)
    
    return {
        'vendor': vendor,
        'vendor_batches': vendor_batches,
        'total_purchases': total_purchases,
        'total_pieces': total_pieces,
        'remaining_pieces': remaining_pieces,
        'processed_pieces': processed_pieces,
        'production_records': production_records,
        'total_processing_cost': total_processing_cost,
        'average_cost_per_piece': total_purchases / total_pieces if total_pieces > 0 else 0,
        'total_paid': total_paid,
        'outstanding_balance': outstanding_balance,
        'payment_percentage': (total_paid / total_purchases * 100) if total_purchases > 0 else 0
    }

def generate_batch_detail_report(models, batch_id):
    """Generate detailed report for a specific batch"""
    batch = models['inventory_batch'].get_by_id(batch_id)
    if not batch:
        return {'error': 'Batch not found'}
    
    # Get production records for this batch
    production_records = []
    for ile_group in batch.get('ile_groups', []):
        for prod_record in ile_group.get('production_records', []):
            production_records.append({
                'ile_number': ile_group['ile_number'],
                'date': prod_record.get('production_date'),
                'pieces_processed': prod_record.get('pieces_processed', 0),
                'processing_cost': prod_record.get('processing_cost', 0),
                'remaining_pieces': ile_group.get('remaining_pieces', 0)
            })
    
    # Get sales records for this batch
    sales_records = []
    for ile_group in batch.get('ile_groups', []):
        for sale_record in ile_group.get('sales_records', []):
            sales_records.append({
                'ile_number': ile_group['ile_number'],
                'date': sale_record.get('sales_date'),
                'pieces_sold': sale_record.get('pieces_sold', 0),
                'sales_amount': sale_record.get('sales_amount', 0)
            })
    
    return {
        'batch': batch,
        'production_records': production_records,
        'sales_records': sales_records,
        'total_production_cost': sum(record['processing_cost'] for record in production_records),
        'total_sales_amount': sum(record['sales_amount'] for record in sales_records)
    }

def generate_inventory_status_report(models):
    """Generate current inventory status report"""
    batches = models['inventory_batch'].get_all()
    
    # Group by vendor
    vendor_inventory = {}
    for batch in batches:
        vendor_id = batch.get('vendor_id')
        vendor_name = batch.get('vendor_name', 'Unknown')
        
        if vendor_id not in vendor_inventory:
            vendor_inventory[vendor_id] = {
                'vendor_name': vendor_name,
                'batches': [],
                'total_pieces': 0,
                'remaining_pieces': 0,
                'total_cost': 0
            }
        
        vendor_inventory[vendor_id]['batches'].append(batch)
        vendor_inventory[vendor_id]['total_pieces'] += batch.get('total_pieces', 0)
        vendor_inventory[vendor_id]['remaining_pieces'] += batch.get('current_pieces', 0)
        vendor_inventory[vendor_id]['total_cost'] += batch.get('purchase_cost', 0)
    
    return {
        'vendor_inventory': vendor_inventory,
        'total_batches': len(batches),
        'total_pieces': sum(batch.get('total_pieces', 0) for batch in batches),
        'remaining_pieces': sum(batch.get('current_pieces', 0) for batch in batches)
    }

def generate_production_summary_report(models, start_date, end_date):
    """Generate production summary report"""
    batches = models['inventory_batch'].get_all()
    
    production_summary = []
    for batch in batches:
        for ile_group in batch.get('ile_groups', []):
            for prod_record in ile_group.get('production_records', []):
                prod_date = prod_record.get('production_date')
                
                # Filter by date range if provided
                if start_date and end_date and prod_date:
                    if not _compare_dates(prod_date, start_date, end_date):
                        continue
                
                production_summary.append({
                    'date': prod_date,
                    'recorded_at': prod_record.get('recorded_at', prod_date),
                    'vendor_name': batch.get('vendor_name'),
                    'batch_id': batch['id'],
                    'ile_number': ile_group['ile_number'],
                    'pieces_processed': prod_record.get('pieces_processed', 0),
                    'processing_cost': prod_record.get('processing_cost', 0)
                })
    
    # Sort by recorded_at (most recent first)
    production_summary.sort(key=lambda x: x.get('recorded_at', datetime.min), reverse=True)
    
    total_pieces = sum(record['pieces_processed'] for record in production_summary)
    total_cost = sum(record['processing_cost'] for record in production_summary)
    
    return {
        'production_summary': production_summary,
        'total_pieces_processed': total_pieces,
        'total_processing_cost': total_cost,
        'average_cost_per_piece': total_cost / total_pieces if total_pieces > 0 else 0
    }

def generate_sales_summary_report(models, start_date, end_date):
    """Generate sales summary report"""
    # Get all journal entries that are sales
    journal_entries = models['journal_entry'].get_all()
    sales_entries = []
    
    for entry in journal_entries:
        if 'Sale to customer' in entry.get('description', ''):
            # Filter by date range if provided
            if start_date and end_date:
                entry_date = entry.get('date', datetime.min)
                if not _compare_dates(entry_date, start_date, end_date):
                    continue
            
            # Calculate total credits for this entry
            total_credits = sum(line.get('credit', 0) for line in entry.get('entries', []))
            entry['total_credits'] = total_credits
            sales_entries.append(entry)
    
    # Calculate totals
    total_sales = sum(entry.get('total_credits', 0) for entry in sales_entries)
    
    return {
        'sales_entries': sales_entries,
        'total_sales': total_sales,
        'total_transactions': len(sales_entries)
    }

def generate_customer_summary_report(models, start_date=None, end_date=None, customer_id=None):
    """Generate customer summary report with deposits and sales"""
    try:
        # Get all customers or filter by specific customer
        customers = models['customer'].get_all()
        if customer_id:
            customers = [c for c in customers if c['id'] == customer_id]
        
        # Get customer deposits
        deposits = models['customer_deposit'].get_all()
        if start_date and end_date:
            deposits = [d for d in deposits if _compare_dates(d.get('deposit_date'), start_date, end_date)]
        
        # Get sales records - look for sales with customer information in description
        all_sales = models['journal_entry'].get_all()
        sales = []
        for sale in all_sales:
            description = sale.get('description', '')
            if 'Sale to customer' in description and 'Invoice' in description:
                sales.append(sale)
        
        if start_date and end_date:
            sales = [s for s in sales if _compare_dates(s.get('date'), start_date, end_date)]
        
        # Calculate customer statistics
        customer_stats = []
        for customer in customers:
            customer_id = customer['id']
            customer_name = customer['name']
            
            # Calculate deposits for this customer
            customer_deposits = [d for d in deposits if d.get('customer_id') == customer_id]
            total_deposits = sum(d.get('amount', 0) for d in customer_deposits)
            
            # Calculate sales for this customer (from journal entries)
            customer_sales = []
            total_sales = 0
            for sale in sales:
                # Check if this sale is for this customer by looking at the description
                description = sale.get('description', '')
                # Look for "Sale to customer {customer_id}" pattern
                if f"Sale to customer {customer_id}" in description:
                    amount = 0
                    payment_at_sale = 0
                    for entry in sale.get('entries', []):
                        if entry.get('account_code') == '4000':  # Revenue account
                            amount = entry.get('credit', 0)
                        if entry.get('account_code') in ('1000', '1100'):
                            payment_at_sale += entry.get('debit', 0) or 0
                    if amount > 0:
                        customer_sales.append({
                            'date': sale.get('date'),
                            'created_at': sale.get('created_at', sale.get('date')),
                            'amount': amount,
                            'reference': sale.get('reference', ''),
                            'description': description,
                            'payment_at_sale': payment_at_sale
                        })
                        total_sales += amount
            
            # Treat payments at time of sale as deposit-equivalent inflows for balance calc
            total_payments_at_sale = sum(s.get('payment_at_sale', 0) for s in customer_sales)
            total_inflows = total_deposits + total_payments_at_sale
            # Balance heuristic: inflows (deposits + payments) minus sales billed
            current_balance = total_inflows - total_sales
            
            # Sort deposits and sales by date (most recent first)
            sorted_deposits = sorted(customer_deposits, key=lambda x: x.get('created_at', datetime.min), reverse=True)
            sorted_sales = sorted(customer_sales, key=lambda x: x.get('created_at', datetime.min), reverse=True)
            
            customer_stats.append({
                'customer_id': customer_id,
                'customer_name': customer_name,
                'total_deposits': total_deposits,
                'total_payments_at_sale': total_payments_at_sale,
                'total_inflows': total_inflows,
                'total_sales': total_sales,
                'current_balance': current_balance,
                'deposit_count': len(customer_deposits),
                'sales_count': len(customer_sales),
                'recent_deposits': sorted_deposits,  # Show all deposits, not just recent 5
                'recent_sales': sorted_sales  # Show all sales, not just recent 5
            })
        
        # Sort by current balance (highest credit first)
        customer_stats.sort(key=lambda x: x['current_balance'], reverse=True)
        
        # Calculate totals
        total_deposits = sum(c['total_deposits'] for c in customer_stats)
        total_sales = sum(c['total_sales'] for c in customer_stats)
        total_balance = sum(c['current_balance'] for c in customer_stats)
        
        return {
            'report_title': 'Customer Summary Report',
            'report_data': {
                'customers': customer_stats,
                'summary': {
                    'total_customers': len(customer_stats),
                    'total_deposits': total_deposits,
                    'total_sales': total_sales,
                    'total_balance': total_balance
                }
            }
        }
        
    except Exception as e:
        print(f"Error generating customer summary report: {e}")
        return {
            'report_title': 'Customer Summary Report',
            'report_data': {
                'customers': [],
                'summary': {
                    'total_customers': 0,
                    'total_deposits': 0,
                    'total_sales': 0,
                    'total_balance': 0
                },
                'error': str(e)
            }
        }

@app.route('/reports/profit-loss')
@auth_required
def profit_loss_report():
    """Generate Profit & Loss Statement"""
    accounting_service = get_accounting_service()
    
    # Get date range from query parameters
    start_date_str = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # Generate P&L statement
    pnl_data = accounting_service.generate_profit_loss_statement(start_date, end_date)
    
    return render_template('reports/profit_loss.html', 
                         pnl_data=pnl_data, 
                         user=session["user"])

@app.route('/reports/balance-sheet')
@auth_required
def balance_sheet_report():
    """Generate Balance Sheet"""
    accounting_service = get_accounting_service()
    
    # Get as-of date from query parameters
    as_of_date_str = request.args.get('as_of_date', datetime.now().strftime('%Y-%m-%d'))
    as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
    
    # Generate balance sheet
    balance_sheet_data = accounting_service.generate_balance_sheet(as_of_date)
    
    return render_template('reports/balance_sheet.html', 
                         balance_sheet_data=balance_sheet_data, 
                         user=session["user"])

@app.route('/trial-balance')
@auth_required
def trial_balance():
    """Generate Trial Balance"""
    accounting_service = get_accounting_service()
    
    # Get as-of date from query parameters
    as_of_date_str = request.args.get('as_of_date', datetime.now().strftime('%Y-%m-%d'))
    as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
    
    # Generate trial balance
    trial_balance_data = accounting_service.get_trial_balance(as_of_date)
    
    return render_template('reports/trial_balance.html', 
                         trial_balance_data=trial_balance_data, 
                         as_of_date=as_of_date.strftime('%Y-%m-%d'),
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/customers', methods=['GET', 'POST'])
@auth_required
def customers_route():
    """Manage customers"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('test_name')
            phone_number = request.form.get('test_phone', '')
            email = request.form.get('test_email', '')
            address = request.form.get('test_address', '')
            credit_limit = float(request.form.get('test_credit', 0))
            
            # Debug: Print form data
            print(f"DEBUG - Form data: name='{name}', phone='{phone_number}', email='{email}', address='{address}', credit_limit={credit_limit}")
            print(f"DEBUG - Name type: {type(name)}, Name repr: {repr(name)}")
            print(f"DEBUG - All form keys: {list(request.form.keys())}")
            print(f"DEBUG - Raw form data: {dict(request.form)}")
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Customer name is required.", "danger")
                return redirect(url_for('customers_route'))
            
            customer_id = models['customer'].create_customer(
                name=name.strip(),
                phone_number=phone_number,
                email=email,
                address=address,
                credit_limit=credit_limit
            )
            
            flash(f"Customer '{name.strip()}' created successfully.", "success")
            return redirect(url_for('customers_route'))
            
        except Exception as e:
            flash(f"Error creating customer: {str(e)}", "danger")
    
    # Get all customers
    customers = models['customer'].get_all()
    
    return render_template('customers.html', 
                         customers=customers, 
                         user=session["user"])

@app.route('/vendors', methods=['GET', 'POST'])
@auth_required
def vendors_route():
    """Manage vendors"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('vendor_name')
            phone_number = request.form.get('vendor_phone', '')
            email = request.form.get('vendor_email', '')
            address = request.form.get('vendor_address', '')
            contact_person = request.form.get('vendor_contact', '')
            payment_terms = request.form.get('vendor_payment', 'net_30')
            
            # Debug: Print form data
            print(f"DEBUG - Vendor form data: name='{name}', phone='{phone_number}', email='{email}', address='{address}', contact_person='{contact_person}', payment_terms='{payment_terms}'")
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Vendor name is required.", "danger")
                return redirect(url_for('vendors_route'))
            
            vendor_id = models['vendor'].create_vendor(
                name=name.strip(),
                phone_number=phone_number,
                email=email,
                address=address,
                contact_person=contact_person,
                payment_terms=payment_terms
            )
            
            flash(f"Vendor '{name.strip()}' created successfully.", "success")
            return redirect(url_for('vendors_route'))
            
        except Exception as e:
            flash(f"Error creating vendor: {str(e)}", "danger")
    
    # Get all vendors
    vendors = models['vendor'].get_all()
    
    return render_template('vendors.html', 
                         vendors=vendors, 
                         user=session["user"])

@app.route('/products', methods=['GET', 'POST'])
@auth_required
def products_route():
    """Manage products"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('product_name')
            description = request.form.get('product_description', '')
            wholesale_price = float(request.form.get('product_wholesale', 0))
            retail_price = float(request.form.get('product_retail', 0))
            unit_of_measure = request.form.get('product_unit', 'piece')
            category = request.form.get('product_category', 'ponmo')
            
            # Debug: Print form data
            print(f"DEBUG - Product form data: name='{name}', description='{description}', wholesale_price={wholesale_price}, retail_price={retail_price}, unit_of_measure='{unit_of_measure}', category='{category}'")
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Product name is required.", "danger")
                return redirect(url_for('products_route'))
            
            product_id = models['product'].create_product(
                name=name.strip(),
                description=description,
                wholesale_price=wholesale_price,
                retail_price=retail_price,
                unit_of_measure=unit_of_measure,
                category=category
            )
            
            flash(f"Product '{name.strip()}' created successfully.", "success")
            return redirect(url_for('products_route'))
            
        except Exception as e:
            flash(f"Error creating product: {str(e)}", "danger")
    
    # Get all products
    products = models['product'].get_all()
    
    return render_template('products.html', 
                         products=products, 
                         user=session["user"])

@app.route('/setup_business', methods=['GET', 'POST'])
def setup_business():
    """Setup business details for new users"""
    pending_user = session.get("pending_user")

    if not pending_user:
        flash("Unauthorized access. Please sign in first.", "danger")
        return redirect(url_for("login"))

    if request.method == 'POST':
        business_name = request.form.get("business_name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()

        if not business_name or not phone_number:
            flash("Business name and phone number are required.", "danger")
            return redirect(url_for("setup_business"))

        # Save details in Firestore
        user_id = pending_user["uid"]
        user_email = pending_user["email"]
        db.collection("users").document(user_id).set({
            "email": user_email,
            "business_name": business_name,
            "phone_number": phone_number,
            "created_at": datetime.utcnow()
        })

        # Initialize accounting structure for new user
        accounting_ref = db.collection(f"user_data_{user_id}").document("accounting")
        accounting_ref.set({
            "initialized_at": datetime.utcnow(),
            "chart_of_accounts_version": "1.0"
        })

        # Store user in session
        session["user"] = {
            "uid": user_id,
            "email": user_email,
            "business_name": business_name,
            "phone_number": phone_number
        }

        session.pop("pending_user", None)

        flash("Business details saved successfully! Redirecting to dashboard...", "success")
        return redirect(url_for("dashboard"))

    return render_template("setup_business.html", user=pending_user)

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html', current_date=datetime.now())

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html', current_date=datetime.now())

@app.route('/reset-password')
def reset_password():
    """Password reset page"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('forgot_password.html')

@app.route('/auth', methods=['POST'])
def authorize():
    """Google OAuth authentication"""
    print("=== AUTH DEBUG START ===")
    print(f"Request method: {request.method}")
    print(f"Request content type: {request.content_type}")
    print(f"Request JSON: {request.json}")
    
    token = request.json.get("idToken")
    print(f"Token received: {'YES' if token else 'NO'}")
    print(f"Token length: {len(token) if token else 0}")
    
    if not token:
        print("ERROR: No token received")
        return {"status": "error", "message": "Unauthorized: No token received"}, 401

    try:
        print("Attempting to verify token with Firebase...")
        # Verify the token with Firebase
        decoded_token = auth.verify_id_token(token)
        print(f"Token verification successful!")
        print(f"Decoded token keys: {list(decoded_token.keys())}")
        
        user_id = decoded_token.get("uid")
        user_email = decoded_token.get("email")
        print(f"User ID: {user_id}")
        print(f"User Email: {user_email}")

        if not user_id or not user_email:
            print("ERROR: Missing user info in token")
            return {"status": "error", "message": "Unauthorized: Missing user info"}, 401

        print("Checking user in database...")
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        print(f"User document exists: {user_doc.exists}")

        # First-time Google user
        if not user_doc.exists:
            print("First-time user - redirecting to setup")
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}

        user_data = user_doc.to_dict()
        print(f"User data: {user_data}")

        # Ensure business details are set
        if not user_data.get("business_name") or not user_data.get("phone_number"):
            print("User missing business details - redirecting to setup")
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}

        print("User authenticated successfully - storing in session")
        # Store user in session
        session["user"] = {
            "uid": user_id,
            "email": user_email,
            "business_name": user_data["business_name"],
            "phone_number": user_data["phone_number"],
        }

        print("=== AUTH DEBUG END - SUCCESS ===")
        return {"status": "success"}

    except Exception as e:
        print(f"=== AUTH DEBUG END - ERROR ===")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"Exception details: {e}")
        return {"status": "error", "message": str(e)}, 401

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route('/stock')
@auth_required
def stock_route():
    """Stock/Inventory management page"""
    return render_template('stock.html', user=session["user"])

@app.route('/expenses', methods=['GET', 'POST'])
@auth_required
def expenses_route():
    """Record expenses with proper accounting"""
    accounting_service = get_accounting_service()
    
    if request.method == 'POST':
        try:
            # Get form data
            expense_date_str = request.form.get('expense_date')
            expense_type = request.form.get('expense_type')
            account_code = request.form.get('account_code')
            description = request.form.get('description')
            amount = float(request.form.get('amount', 0))
            payment_method = request.form.get('payment_method', 'cash')
            vendor = request.form.get('vendor', '')
            notes = request.form.get('notes', '')
            reference = request.form.get('reference', f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            # Validate date
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d')
            
            # Validate amount
            if amount <= 0:
                flash("Expense amount must be greater than 0.", "danger")
                return redirect(url_for('expenses_route'))
            
            # Record the expense using accounting service
            journal_entry_id = accounting_service.record_expense(
                date=expense_date,
                account_code=account_code,
                amount=amount,
                description=description,
                payment_method=payment_method,
                reference=reference
            )
            
            flash(f"Expense recorded successfully. Journal Entry: {journal_entry_id}", "success")
            return redirect(url_for('expenses_route'))
            
        except Exception as e:
            flash(f"Error recording expense: {str(e)}", "danger")
    
    # Get recent expenses for display
    models = get_models()
    expenses = []  # Placeholder - would need to implement expense model
    
    return render_template('expenses.html', 
                         expenses=expenses,
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/debug-form', methods=['POST'])
def debug_form():
    """Debug form submission"""
    print("=== DEBUG FORM SUBMISSION ===")
    print(f"Form data: {dict(request.form)}")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print("=============================")
    return f"Form data received: {dict(request.form)}"

@app.route('/delete-vendor/<vendor_id>', methods=['POST'])
@auth_required
def delete_vendor(vendor_id):
    """Delete a vendor"""
    try:
        models = get_models()
        success = models['vendor'].delete(vendor_id)
        if success:
            flash("Vendor deleted successfully.", "success")
        else:
            flash("Failed to delete vendor.", "danger")
    except Exception as e:
        flash(f"Error deleting vendor: {str(e)}", "danger")
    
    return redirect(url_for('vendors_route'))

@app.route('/delete-customer/<customer_id>', methods=['POST'])
@auth_required
def delete_customer(customer_id):
    """Delete a customer"""
    try:
        models = get_models()
        success = models['customer'].delete(customer_id)
        if success:
            flash("Customer deleted successfully.", "success")
        else:
            flash("Failed to delete customer.", "danger")
    except Exception as e:
        flash(f"Error deleting customer: {str(e)}", "danger")
    
    return redirect(url_for('customers_route'))

@app.route('/delete-product/<product_id>', methods=['POST'])
@auth_required
def delete_product(product_id):
    """Delete a product"""
    try:
        models = get_models()
        success = models['product'].delete(product_id)
        if success:
            flash("Product deleted successfully.", "success")
        else:
            flash("Failed to delete product.", "danger")
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", "danger")
    
    return redirect(url_for('products_route'))

@app.route('/edit-customer/<customer_id>', methods=['GET', 'POST'])
@auth_required
def edit_customer(customer_id):
    """Edit a customer"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('test_name')
            phone_number = request.form.get('test_phone', '')
            email = request.form.get('test_email', '')
            address = request.form.get('test_address', '')
            credit_limit = float(request.form.get('test_credit', 0))
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Customer name is required.", "danger")
                return redirect(url_for('edit_customer', customer_id=customer_id))
            
            # Update customer
            success = models['customer'].update_customer(customer_id, {
                'name': name.strip(),
                'phone_number': phone_number,
                'email': email,
                'address': address,
                'credit_limit': credit_limit
            })
            
            if success:
                flash("Customer updated successfully.", "success")
                return redirect(url_for('customers_route'))
            else:
                flash("Failed to update customer.", "danger")
                
        except Exception as e:
            flash(f"Error updating customer: {str(e)}", "danger")
    
    # Get customer data for editing
    customer = models['customer'].get_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers_route'))
    
    return render_template('edit_customer.html', customer=customer, user=session["user"])

@app.route('/edit-vendor/<vendor_id>', methods=['GET', 'POST'])
@auth_required
def edit_vendor(vendor_id):
    """Edit a vendor"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('vendor_name')
            phone_number = request.form.get('vendor_phone', '')
            email = request.form.get('vendor_email', '')
            address = request.form.get('vendor_address', '')
            contact_person = request.form.get('vendor_contact', '')
            payment_terms = request.form.get('vendor_payment', 'net_30')
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Vendor name is required.", "danger")
                return redirect(url_for('edit_vendor', vendor_id=vendor_id))
            
            # Update vendor
            success = models['vendor'].update_vendor(vendor_id, {
                'name': name.strip(),
                'phone_number': phone_number,
                'email': email,
                'address': address,
                'contact_person': contact_person,
                'payment_terms': payment_terms
            })
            
            if success:
                flash("Vendor updated successfully.", "success")
                return redirect(url_for('vendors_route'))
            else:
                flash("Failed to update vendor.", "danger")
                
        except Exception as e:
            flash(f"Error updating vendor: {str(e)}", "danger")
    
    # Get vendor data for editing
    vendor = models['vendor'].get_by_id(vendor_id)
    if not vendor:
        flash("Vendor not found.", "danger")
        return redirect(url_for('vendors_route'))
    
    return render_template('edit_vendor.html', vendor=vendor, user=session["user"])

@app.route('/edit-product/<product_id>', methods=['GET', 'POST'])
@auth_required
def edit_product(product_id):
    """Edit a product"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            name = request.form.get('product_name')
            description = request.form.get('product_description', '')
            wholesale_price = float(request.form.get('product_wholesale', 0))
            retail_price = float(request.form.get('product_retail', 0))
            unit_of_measure = request.form.get('product_unit', 'piece')
            category = request.form.get('product_category', 'ponmo')
            
            # Validate name is not empty
            if not name or name.strip() == '':
                flash("Product name is required.", "danger")
                return redirect(url_for('edit_product', product_id=product_id))
            
            # Update product
            success = models['product'].update_product(product_id, {
                'name': name.strip(),
                'description': description,
                'wholesale_price': wholesale_price,
                'retail_price': retail_price,
                'unit_of_measure': unit_of_measure,
                'category': category
            })
            
            if success:
                flash("Product updated successfully.", "success")
                return redirect(url_for('products_route'))
            else:
                flash("Failed to update product.", "danger")
                
        except Exception as e:
            flash(f"Error updating product: {str(e)}", "danger")
    
    # Get product data for editing
    product = models['product'].get_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products_route'))
    
    return render_template('edit_product.html', product=product, user=session["user"])

@app.route('/inventory-batches', methods=['GET', 'POST'])
@auth_required
def inventory_batches_route():
    """Manage inventory batches"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            vendor_id = request.form.get('vendor_id')
            raw_material_type = request.form.get('raw_material_type', 'cow_skin')
            total_ile = int(request.form.get('total_ile', 1))
            pieces_per_ile = int(request.form.get('pieces_per_ile', 100))
            purchase_cost = float(request.form.get('purchase_cost', 0))
            purchase_date_str = request.form.get('purchase_date')
            payment_method = request.form.get('payment_method', 'accounts_payable')
            reference = request.form.get('reference', '')
            
            # Get vendor info
            vendor = models['vendor'].get_by_id(vendor_id)
            if not vendor:
                flash("Vendor not found.", "danger")
                return redirect(url_for('inventory_batches_route'))
            
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d') if purchase_date_str else datetime.now()
            
            # Create batch
            batch_id = models['inventory_batch'].create_batch(
                vendor_id=vendor_id,
                vendor_name=vendor['name'],
                raw_material_type=raw_material_type,
                total_ile=total_ile,
                pieces_per_ile=pieces_per_ile,
                purchase_cost=purchase_cost,
                purchase_date=purchase_date,
                payment_method=payment_method,
                reference=reference
            )
            
            # Record the purchase in accounting system
            accounting_service = get_accounting_service()
            journal_entry_id = accounting_service.record_purchase_from_batch(
                batch_id=batch_id,
                vendor_id=vendor_id,
                date=purchase_date,
                raw_materials_cost=purchase_cost,
                quantity=total_ile * pieces_per_ile,
                reference=reference or f"Batch {batch_id[:8]}...",
                payment_method=payment_method
            )
            
            flash(f"Inventory batch created successfully! Batch ID: {batch_id}", "success")
            return redirect(url_for('inventory_batches_route'))
            
        except Exception as e:
            flash(f"Error creating inventory batch: {str(e)}", "danger")
    
    # Get all batches and vendors
    batches = models['inventory_batch'].get_all()
    vendors = models['vendor'].get_all()
    
    return render_template('inventory_batches.html', 
                         batches=batches, 
                         vendors=vendors, 
                         current_date=datetime.now(),
                         user=session["user"])

@app.route('/batch-details/<batch_id>')
@auth_required
def batch_details_route(batch_id):
    """View detailed information about a specific batch"""
    models = get_models()
    
    batch = models['inventory_batch'].get_by_id(batch_id)
    if not batch:
        flash("Batch not found.", "danger")
        return redirect(url_for('inventory_batches_route'))
    
    # Get profitability metrics
    profitability = models['inventory_batch'].calculate_batch_profitability(batch_id)
    
    return render_template('batch_details.html', 
                         batch=batch, 
                         profitability=profitability,
                         current_date=datetime.now(),
                         user=session["user"])


@app.route('/delete-batch/<batch_id>', methods=['POST'])
@auth_required
def delete_batch(batch_id):
    """Delete an inventory batch and its associated journal entries"""
    models = get_models()
    
    try:
        # Get the batch first to check if it exists
        batch = models['inventory_batch'].get_by_id(batch_id)
        if not batch:
            flash("Inventory batch not found.", "danger")
            return redirect(url_for('inventory_batches_route'))
        
        # Check if batch has any sales or production records
        has_sales = any(ile_group.get('sales_records') for ile_group in batch.get('ile_groups', []))
        has_production = any(ile_group.get('production_records') for ile_group in batch.get('ile_groups', []))
        
        if has_sales or has_production:
            flash("Cannot delete batch that has sales or production records. Please delete those records first.", "danger")
            return redirect(url_for('inventory_batches_route'))
        
        # Delete associated journal entries
        all_entries = models['journal_entry'].get_all()
        deleted_entries = 0
        for entry in all_entries:
            description = entry.get('description', '')
            if batch_id in description:
                models['journal_entry'].delete(entry['id'])
                deleted_entries += 1
        
        # Delete the batch
        success = models['inventory_batch'].delete(batch_id)
        
        if success:
            flash(f"Inventory batch deleted successfully. {deleted_entries} associated journal entries also deleted.", "success")
        else:
            flash("Failed to delete inventory batch.", "danger")
            
    except Exception as e:
        flash(f"Error deleting inventory batch: {str(e)}", "danger")
    
    return redirect(url_for('inventory_batches_route'))

@app.route('/edit-batch/<batch_id>', methods=['GET', 'POST'])
@auth_required
def edit_batch(batch_id):
    """Edit an inventory batch"""
    models = get_models()
    
    if request.method == 'POST':
        try:
            # Get form data
            vendor_id = request.form.get('vendor_id')
            raw_material_type = request.form.get('raw_material_type', 'cow_skin')
            total_ile = int(request.form.get('total_ile', 1))
            pieces_per_ile = int(request.form.get('pieces_per_ile', 100))
            purchase_cost = float(request.form.get('purchase_cost', 0))
            purchase_date_str = request.form.get('purchase_date')
            payment_method = request.form.get('payment_method', 'accounts_payable')
            reference = request.form.get('reference', '')
            
            # Get vendor info
            vendor = models['vendor'].get_by_id(vendor_id)
            if not vendor:
                flash("Vendor not found.", "danger")
                return redirect(url_for('edit_batch', batch_id=batch_id))
            
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d') if purchase_date_str else datetime.now()
            
            # Update batch data
            batch_data = {
                'vendor_id': vendor_id,
                'vendor_name': vendor['name'],
                'raw_material_type': raw_material_type,
                'total_ile': total_ile,
                'pieces_per_ile': pieces_per_ile,
                'total_pieces': total_ile * pieces_per_ile,
                'purchase_cost': purchase_cost,
                'purchase_date': purchase_date,
                'payment_method': payment_method,
                'reference': reference,
                'updated_at': datetime.now()
            }
            
            # Update the batch
            success = models['inventory_batch'].update(batch_id, batch_data)
            
            if success:
                flash("Inventory batch updated successfully.", "success")
                return redirect(url_for('inventory_batches_route'))
            else:
                flash("Failed to update inventory batch.", "danger")
                
        except Exception as e:
            flash(f"Error updating inventory batch: {str(e)}", "danger")
    
    # Get batch data for editing
    batch = models['inventory_batch'].get_by_id(batch_id)
    if not batch:
        flash("Inventory batch not found.", "danger")
        return redirect(url_for('inventory_batches_route'))
    
    # Get vendors for dropdown
    vendors = models['vendor'].get_all()
    
    return render_template('edit_batch.html', 
                         batch=batch, 
                         vendors=vendors, 
                         current_date=datetime.now(),
                         user=session["user"])

# ----------------------------------------------------------------------
# Financial Statements Routes
# ----------------------------------------------------------------------

@app.route('/financial-statements/trial-balance')
def trial_balance_route():
    """Trial Balance page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        from src.services.financial_statements_service import FinancialStatementsService
        models = get_models()
        
        # Get date parameter
        as_of_date_str = request.args.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            try:
                as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid date format. Using current date.", "warning")
        
        # Generate trial balance
        financial_service = FinancialStatementsService(models['journal_entry'])
        trial_balance_data = financial_service.get_trial_balance(as_of_date)
        
        return render_template('financial_statements/trial_balance.html',
                             trial_balance=trial_balance_data,
                             current_date=datetime.now(),
                             user=session["user"])
    
    except Exception as e:
        print(f"Error generating trial balance: {str(e)}")
        flash(f"Error generating trial balance: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/financial-statements/profit-loss')
def profit_loss_route():
    """Profit & Loss Statement page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        from src.services.financial_statements_service import FinancialStatementsService
        models = get_models()
        
        # Get date parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid start date format.", "warning")
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid end date format.", "warning")
        
        # Generate profit & loss statement
        financial_service = FinancialStatementsService(models['journal_entry'])
        profit_loss_data = financial_service.get_profit_loss_statement(start_date, end_date)
        
        return render_template('financial_statements/profit_loss.html',
                             profit_loss=profit_loss_data,
                             current_date=datetime.now(),
                             user=session["user"])
    
    except Exception as e:
        print(f"Error generating profit & loss statement: {str(e)}")
        flash(f"Error generating profit & loss statement: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/financial-statements/balance-sheet')
def balance_sheet_route():
    """Balance Sheet page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        from src.services.financial_statements_service import FinancialStatementsService
        models = get_models()
        
        # Get date parameter
        as_of_date_str = request.args.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            try:
                as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid date format. Using current date.", "warning")
        
        # Generate balance sheet
        financial_service = FinancialStatementsService(models['journal_entry'])
        balance_sheet_data = financial_service.get_balance_sheet(as_of_date)
        
        return render_template('financial_statements/balance_sheet.html',
                             balance_sheet=balance_sheet_data,
                             current_date=datetime.now(),
                             user=session["user"])
    
    except Exception as e:
        print(f"Error generating balance sheet: {str(e)}")
        flash(f"Error generating balance sheet: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/financial-statements/summary')
def financial_summary_route():
    """Comprehensive Financial Summary page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        from src.services.financial_statements_service import FinancialStatementsService
        models = get_models()
        
        # Get date parameter
        as_of_date_str = request.args.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            try:
                as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid date format. Using current date.", "warning")
        
        # Generate comprehensive financial summary
        financial_service = FinancialStatementsService(models['journal_entry'])
        financial_summary = financial_service.get_financial_summary(as_of_date)
        
        return render_template('financial_statements/financial_summary.html',
                             summary=financial_summary,
                             current_date=datetime.now(),
                             user=session["user"])
    
    except Exception as e:
        print(f"Error generating financial summary: {str(e)}")
        flash(f"Error generating financial summary: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

# ----------------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # app.run(debug=True, port=5001)
    app.run(debug=False)