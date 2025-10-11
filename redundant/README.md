# Redundant Files

This folder contains old or redundant files that are no longer being used in the current application.

## Moved Files

### Templates (Old/Unused)
- `dashboard.html` - Replaced by `dashboard_accounting.html`
- `deposit.html` - Replaced by `customer_deposits.html`
- `sales.html` - Replaced by `sales_accounting.html`
- `reports.html` - Replaced by `reports_accounting.html`
- `stock.html` - Replaced by `inventory_batches.html`
- `tools.html` - No longer used
- `navbar_private.html` - Replaced by `layout_accounting.html`
- `navbar_public.html` - Replaced by `layout_accounting.html`
- `footer.html` - Integrated into `layout_accounting.html`

### Static Files (Old/Unused)
- `static/css/home_css.css` - Replaced by `accounting-dashboard.css`
- `static/css/style.css` - Replaced by `accounting-dashboard.css`
- `static/js/index.js` - No longer used
- `static/js/script.js` - No longer used
- `static/js/scripts.js` - No longer used

### Configuration Files (Old/Unused)
- `firebase _config.py` - Replaced by proper Firebase configuration
- `config.py` - No longer used
- `co.sh` - Old script, no longer needed
- `compiled.txt` - Old compilation output
- `templates.zip` - Old backup file

### Deployment Scripts (Old/Unused)
- `deploy-railway.sh` - Replaced by newer deployment methods

## Current Active Files

The following files are currently being used and should NOT be moved:

### Templates
- `dashboard_accounting.html` - Main dashboard
- `sales_accounting.html` - Sales management
- `reports_accounting.html` - Business reports
- `inventory_batches.html` - Inventory management
- `customer_deposits.html` - Customer deposits
- `expenses.html` - Expense management
- `expense_types.html` - Expense type management
- `production.html` - Production tracking
- `vendor_payments.html` - Vendor payment management
- `customers.html` - Customer management
- `vendors.html` - Vendor management
- `products.html` - Product management
- `layout_accounting.html` - Main layout template
- `layout.html` - Public layout template
- `home.html` - Landing page
- `login.html` - Login page
- `signup.html` - Signup page
- `setup_business.html` - Business setup
- `onboarding_tour.html` - Onboarding tour
- `edit_*.html` - Edit forms
- `batch_details.html` - Batch details
- `financial_statements/` - Financial statement templates
- `reports/` - Report templates

### Static Files
- `static/css/accounting-dashboard.css` - Main CSS file
- `static/js/firebase-config.js` - Firebase configuration
- `static/images/` - All image files

### Configuration
- `app.py` - Main application file
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration
- `deploy.sh` - Main deployment script
- `deploy-k8s.sh` - Kubernetes deployment
- `k8s/` - Kubernetes manifests
- `src/` - Source code modules
- `templates/` - Active templates
- `static/` - Active static files

## Notes

- These files were moved on: $(date)
- Files can be restored if needed by moving them back to their original locations
- Some files may contain useful code snippets that could be referenced for future development
- The application should continue to work normally without these files
