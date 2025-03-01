from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from datetime import datetime, timedelta
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, url_for, session
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from functools import wraps


load_dotenv()

app = Flask(__name__)

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
app.secret_key = os.getenv('SECRET_KEY')

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True       # Ensure cookies are sent over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True     # Prevent JavaScript access to cookies
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Firebase Admin SDK and Firestore client
cred = credentials.Certificate("firebase-auth.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

########################################
# Authentication Decorator
########################################
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.route('/')
def home():
    return render_template('home.html')

# ------------------------------
# Login Route
# ------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            # Authenticate user with Firebase (just checks existence)
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


# ------------------------------
# Signup Route
# ------------------------------
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

        # Create a user-specific collection
        user_collection_ref = db.collection(f"user_data_{user_id}")
        user_collection_ref.document("metadata").set({
            "business_name": business_name,
            "created_at": datetime.utcnow()
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


# ------------------------------
# Google Authentication (OAuth)
# ------------------------------
@app.route('/auth', methods=['POST'])
def authorize():
    token = request.json.get("idToken")
    if not token:
        return {"status": "error", "message": "Unauthorized: No token received"}, 401

    try:
        # Verify the token with Firebase
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        user_email = decoded_token.get("email")

        if not user_id or not user_email:
            return {"status": "error", "message": "Unauthorized: Missing user info"}, 401

        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        # First-time Google user
        if not user_doc.exists:
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}

        user_data = user_doc.to_dict()

        # Ensure business details are set
        if not user_data.get("business_name") or not user_data.get("phone_number"):
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}

        # Store user in session
        session["user"] = {
            "uid": user_id,
            "email": user_email,
            "business_name": user_data["business_name"],
            "phone_number": user_data["phone_number"],
        }

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}, 401


# ------------------------------
# Setup Business Route
# ------------------------------
@app.route('/setup_business', methods=['GET', 'POST'])
def setup_business():
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

        # Create user-specific collection if not already created
        user_collection_ref = db.collection(f"user_data_{user_id}")
        user_collection_ref.document("metadata").set({
            "business_name": business_name,
            "created_at": datetime.utcnow()
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

    return render_template("setup_business.html")


@app.route('/reset-password')
def reset_password():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('forgot_password.html')


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ------------------------------
# Verify Token (Optional, for Google)
# ------------------------------
@app.route("/verify-token", methods=["POST"])
def verify_token():
    token = request.json.get("idToken")
    if not token:
        return {"status": "error", "message": "Unauthorized: No token received"}, 401

    try:
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        user_email = decoded_token.get("email")

        if not user_id or not user_email:
            return {"status": "error", "message": "Unauthorized: Missing user info"}, 401

        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}, 200

        user_data = user_doc.to_dict()
        if not user_data.get("business_name") or not user_data.get("phone_number"):
            session["pending_user"] = {"uid": user_id, "email": user_email}
            return {"status": "setup"}, 200

        session["user"] = {
            "uid": user_id,
            "email": user_email,
            "business_name": user_data["business_name"],
            "phone_number": user_data["phone_number"],
        }
        return {"status": "success"}, 200

    except Exception as e:
        return {"status": "error", "message": f"Unauthorized: {str(e)}"}, 401


# ------------------------------
# Dashboard
# ------------------------------
@app.route('/dashboard')
@auth_required
def dashboard():
    return render_template("dashboard.html", user=session["user"])


@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


# ------------------------------
# Sales Route
# ------------------------------
@app.route('/sales', methods=['GET', 'POST'])
@auth_required
def sales_route():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")
    user_ref = db.collection("users").document(user_id)  # Fetch user document

    if request.method == 'POST':
        try:
            # Validate and parse date
            date_str = request.form.get('date')
            datetime.strptime(date_str, '%Y-%m-%d')

            # Fetch "customer" and "vendor" from user_data_{user_id}
            customer_id = request.form.get('customer')
            customer_doc = user_data_collection.document(customer_id).get()
            if not customer_doc.exists or customer_doc.to_dict().get("type") != "customer":
                raise ValueError("Invalid customer selected")

            vendor_id = request.form.get('vendor')
            vendor_doc = user_data_collection.document(vendor_id).get()
            if not vendor_doc.exists or vendor_doc.to_dict().get("type") != "vendor":
                raise ValueError("Invalid vendor selected")

            # Get product details from form
            products = request.form.getlist('product[]')
            quantities1 = request.form.getlist('quantity1[]')
            quantities2 = request.form.getlist('quantity2[]')
            subtotals = request.form.getlist('subtotal[]')

            if not products:
                raise ValueError("No products selected")

            product_details = []
            total_amount = 0
            for i in range(len(products)):
                subtotal = float(subtotals[i])
                quantity1 = int(quantities1[i])
                quantity2 = int(quantities2[i])
                total_amount += subtotal

                product_details.append({
                    'product': products[i],
                    'quantity1': quantity1,
                    'quantity2': quantity2,
                    'subtotal': subtotal
                })

            # 🔥 Fetch last invoice number from user's document
            user_doc = user_ref.get()
            if user_doc.exists:
                last_invoice_number = user_doc.to_dict().get("last_invoice_number", 0)
            else:
                last_invoice_number = 0  # Default if user doc is missing

            # Increment invoice number
            new_invoice_number = f"{last_invoice_number + 1:06d}"

            #get payment method
            payment_method = request.form.get('payment_method')

            if payment_method == "bank":
                bank_name = request.form.get('bank_name')
            else:
                bank_name = "N/A"
            amount_paid = request.form.get('amount_paid')
            if not amount_paid:
                amount_paid = 0
            amount_paid = float(amount_paid)

            # Store sale in user_data_{user_id} with type="sale"
            sale_data = {
                'type': 'sale',
                'date': date_str,
                'invoice_number': new_invoice_number,
                'customer_id': customer_id,
                'vendor_id': vendor_id,
                'total_amount': total_amount,
                'products': product_details,
                'created_at': datetime.utcnow(),
                'bank_name': bank_name,
                'payment_method': payment_method,
                'amount_paid': amount_paid
            }
            user_data_collection.add(sale_data)

            # 🔥 Update user's last invoice number (No indexing required)
            user_ref.update({"last_invoice_number": last_invoice_number + 1})

            flash(f"Sale recorded with invoice {new_invoice_number}.", "success")
            return redirect(url_for('sales_route'))

        except ValueError as e:
            flash(f"Input Error: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error processing sale: {str(e)}", "danger")

    # Fetch customers, vendors, and products from user_data_{user_id}
    customers = []
    vendors = []
    products = []
    bank_names = []

    for doc in user_data_collection.where("type", "==", "customer").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        customers.append(doc_dict)

    for doc in user_data_collection.where("type", "==", "vendor").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        vendors.append(doc_dict)

    for doc in user_data_collection.where("type", "==", "product").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        products.append(doc_dict)

    for doc in user_data_collection.where("type", "==", "bank").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        bank_names.append(doc_dict)

    return render_template('sales.html', customers=customers, vendors=vendors, products=products, bank_names=bank_names, user=session["user"])


# ------------------------------
# Deposit Route
# ------------------------------
@app.route('/deposit', methods=['GET', 'POST'])
@auth_required
def deposit_route():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")


    if request.method == 'POST':
        try:
            date_str = request.form.get('date')
            datetime.strptime(date_str, '%Y-%m-%d')
            customer_id = request.form.get('customer')
            amount_str = request.form.get('amount_paid')
            # vendor_id = request.form.get('vendor')
            # vendor_doc = user_data_collection.document(vendor_id).get()
            # if not vendor_doc.exists or vendor_doc.to_dict().get("type") != "vendor":
            #     raise ValueError("Invalid vendor selected")
            
            if not amount_str:
                raise ValueError("Amount is required")
            amount = float(amount_str)

            bank_or_cash = request.form.get('payment_method')
            #get bank name
            if bank_or_cash:
                bank_name = request.form.get('bank_name')
            else:
                bank_name = "N/A"

            if bank_or_cash == "cash":
                bank_name = "N/A"
            deposit_data = {
                "type": "deposit",
                "date": date_str,
                "customer_id": customer_id,
                "amount": amount,
                "created_at": datetime.utcnow(),
                "bank_name": bank_name,
                "payment_method": bank_or_cash
                # 'vendor_id': vendor_id
                
            }
            user_data_collection.add(deposit_data)

            flash("Deposit recorded successfully.", "success")
            return redirect(url_for('deposit_route'))
        except Exception as e:
            flash(f"Error processing deposit: {str(e)}", "danger")
            return redirect(url_for('deposit_route'))

    # Fetch customers from user_data_{user_id} with type="customer"
    customers = []
    bank_names = []
    vendors = []

    for doc in user_data_collection.where("type", "==", "vendor").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        vendors.append(doc_dict)
    for doc in user_data_collection.where("type", "==", "bank").stream():
        data = doc.to_dict()
        data['id'] = doc.id
        bank_names.append(data)
    for doc in user_data_collection.where("type", "==", "customer").stream():
        data = doc.to_dict()
        data['id'] = doc.id
        customers.append(data)
    return render_template('deposit.html', customers=customers, bank_names=bank_names, vendors=vendors, user=session["user"])



# ------------------------------
# Expenses Route
# ------------------------------
@app.route('/expenses', methods=['GET', 'POST'])
@auth_required
def expenses_route():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")

    # Fetch vendors (used when category is "awo")
    vendors = []
    for doc in user_data_collection.where("type", "==", "vendor").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        vendors.append(doc_dict)

    # Fetch bank names (for bank transfer payment method)
    bank_names = []
    for doc in user_data_collection.where("type", "==", "bank").stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        bank_names.append(doc_dict)

    if request.method == 'POST':
        try:
            date_str = request.form.get('date')
            datetime.strptime(date_str, '%Y-%m-%d')
            
            expense_category = request.form.get('expense_category', 'NIL')  # "company", "awo", or "personal"
            expense_type_selected = request.form.get('expense_type', 'NIL')
            amount = float(request.form.get('amount_paid', 0))
            bank_or_cash = request.form.get('payment_method', 'NIL')

            vendor_id = None
            if expense_category == "awo":
                vendor_id = request.form.get('vendor', '')
                if not vendor_id:
                    flash("Vendor is required for Awo expenses.", "danger")
                    return redirect(url_for('expenses_route'))
            
            expense_data = {
                "type": "expense",  # Represents an actual expense transaction
                "date": date_str,
                "expense_category": expense_category,
                "expense_type": expense_type_selected,
                "amount": amount,
                "bank_or_cash": bank_or_cash,
                "vendor_id": vendor_id,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(expense_data)
            
            flash("Expense recorded successfully.", "success")
            return redirect(url_for('expenses_route'))
        except Exception as e:
            flash(f"Error processing expense: {str(e)}", "danger")
            return redirect(url_for('expenses_route'))

    return render_template('expenses.html', vendors=vendors, bank_names=bank_names, user=session["user"])




@app.route('/expense-types/<category>')
@auth_required
def expense_types_by_category(category):
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")
    expense_types = []
    for doc in user_data_collection.where("type", "==", "expense_type").where("category", "==", category).stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        expense_types.append(doc_dict)
    return jsonify(expense_types)



@app.route('/tools', methods=['GET', 'POST'])
@auth_required
def tools_route():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")

    # 1) Fetch standard docs (customers, vendors, products, banks, expense_types)
    customers = []
    for doc in user_data_collection.where("type", "==", "customer").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        customers.append(d)

    vendors = []
    for doc in user_data_collection.where("type", "==", "vendor").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        vendors.append(d)

    products = []
    for doc in user_data_collection.where("type", "==", "product").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        products.append(d)

    bank_names = []
    for doc in user_data_collection.where("type", "==", "bank").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        bank_names.append(d)

    expense_types = []
    for doc in user_data_collection.where("type", "==", "expense_type").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        expense_types.append(d)

    # We'll store transactions in 'all_transactions' if user selects "edit_records"
    all_transactions = []

    if request.method == 'POST':
        current_section = request.form.get('current_section', 'customers')
        action = request.form.get('action')
        entity_type = request.form.get('entity_type')

        # -------------------------------
        # ADD CUSTOMER / VENDOR
        # -------------------------------
        if action == 'add':
            name = request.form.get('name')
            phone_number = request.form.get('phone_number', '')

            if entity_type in ['customer', 'vendor']:
                # Check if entity exists
                existing_entity = user_data_collection.where("type", "==", entity_type)\
                    .where("name", "==", name).get()
                if existing_entity:
                    flash(f"{entity_type.capitalize()} '{name}' already exists.", "danger")
                    return redirect(url_for('tools_route', section=current_section))

                doc_data = {
                    "type": entity_type,
                    "name": name,
                    "phone_number": phone_number,
                    "created_at": datetime.utcnow()
                }
                user_data_collection.add(doc_data)
                flash(f"{entity_type.capitalize()} added successfully.", "success")

        elif action == 'add_bank_name':
            bank_name = request.form.get('bank_name', '').strip()
            if not bank_name:
                flash("Bank name is required.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            existing_bank = user_data_collection.where("type", "==", "bank")\
                .where("name", "==", bank_name).get()
            if existing_bank:
                flash(f"Bank '{bank_name}' already exists.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            doc_data = {
                "type": "bank",
                "name": bank_name,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(doc_data)
            flash(f"Bank '{bank_name}' added successfully.", "success")

        elif action == 'add_expenses_type':
            expense_type = request.form.get('expense_type', '').strip()
            expense_category = request.form.get('expense_category', '').strip()
            if not expense_type or not expense_category:
                flash("Expense type and category are required.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            existing_expense = user_data_collection.where("type", "==", "expense_type")\
                .where("name", "==", expense_type)\
                .where("category", "==", expense_category).get()
            if existing_expense:
                flash(f"Expense '{expense_type}' already exists under category '{expense_category}'.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            doc_data = {
                "type": "expense_type",
                "name": expense_type,
                "category": expense_category,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(doc_data)
            flash(f"Expense '{expense_type}' added successfully under category '{expense_category}'.", "success")

        elif action == 'add_product':
            product_name = request.form.get('product_name', '').strip()
            price1 = request.form.get('price1', '').strip()
            price2 = request.form.get('price2', '').strip()

            if not product_name or not price1 or not price2:
                flash("All product fields are required.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            try:
                price1 = float(price1)
                price2 = float(price2)
            except ValueError:
                flash("Price fields must be valid numbers.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            existing_product = user_data_collection.where("type", "==", "product")\
                .where("name", "==", product_name).get()
            if existing_product:
                flash(f"Product '{product_name}' already exists.", "danger")
                return redirect(url_for('tools_route', section=current_section))

            doc_data = {
                "type": "product",
                "name": product_name,
                "price1": price1,
                "price2": price2,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(doc_data)
            flash(f"Product '{product_name}' added successfully.", "success")

        # -------------------------------
        # DELETE operations
        # -------------------------------
        elif action == 'delete':
            doc_id = request.form.get('id')
            user_data_collection.document(doc_id).delete()
            flash(f"{entity_type.capitalize()} deleted successfully.", "danger")

        elif action == 'delete_product':
            doc_id = request.form.get('id')
            user_data_collection.document(doc_id).delete()
            flash("Product deleted successfully.", "danger")

        elif action == 'delete_expenses_type':
            doc_id = request.form.get('id')
            user_data_collection.document(doc_id).delete()
            flash("Expense type deleted successfully.", "danger")

        elif action == 'delete_bank_name':
            doc_id = request.form.get('id')
            user_data_collection.document(doc_id).delete()
            flash("Bank name deleted successfully.", "danger")

        # -------------------------------
        # EDIT TRANSACTION
        # -------------------------------
        elif action == 'edit_record':
            doc_id = request.form.get('id')
            record_ref = user_data_collection.document(doc_id)
            record_snap = record_ref.get()
            if not record_snap.exists:
                flash("Record not found for editing.", "danger")
                return redirect(url_for('tools_route', section='edit_records'))

            record_data = record_snap.to_dict()
            # Here you could show a form or do an update:
            flash(f"Editing record {doc_id} (type: {record_data.get('type')}). Implement your logic.", "info")

            return redirect(url_for('tools_route', section='edit_records'))

        else:
            flash("Invalid action.", "danger")

        return redirect(url_for('tools_route', section=current_section))

    # --------------------------------------
    # Handle GET or after POST (redirection)
    # --------------------------------------
    current_section = request.args.get('section', 'customers')

    # If "edit_records", possibly filter by type
    if current_section == "edit_records":
        filter_type = request.args.get('filter_type', 'all')
        if filter_type == 'all':
            tx_query = user_data_collection.where("type", "in", ["sale", "deposit", "production", "stock", "expense"])
        else:
            tx_query = user_data_collection.where("type", "==", filter_type)

        for doc in tx_query.stream():
            tx_dict = doc.to_dict()
            tx_dict["id"] = doc.id
            all_transactions.append(tx_dict)

    return render_template(
        'tools.html',
        customers=customers,
        vendors=vendors,
        products=products,
        bank_names=bank_names,
        expense_types=expense_types,
        all_transactions=all_transactions,
        current_section=current_section,
        user=session["user"]
    )






@app.route('/stock', methods=['GET', 'POST'])
@auth_required
def stock():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")

    # Fetch vendors to populate the dropdown
    vendors = []
    for doc in user_data_collection.where("type", "==", "vendor").stream():
        vendor = doc.to_dict()
        vendor["id"] = doc.id
        vendors.append(vendor)

    if request.method == "POST":
        try:
            # Get and validate inputs
            date_str = request.form.get("date")
            datetime.strptime(date_str, '%Y-%m-%d')  # Ensure valid date format

            vendor_id = request.form.get("vendor")
            quantity = float(request.form.get("quantity"))
            total_price = float(request.form.get("total_price"))
            amount_paid = float(request.form.get("amount_paid", 0))
            
            # Calculate stock rate (ensure quantity is not zero)
            rate = total_price / quantity if quantity != 0 else 0

            # Build the stock record document
            stock_data = {
                "type": "stock",
                "date": date_str,
                "vendor_id": vendor_id,
                "quantity": quantity,
                "total_price": total_price,
                "amount_paid": amount_paid,
                "rate": rate,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(stock_data)
            flash("Stock record saved successfully.", "success")
            return redirect(url_for("stock"))
        except Exception as e:
            flash(f"Error saving stock: {str(e)}", "danger")
            return redirect(url_for("stock"))

    return render_template("stock.html", vendors=vendors, user=session["user"])


@app.route('/vendor-stock/<vendor_id>')
@auth_required
def vendor_stock(vendor_id):
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")
    # Sum stock quantities for this vendor from stock records
    total_stock = 0
    for doc in user_data_collection.where("type", "==", "stock").where("vendor_id", "==", vendor_id).stream():
        data = doc.to_dict()
        total_stock += float(data.get("quantity", 0))
    # Sum production (i.e. processed) for this vendor
    total_produced = 0
    for doc in user_data_collection.where("type", "==", "production").where("vendor_id", "==", vendor_id).stream():
        data = doc.to_dict()
        total_produced += float(data.get("processed", 0))
    current_stock = total_stock - total_produced
    return jsonify({"current_stock": current_stock})


@app.route('/production', methods=['GET', 'POST'])
@auth_required
def production():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")

    # Fetch vendors to populate the dropdown
    vendors = []
    for doc in user_data_collection.where("type", "==", "vendor").stream():
        vendor = doc.to_dict()
        vendor["id"] = doc.id
        vendors.append(vendor)
    
    if request.method == "POST":
        try:
            date_str = request.form.get("date")
            datetime.strptime(date_str, '%Y-%m-%d')  # Validate date format
            
            vendor_id = request.form.get("vendor")
            current_stock = float(request.form.get("current_stock", 0))
            processed = float(request.form.get("processed", 0))
            remaining = current_stock - processed

            production_data = {
                "type": "production",
                "date": date_str,
                "vendor_id": vendor_id,
                "current_stock": current_stock,
                "processed": processed,
                "remaining": remaining,
                "created_at": datetime.utcnow()
            }
            user_data_collection.add(production_data)
            flash("Production record saved successfully.", "success")
            return redirect(url_for("production"))
        except Exception as e:
            flash(f"Error saving production record: {str(e)}", "danger")
            return redirect(url_for("production"))
    
    return render_template("production.html", vendors=vendors, user=session["user"])

@app.route('/reports', methods=['GET'])
@auth_required
def reports():
    user_id = session["user"]["uid"]
    user_data_collection = db.collection(f"user_data_{user_id}")

    report_type = request.args.get('report_type')
    selected_id = request.args.get('selected_id')
    context = {"report_type": report_type}

    if report_type == "customer":
        # Fetch all customers
        customers = []
        for doc in user_data_collection.where("type", "==", "customer").stream():
            d = doc.to_dict()
            d["id"] = doc.id
            customers.append(d)
        context["customers"] = customers

        # If a customer is selected, fetch data
        if selected_id:
            total_sales = 0.0
            total_sales_payments = 0.0  # sum of sale.amount_paid
            sales_records = []
            for doc in user_data_collection.where("type", "==", "sale")\
                                           .where("customer_id", "==", selected_id).stream():
                d = doc.to_dict()
                d["id"] = doc.id
                # Fetch vendor information
                vendor_id = d.get("vendor_id")
                if vendor_id:
                    vendor_doc = user_data_collection.document(vendor_id).get()
                    if vendor_doc.exists:
                        d["vendor"] = vendor_doc.to_dict()
                sales_records.append(d)
                total_sales += float(d.get("total_amount", 0))
                total_sales_payments += float(d.get("amount_paid", 0))

            total_deposits = 0.0
            deposit_records = []
            for doc in user_data_collection.where("type", "==", "deposit")\
                                           .where("customer_id", "==", selected_id).stream():
                d = doc.to_dict()
                d["id"] = doc.id
                deposit_records.append(d)
                total_deposits += float(d.get("amount", 0))

            money_in = total_deposits + total_sales_payments
            money_out = total_sales
            current_balance = money_in - money_out

            daily_net = {}
            for sale in sales_records:
                date_str = sale.get("date", "")
                if date_str not in daily_net:
                    daily_net[date_str] = 0.0
                invoice = float(sale.get("total_amount", 0))
                paid = float(sale.get("amount_paid", 0))
                daily_net[date_str] += (paid - invoice)

            for dep in deposit_records:
                date_str = dep.get("date", "")
                if date_str not in daily_net:
                    daily_net[date_str] = 0.0
                daily_net[date_str] += float(dep.get("amount", 0))

            sorted_dates = sorted(daily_net.keys())
            chart_labels = []
            chart_data = []
            running_balance = 0.0
            for date_str in sorted_dates:
                net_change = daily_net[date_str]
                running_balance += net_change
                chart_labels.append(date_str)
                chart_data.append(round(running_balance, 2))

            context.update({
                "selected_customer": selected_id,
                "sales_records": sales_records,
                "deposit_records": deposit_records,
                "total_sales": total_sales,
                "total_sales_payments": total_sales_payments,
                "total_deposits": total_deposits,
                "current_balance": current_balance,
                "chart_labels": chart_labels,
                "chart_data": chart_data,
            })

    elif report_type == "vendor":
        # Fetch all vendors
        vendors = []
        for doc in user_data_collection.where("type", "==", "vendor").stream():
            d = doc.to_dict()
            d["id"] = doc.id
            vendors.append(d)
        context["vendors"] = vendors

        # If a vendor is selected, fetch data
        if selected_id:
            total_stock_in = 0.0
            stock_records = []
            for doc in user_data_collection.where("type", "==", "stock")\
                                           .where("vendor_id", "==", selected_id).stream():
                s = doc.to_dict()
                s["id"] = doc.id
                stock_records.append(s)
                total_stock_in += float(s.get("quantity", 0))

            total_produced = 0.0
            production_records = []
            for doc in user_data_collection.where("type", "==", "production")\
                                           .where("vendor_id", "==", selected_id).stream():
                p = doc.to_dict()
                p["id"] = doc.id
                production_records.append(p)
                total_produced += float(p.get("processed", 0))

            total_vendor_expenses = 0.0
            vendor_expenses_records = []
            for doc in user_data_collection.where("type", "==", "expense")\
                                           .where("vendor_id", "==", selected_id).stream():
                e = doc.to_dict()
                e["id"] = doc.id
                vendor_expenses_records.append(e)
                total_vendor_expenses += float(e.get("amount", 0))

            total_sales_revenue = 0.0
            sales_records = []
            for doc in user_data_collection.where("type", "==", "sale")\
                                           .where("vendor_id", "==", selected_id).stream():
                sale = doc.to_dict()
                sale["id"] = doc.id
                sales_records.append(sale)
                total_sales_revenue += float(sale.get("total_amount", 0))

            total_stock_cost = 0.0
            for st in stock_records:
                qty = float(st.get("quantity", 0))
                rate = float(st.get("rate", 0))
                total_stock_cost += qty * rate

            average_cost = 0.0
            if total_stock_in > 0:
                average_cost = total_stock_cost / total_stock_in

            cogs = total_produced * average_cost
            profit_or_loss = total_sales_revenue - cogs - total_vendor_expenses

            current_balance = total_stock_in - total_produced

            context.update({
                "selected_vendor": selected_id,
                "stock_records": stock_records,
                "production_records": production_records,
                "vendor_expenses_records": vendor_expenses_records,
                "sales_records": sales_records,
                "total_stock_in": total_stock_in,
                "total_produced": total_produced,
                "total_vendor_expenses": total_vendor_expenses,
                "current_balance": current_balance,
                "total_stock_cost": total_stock_cost,
                "average_cost": average_cost,
                "total_sales_revenue": total_sales_revenue,
                "cogs": cogs,
                "profit_or_loss": profit_or_loss,
            })

    return render_template("reports.html", user=session["user"], **context)
# ----------------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=False)
