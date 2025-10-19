"""
Standard Chart of Accounts for Ponmo Business
Following GAAP (Generally Accepted Accounting Principles)
"""

from enum import Enum
from typing import Dict, List, Tuple

class AccountType(Enum):
    """Standard account types in accounting"""
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

class AccountCategory(Enum):
    """Account categories for better organization"""
    CURRENT_ASSET = "CURRENT_ASSET"
    FIXED_ASSET = "FIXED_ASSET"
    CURRENT_LIABILITY = "CURRENT_LIABILITY"
    LONG_TERM_LIABILITY = "LONG_TERM_LIABILITY"
    OWNER_EQUITY = "OWNER_EQUITY"
    OPERATING_REVENUE = "OPERATING_REVENUE"
    COST_OF_GOODS_SOLD = "COST_OF_GOODS_SOLD"
    OPERATING_EXPENSE = "OPERATING_EXPENSE"

# Standard Chart of Accounts for Ponmo Business
CHART_OF_ACCOUNTS = {
    # ASSETS (1000-1999)
    "1000": {
        "name": "Cash on Hand",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "Physical cash available"
    },
    "1100": {
        "name": "Bank Accounts",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "All bank account balances"
    },
    "1200": {
        "name": "Accounts Receivable",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "Money owed by customers"
    },
    "1300": {
        "name": "Raw Materials Inventory",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "Raw cow skins inventory"
    },
    "1310": {
        "name": "Work in Process Inventory",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "Partially processed cow skins"
    },
    "1320": {
        "name": "Finished Goods Inventory",
        "type": AccountType.ASSET,
        "category": AccountCategory.CURRENT_ASSET,
        "description": "Processed ponmo ready for sale"
    },
    "1400": {
        "name": "Equipment",
        "type": AccountType.ASSET,
        "category": AccountCategory.FIXED_ASSET,
        "description": "Processing equipment and machinery"
    },
    "1500": {
        "name": "Accumulated Depreciation - Equipment",
        "type": AccountType.ASSET,
        "category": AccountCategory.FIXED_ASSET,
        "description": "Depreciation accumulated on equipment (contra-asset)"
    },
    
    # LIABILITIES (2000-2999)
    "2000": {
        "name": "Accounts Payable",
        "type": AccountType.LIABILITY,
        "category": AccountCategory.CURRENT_LIABILITY,
        "description": "Money owed to vendors"
    },
    "2100": {
        "name": "Accrued Expenses",
        "type": AccountType.LIABILITY,
        "category": AccountCategory.CURRENT_LIABILITY,
        "description": "Expenses incurred but not yet paid"
    },
    "2200": {
        "name": "Customer Deposits",
        "type": AccountType.LIABILITY,
        "category": AccountCategory.CURRENT_LIABILITY,
        "description": "Advance payments received from customers"
    },
    
    # EQUITY (3000-3999)
    "3000": {
        "name": "Owner's Capital",
        "type": AccountType.EQUITY,
        "category": AccountCategory.OWNER_EQUITY,
        "description": "Owner's initial investment"
    },
    "3100": {
        "name": "Retained Earnings",
        "type": AccountType.EQUITY,
        "category": AccountCategory.OWNER_EQUITY,
        "description": "Accumulated profits from previous periods"
    },
    "3200": {
        "name": "Current Year Profit/Loss",
        "type": AccountType.EQUITY,
        "category": AccountCategory.OWNER_EQUITY,
        "description": "Current year's net profit or loss"
    },
    
    # REVENUE (4000-4999)
    "4000": {
        "name": "Sales Revenue",
        "type": AccountType.REVENUE,
        "category": AccountCategory.OPERATING_REVENUE,
        "description": "Revenue from ponmo sales"
    },
    "4100": {
        "name": "Service Revenue",
        "type": AccountType.REVENUE,
        "category": AccountCategory.OPERATING_REVENUE,
        "description": "Revenue from processing services"
    },
    
    # EXPENSES (5000-5999)
    "5000": {
        "name": "Cost of Goods Sold",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.COST_OF_GOODS_SOLD,
        "description": "Direct costs of producing ponmo"
    },
    "5100": {
        "name": "Raw Materials Purchased",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.COST_OF_GOODS_SOLD,
        "description": "Cost of raw cow skins purchased"
    },
    "5200": {
        "name": "Direct Labor",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.COST_OF_GOODS_SOLD,
        "description": "Labor costs for processing"
    },
    "5300": {
        "name": "Manufacturing Overhead",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.COST_OF_GOODS_SOLD,
        "description": "Indirect manufacturing costs"
    },
    "5400": {
        "name": "Operating Expenses",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.OPERATING_EXPENSE,
        "description": "General operating expenses"
    },
    "5500": {
        "name": "Administrative Expenses",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.OPERATING_EXPENSE,
        "description": "Administrative and office expenses"
    },
    "5600": {
        "name": "Selling Expenses",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.OPERATING_EXPENSE,
        "description": "Marketing and selling expenses"
    },
    "5700": {
        "name": "Financing Expenses",
        "type": AccountType.EXPENSE,
        "category": AccountCategory.OPERATING_EXPENSE,
        "description": "Interest on loans, bank charges, and other financing costs"
    }
}

def get_accounts_by_type(account_type: AccountType) -> List[Tuple[str, Dict]]:
    """Get all accounts of a specific type"""
    return [(code, details) for code, details in CHART_OF_ACCOUNTS.items() 
            if details["type"] == account_type]

def get_accounts_by_category(category: AccountCategory) -> List[Tuple[str, Dict]]:
    """Get all accounts of a specific category"""
    return [(code, details) for code, details in CHART_OF_ACCOUNTS.items() 
            if details["category"] == category]

def get_account_info(account_code: str) -> Dict:
    """Get information for a specific account code"""
    return CHART_OF_ACCOUNTS.get(account_code, {})

def is_debit_account(account_type: AccountType) -> bool:
    """Determine if account type increases with debits"""
    return account_type in [AccountType.ASSET, AccountType.EXPENSE]

def is_credit_account(account_type: AccountType) -> bool:
    """Determine if account type increases with credits"""
    return account_type in [AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE]
