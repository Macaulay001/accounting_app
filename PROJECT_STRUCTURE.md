# Ponmo Business Manager - Proper Project Structure

## 📁 Recommended Project Structure

```
accounting_app/
├── app.py                          # Main Flask application (minimal)
├── config.py                       # Configuration management
├── requirements.txt                # Dependencies
├── .env.example                    # Environment variables template
├── README.md                       # Project documentation
├── 
├── src/                           # Main application code
│   ├── __init__.py
│   ├── models/                    # Database models
│   │   ├── __init__.py
│   │   ├── base.py               # Base model class
│   │   ├── user.py               # User model
│   │   ├── chart_of_accounts.py  # Chart of accounts
│   │   ├── journal_entry.py      # Journal entries
│   │   ├── transaction.py        # Individual transactions
│   │   ├── customer.py           # Customer model
│   │   ├── vendor.py             # Vendor model
│   │   └── product.py            # Product model
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── accounting_service.py  # Core accounting logic
│   │   ├── inventory_service.py   # Inventory management
│   │   ├── sales_service.py       # Sales processing
│   │   ├── reporting_service.py   # Financial reporting
│   │   └── auth_service.py        # Authentication logic
│   │
│   ├── controllers/               # Request handling
│   │   ├── __init__.py
│   │   ├── auth_controller.py     # Authentication routes
│   │   ├── sales_controller.py    # Sales routes
│   │   ├── inventory_controller.py # Inventory routes
│   │   ├── reporting_controller.py # Reporting routes
│   │   └── dashboard_controller.py # Dashboard routes
│   │
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   ├── validators.py          # Input validation
│   │   ├── formatters.py          # Data formatting
│   │   ├── calculations.py        # Financial calculations
│   │   └── firebase_client.py     # Firebase wrapper
│   │
│   └── constants/                 # Application constants
│       ├── __init__.py
│       ├── chart_of_accounts.py   # Standard chart of accounts
│       ├── account_types.py       # Account type definitions
│       └── business_rules.py      # Business rule constants
│
├── templates/                     # HTML templates (existing)
├── static/                       # Static assets (existing)
├── tests/                        # Test files
│   ├── __init__.py
│   ├── test_models/
│   ├── test_services/
│   └── test_controllers/
│
└── migrations/                   # Database migrations (if needed)
    └── __init__.py
```

## 🧮 Standard Chart of Accounts for Ponmo Business

### ASSETS (1000-1999)
- 1000 - Cash on Hand
- 1100 - Bank Accounts
- 1200 - Accounts Receivable
- 1300 - Raw Materials Inventory (Cow Skins)
- 1310 - Work in Process Inventory
- 1320 - Finished Goods Inventory (Processed Ponmo)
- 1400 - Equipment
- 1500 - Accumulated Depreciation - Equipment

### LIABILITIES (2000-2999)
- 2000 - Accounts Payable
- 2100 - Accrued Expenses
- 2200 - Short-term Loans

### EQUITY (3000-3999)
- 3000 - Owner's Capital
- 3100 - Retained Earnings
- 3200 - Current Year Profit/Loss

### REVENUE (4000-4999)
- 4000 - Sales Revenue
- 4100 - Service Revenue

### EXPENSES (5000-5999)
- 5000 - Cost of Goods Sold
- 5100 - Raw Materials Purchased
- 5200 - Direct Labor
- 5300 - Manufacturing Overhead
- 5400 - Operating Expenses
- 5500 - Administrative Expenses
- 5600 - Selling Expenses

## 🔄 Double-Entry Bookkeeping Examples

### Purchase Raw Materials (Cow Skins)
```
DEBIT:  1300 - Raw Materials Inventory    $1,000
CREDIT: 2000 - Accounts Payable           $1,000
```

### Process Raw Materials
```
DEBIT:  5000 - Cost of Goods Sold         $800
DEBIT:  1310 - Work in Process Inventory  $200
CREDIT: 1300 - Raw Materials Inventory    $1,000
```

### Complete Production
```
DEBIT:  1320 - Finished Goods Inventory   $1,200
CREDIT: 1310 - Work in Process Inventory  $1,200
```

### Record Sale
```
DEBIT:  1200 - Accounts Receivable        $1,500
CREDIT: 4000 - Sales Revenue              $1,500

DEBIT:  5000 - Cost of Goods Sold         $1,200
CREDIT: 1320 - Finished Goods Inventory   $1,200
```

### Receive Payment
```
DEBIT:  1000 - Cash on Hand               $1,500
CREDIT: 1200 - Accounts Receivable        $1,500
```

## 📊 Standard Financial Statements

### 1. Profit & Loss Statement
- Revenue
- Cost of Goods Sold
- Gross Profit
- Operating Expenses
- Net Profit

### 2. Balance Sheet
- Assets (Current & Fixed)
- Liabilities (Current & Long-term)
- Equity

### 3. Cash Flow Statement
- Operating Activities
- Investing Activities
- Financing Activities

## 🎯 Benefits of This Structure

1. **Standard Accounting**: Follows GAAP principles
2. **Clean Architecture**: Separation of concerns
3. **Maintainable**: Easy to modify and extend
4. **Testable**: Each component can be tested independently
5. **Scalable**: Can handle multiple businesses
6. **Professional**: Industry-standard practices
7. **Auditable**: Complete transaction trails
8. **Compliant**: Meets accounting standards
