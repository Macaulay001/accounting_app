"""
Core Accounting Service
Handles all accounting operations following standard practices
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from ..models.journal_entry import JournalEntry
from ..constants import CHART_OF_ACCOUNTS, AccountType

class AccountingService:
    """Core accounting service for double-entry bookkeeping operations"""
    
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
        self.journal_entry_model = JournalEntry(db, user_id)
    
    def record_purchase(self, 
                       vendor_id: str,
                       date: datetime,
                       raw_materials_cost: float,
                       quantity: float,
                       reference: str,
                       payment_method: str = "accounts_payable") -> str:
        """
        Record purchase of raw materials (cow skins)
        
        Journal Entry:
        DEBIT:  1300 - Raw Materials Inventory
        CREDIT: 2000 - Accounts Payable (or 1000/1100 for cash)
        """
        entries = [
            {
                "account_code": "1300",  # Raw Materials Inventory
                "debit": raw_materials_cost,
                "credit": 0
            }
        ]
        
        # Credit side depends on payment method
        if payment_method == "cash":
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": 0,
                "credit": raw_materials_cost
            })
        elif payment_method == "bank_transfer":
            entries.append({
                "account_code": "1100",  # Bank Accounts
                "debit": 0,
                "credit": raw_materials_cost
            })
        else:  # accounts_payable
            entries.append({
                "account_code": "2000",  # Accounts Payable
                "debit": 0,
                "credit": raw_materials_cost
            })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Purchase of raw materials from vendor {vendor_id}",
            reference=reference,
            entries=entries
        )
    
    def record_purchase_from_batch(self,
                                 batch_id: str,
                                 vendor_id: str,
                                 date: datetime,
                                 raw_materials_cost: float,
                                 quantity: int,
                                 reference: str,
                                 payment_method: str = "accounts_payable") -> str:
        """
        Record purchase journal entry from inventory batch data
        
        This method creates journal entries based on inventory batch data,
        ensuring consistency between inventory tracking and accounting records.
        """
        entries = []
        
        # Raw materials side
        entries.append({
            "account_code": "1300",  # Raw Materials Inventory
            "debit": raw_materials_cost,
            "credit": 0
        })
        
        # Payment side
        if payment_method == "cash":
            entries.append({
                "account_code": "1000",  # Cash
                "debit": 0,
                "credit": raw_materials_cost
            })
        elif payment_method == "bank_transfer":
            entries.append({
                "account_code": "1100",  # Bank
                "debit": 0,
                "credit": raw_materials_cost
            })
        else:  # accounts_payable
            entries.append({
                "account_code": "2000",  # Accounts Payable
                "debit": 0,
                "credit": raw_materials_cost
            })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Purchase of raw materials - Batch {batch_id[:8]}... from vendor {vendor_id}",
            reference=reference,
            entries=entries
        )
    
    def record_production(self,
                         date: datetime,
                         raw_materials_used: float,
                         processing_cost: float,
                         finished_goods_value: float,
                         reference: str) -> str:
        """
        Record production process (raw materials -> finished goods)
        
        Journal Entries:
        1. DEBIT:  5000 - Cost of Goods Sold (raw materials)
        2. DEBIT:  1310 - Work in Process Inventory (processing cost) - only if > 0
        3. CREDIT: 1300 - Raw Materials Inventory
        4. DEBIT:  1320 - Finished Goods Inventory
        5. CREDIT: 1310 - Work in Process Inventory - only if > 0
        """
        # First entry: Move raw materials to production
        entries1 = [
            {
                "account_code": "1310",  # Work in Process Inventory
                "debit": raw_materials_used,
                "credit": 0
            },
            {
                "account_code": "1300",  # Raw Materials Inventory
                "debit": 0,
                "credit": raw_materials_used
            }
        ]
        
        # Add processing cost entry if it's greater than 0
        if processing_cost > 0:
            entries1.append({
                "account_code": "1310",  # Work in Process Inventory
                "debit": processing_cost,
                "credit": 0
            })
            entries1.append({
                "account_code": "5400",  # Processing Materials Expense
                "debit": 0,
                "credit": processing_cost
            })
        
        self.journal_entry_model.create_entry(
            date=date,
            description=f"Transfer raw materials to production - {reference}",
            reference=f"PROD-{reference}",
            entries=entries1
        )
        
        # Second entry: Complete production
        entries2 = [
            {
                "account_code": "1320",  # Finished Goods Inventory
                "debit": finished_goods_value,
                "credit": 0
            },
            {
                "account_code": "1310",  # Work in Process Inventory
                "debit": 0,
                "credit": raw_materials_used + processing_cost  # Total cost
            }
        ]
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Complete production - {reference}",
            reference=f"COMP-{reference}",
            entries=entries2
        )
    
    def record_vendor_payment(self,
                             vendor_id: str,
                             date: datetime,
                             amount: float,
                             payment_method: str = "cash",
                             reference: str = "") -> str:
        """
        Record payment made to vendor
        
        Journal Entries:
        DEBIT:  [Payment Account] (Cash/Bank)
        CREDIT: [Vendor Account] (Accounts Payable)
        """
        entries = []
        
        # Payment side (debit)
        if payment_method == "cash":
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": amount,
                "credit": 0
            })
        elif payment_method == "bank_transfer":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": amount,
                "credit": 0
            })
        elif payment_method == "check":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": amount,
                "credit": 0
            })
        else:
            # Default to cash
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": amount,
                "credit": 0
            })
        
        # Vendor side (credit) - reduce accounts payable
        entries.append({
            "account_code": "2000",  # Accounts Payable
            "debit": 0,
            "credit": amount
        })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Payment to vendor {vendor_id}",
            reference=reference or f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entries=entries
        )
    
    def record_customer_deposit(self,
                               customer_id: str,
                               amount: float,
                               date: datetime,
                               payment_method: str = 'cash',
                               reference: str = None) -> str:
        """
        Record customer deposit/advance payment
        
        Journal Entries:
        1. DEBIT: 1000/1100 - Cash/Bank (payment received)
        2. CREDIT: 2200 - Customer Deposits (liability account)
        """
        entries = []
        
        # Payment side (debit)
        if payment_method == "cash":
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": amount,
                "credit": 0
            })
        elif payment_method == "bank_transfer":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": amount,
                "credit": 0
            })
        elif payment_method == "check":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": amount,
                "credit": 0
            })
        else:
            # Default to cash
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": amount,
                "credit": 0
            })
        
        # Customer deposit side (credit) - liability
        entries.append({
            "account_code": "2200",  # Customer Deposits (liability)
            "debit": 0,
            "credit": amount
        })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Customer deposit from {customer_id}",
            reference=reference or f"DEP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entries=entries
        )
    
    def record_customer_deposit_usage(self,
                                    customer_id: str,
                                    amount: float,
                                    date: datetime,
                                    reference: str = None) -> str:
        """
        Record usage of customer deposit for sales
        
        Journal Entries:
        1. DEBIT: 2200 - Customer Deposits (reduce liability)
        2. CREDIT: 1000/1100 - Cash/Bank (or 1200 for accounts receivable)
        """
        entries = []
        
        # Reduce customer deposit liability (debit)
        entries.append({
            "account_code": "2200",  # Customer Deposits (liability)
            "debit": amount,
            "credit": 0
        })
        
        # Credit Accounts Receivable to offset the customer's AR
        entries.append({
            "account_code": "1200",  # Accounts Receivable
            "debit": 0,
            "credit": amount
        })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Used customer deposit for sale - customer {customer_id}",
            reference=reference or f"DEP-USE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entries=entries
        )
    
    def record_sale(self,
                   customer_id: str,
                   date: datetime,
                   sales_amount: float,
                   cost_of_goods_sold: float,
                   invoice_number: str,
                   payment_received: float = 0) -> str:
        """
        Record sale of finished goods
        
        Journal Entries:
        1. DEBIT:  1200 - Accounts Receivable (or 1000/1100 for cash)
        2. CREDIT: 4000 - Sales Revenue
        3. DEBIT:  5000 - Cost of Goods Sold
        4. CREDIT: 1320 - Finished Goods Inventory
        """
        entries = []
        
        # Revenue side
        if payment_received >= sales_amount:
            # Full payment received (may include overpayment)
            entries.append({
                "account_code": "1000",  # Cash on Hand (or 1100 for bank)
                "debit": payment_received,
                "credit": 0
            })
            overpayment = payment_received - sales_amount
            if overpayment > 0:
                # Record overpayment as customer deposit liability
                entries.append({
                    "account_code": "2200",  # Customer Deposits (liability)
                    "debit": 0,
                    "credit": overpayment
                })
        else:
            # Partial payment or credit sale
            if payment_received > 0:
                entries.append({
                    "account_code": "1000",  # Cash on Hand
                    "debit": payment_received,
                    "credit": 0
                })
                entries.append({
                    "account_code": "1200",  # Accounts Receivable
                    "debit": sales_amount - payment_received,
                    "credit": 0
                })
            else:
                entries.append({
                    "account_code": "1200",  # Accounts Receivable
                    "debit": sales_amount,
                    "credit": 0
                })
        
        entries.append({
            "account_code": "4000",  # Sales Revenue
            "debit": 0,
            "credit": sales_amount
        })
        
        # COGS side - only create entries if there's actual cost
        if cost_of_goods_sold > 0:
            entries.append({
                "account_code": "5000",  # Cost of Goods Sold
                "debit": cost_of_goods_sold,
                "credit": 0
            })
            entries.append({
                "account_code": "1320",  # Finished Goods Inventory
                "debit": 0,
                "credit": cost_of_goods_sold
            })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Sale to customer {customer_id} - Invoice {invoice_number}",
            reference=invoice_number,
            entries=entries
        )
    
    
    def record_payment_received(self,
                               customer_id: str,
                               date: datetime,
                               amount: float,
                               reference: str,
                               payment_method: str = "cash") -> str:
        """
        Record payment received from customer
        
        Journal Entry:
        DEBIT:  [Cash/Bank Account]
        CREDIT: 1200 - Accounts Receivable
        """
        entries = [
            {
                "account_code": "1000" if payment_method == "cash" else "1100",
                "debit": amount,
                "credit": 0
            },
            {
                "account_code": "1200",  # Accounts Receivable
                "debit": 0,
                "credit": amount
            }
        ]
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=f"Payment received from customer {customer_id}",
            reference=reference,
            entries=entries
        )
    
    def get_account_balance(self, account_code: str, as_of_date: Optional[datetime] = None) -> float:
        """Get account balance as of specific date"""
        return self.journal_entry_model.get_account_balance(account_code, as_of_date)
    
    def get_trial_balance(self, as_of_date: Optional[datetime] = None) -> Dict[str, float]:
        """Get trial balance for all accounts"""
        return self.journal_entry_model.get_trial_balance(as_of_date)
    
    def generate_profit_loss_statement(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate Profit & Loss Statement for the period"""
        # For now, return a simplified version to avoid Firebase index issues
        # TODO: Implement proper date-range filtering once Firebase indexes are set up
        
        # Get current balances (simplified approach)
        revenue = self.get_account_balance("4000")
        cogs = self.get_account_balance("5000")
        operating_expenses = (
            self.get_account_balance("5400") +
            self.get_account_balance("5500") +
            self.get_account_balance("5600")
        )
        
        gross_profit = revenue - cogs
        net_profit = gross_profit - operating_expenses
        
        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "revenue": revenue,
            "cost_of_goods_sold": cogs,
            "gross_profit": gross_profit,
            "operating_expenses": operating_expenses,
            "net_profit": net_profit
        }
    
    def generate_balance_sheet(self, as_of_date: datetime) -> Dict[str, Any]:
        """Generate Balance Sheet as of specific date"""
        # For now, use current balances to avoid Firebase index issues
        # TODO: Implement proper date filtering once Firebase indexes are set up
        
        # Assets
        cash = self.get_account_balance("1000")
        bank = self.get_account_balance("1100")
        receivables = self.get_account_balance("1200")
        raw_materials = self.get_account_balance("1300")
        work_in_process = self.get_account_balance("1310")
        finished_goods = self.get_account_balance("1320")
        equipment = self.get_account_balance("1400")
        accumulated_depreciation = self.get_account_balance("1500")
        
        current_assets = cash + bank + receivables + raw_materials + work_in_process + finished_goods
        fixed_assets = equipment - accumulated_depreciation
        total_assets = current_assets + fixed_assets
        
        # Liabilities
        payables = self.get_account_balance("2000")
        accrued_expenses = self.get_account_balance("2100")
        short_term_loans = self.get_account_balance("2200")
        
        current_liabilities = payables + accrued_expenses + short_term_loans
        total_liabilities = current_liabilities
        
        # Equity
        owners_capital = self.get_account_balance("3000")
        retained_earnings = self.get_account_balance("3100")
        current_year_profit = self.get_account_balance("3200")
        
        total_equity = owners_capital + retained_earnings + current_year_profit
        
        return {
            "as_of_date": as_of_date.strftime('%Y-%m-%d'),
            "assets": {
                "current_assets": current_assets,
                "fixed_assets": fixed_assets,
                "total_assets": total_assets
            },
            "liabilities": {
                "current_liabilities": current_liabilities,
                "total_liabilities": total_liabilities
            },
            "equity": {
                "owners_capital": owners_capital,
                "retained_earnings": retained_earnings,
                "current_year_profit": current_year_profit,
                "total_equity": total_equity
            }
        }

    def record_expense(self, 
                      date: datetime,
                      account_code: str,
                      amount: float,
                      description: str,
                      payment_method: str = "cash",
                      reference: str = "") -> str:
        """
        Record an expense transaction
        
        Args:
            date: Date of the expense
            account_code: Expense account code (e.g., 5400 for utilities)
            amount: Amount of the expense
            description: Description of the expense
            payment_method: How the expense was paid (cash, bank_transfer, etc.)
            reference: Reference number or invoice number
        """
        entries = []
        
        # Expense side (debit)
        entries.append({
            "account_code": account_code,
            "debit": amount,
            "credit": 0
        })
        
        # Payment side (credit)
        if payment_method == "cash":
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": 0,
                "credit": amount
            })
        elif payment_method == "bank_transfer":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": 0,
                "credit": amount
            })
        elif payment_method == "check":
            entries.append({
                "account_code": "1100",  # Bank Account
                "debit": 0,
                "credit": amount
            })
        elif payment_method == "credit_card":
            entries.append({
                "account_code": "2000",  # Accounts Payable (for credit card)
                "debit": 0,
                "credit": amount
            })
        else:
            # Default to cash
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": 0,
                "credit": amount
            })
        
        return self.journal_entry_model.create_entry(
            date=date,
            description=description,
            reference=reference,
            entries=entries
        )
