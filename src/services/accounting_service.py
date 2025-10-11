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
        DEBIT:  [Vendor Account] (Accounts Payable) - reduce what we owe
        CREDIT: [Payment Account] (Cash/Bank) - reduce cash/bank
        """
        entries = []
        
        # Payment side (credit) - reduce cash/bank
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
        else:
            # Default to cash
            entries.append({
                "account_code": "1000",  # Cash on Hand
                "debit": 0,
                "credit": amount
            })
        
        # Vendor side (debit) - reduce accounts payable
        entries.append({
            "account_code": "2000",  # Accounts Payable
            "debit": amount,
            "credit": 0
        })
        
        journal_entry_id = self.journal_entry_model.create_entry(
            date=date,
            description=f"Payment to vendor {vendor_id}",
            reference=reference or f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entries=entries
        )
        
        # DEBUG: Print the created journal entry ID
        print(f"Created Vendor Payment Journal Entry ID: {journal_entry_id}")
        
        return journal_entry_id
    
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
                   payment_received: float = 0,
                   payment_method: str = "cash",
                   batch_id: str = None,
                   ile_number: int = None) -> str:
        """
        Record sale of finished goods
        
        Journal Entries:
        1. DEBIT:  1200 - Accounts Receivable (or 1000/1100 for cash)
        2. CREDIT: 4000 - Sales Revenue
        3. DEBIT:  5000 - Cost of Goods Sold
        4. CREDIT: 1320 - Finished Goods Inventory
        """
        entries = []
        
        # Revenue side - determine which account to debit based on payment method
        if payment_received >= sales_amount:
            # Full payment received (may include overpayment)
            if payment_method == "cash":
                entries.append({
                    "account_code": "1000",  # Cash on Hand
                    "debit": payment_received,
                    "credit": 0
                })
            elif payment_method == "bank_transfer":
                entries.append({
                    "account_code": "1100",  # Bank Account
                    "debit": payment_received,
                    "credit": 0
                })
            elif payment_method == "credit":
                entries.append({
                    "account_code": "1200",  # Accounts Receivable
                    "debit": payment_received,
                    "credit": 0
                })
            else:
                # Default to cash
                entries.append({
                    "account_code": "1000",  # Cash on Hand
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
                # Record the payment received
                if payment_method == "cash":
                    entries.append({
                        "account_code": "1000",  # Cash on Hand
                        "debit": payment_received,
                        "credit": 0
                    })
                elif payment_method == "bank_transfer":
                    entries.append({
                        "account_code": "1100",  # Bank Account
                        "debit": payment_received,
                        "credit": 0
                    })
                elif payment_method == "credit":
                    entries.append({
                        "account_code": "1200",  # Accounts Receivable
                        "debit": payment_received,
                        "credit": 0
                    })
                else:
                    # Default to cash
                    entries.append({
                        "account_code": "1000",  # Cash on Hand
                        "debit": payment_received,
                        "credit": 0
                    })
                
                # Record the remaining amount as receivable
                entries.append({
                    "account_code": "1200",  # Accounts Receivable
                    "debit": sales_amount - payment_received,
                    "credit": 0
                })
            else:
                # Credit sale - all goes to receivables
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
        
        journal_entry_id = self.journal_entry_model.create_entry(
            date=date,
            description=f"Sale to customer {customer_id} - Invoice {invoice_number}",
            reference=invoice_number,
            entries=entries,
            batch_id=batch_id,
            ile_number=ile_number
        )
        
        # DEBUG: Print the created journal entry ID
        print(f"Created Journal Entry ID: {journal_entry_id}")
        
        return journal_entry_id
    
    
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
        
    def generate_profit_loss_by_vendor(self, start_date: datetime = None, end_date: datetime = None, from_batch_id: str = None) -> Dict[str, Any]:
        """Generate Profit & Loss analysis by vendor"""
        from ..models.inventory_batch import InventoryBatch
        from ..models.vendor_payment import VendorPayment
        
        inventory_model = InventoryBatch(self.db, self.user_id)
        vendor_payment_model = VendorPayment(self.db, self.user_id)
        
        # Get all batches
        all_batches = inventory_model.get_all()
        
        # Filter batches if from_batch_id is specified
        if from_batch_id:
            # Find the reference batch
            reference_batch = None
            for batch in all_batches:
                if batch.get('id') == from_batch_id:
                    reference_batch = batch
                    break
            
            if reference_batch:
                # Filter batches created on or after the reference batch's creation date
                reference_date = reference_batch.get('created_at') or reference_batch.get('purchase_date')
                if reference_date:
                    all_batches = [batch for batch in all_batches 
                                 if (batch.get('created_at') or batch.get('purchase_date')) >= reference_date]
        
        vendor_analysis = {}
        
        for batch in all_batches:
            vendor_id = batch.get('vendor_id')
            vendor_name = batch.get('vendor_name', 'Unknown')
            
            if vendor_id not in vendor_analysis:
                vendor_analysis[vendor_id] = {
                    'vendor_name': vendor_name,
                    'total_purchase_cost': 0,
                    'total_processing_cost': 0,
                    'total_sales_revenue': 0,
                    'total_pieces_sold': 0,
                    'total_pieces_purchased': 0,
                    'batches': [],
                    'profit_loss': 0,
                    'profit_margin': 0
                }
            
            # Calculate costs and revenue for this batch
            batch_analysis = self._analyze_batch_profitability(batch, start_date, end_date)
            
            vendor_analysis[vendor_id]['total_purchase_cost'] += batch_analysis['purchase_cost']
            vendor_analysis[vendor_id]['total_processing_cost'] += batch_analysis['processing_cost']
            vendor_analysis[vendor_id]['total_sales_revenue'] += batch_analysis['sales_revenue']
            vendor_analysis[vendor_id]['total_pieces_sold'] += batch_analysis['pieces_sold']
            vendor_analysis[vendor_id]['total_pieces_purchased'] += batch_analysis['pieces_purchased']
            vendor_analysis[vendor_id]['batches'].append(batch_analysis)
        
        # Calculate totals and margins
        for vendor_id, data in vendor_analysis.items():
            total_costs = data['total_purchase_cost'] + data['total_processing_cost']
            data['profit_loss'] = data['total_sales_revenue'] - total_costs
            data['profit_margin'] = (data['profit_loss'] / data['total_sales_revenue'] * 100) if data['total_sales_revenue'] > 0 else 0
            
            # Sort batches by purchase date (most recent first)
            data['batches'].sort(key=lambda x: x.get('purchase_date', datetime.min), reverse=True)
        
        return vendor_analysis
    
    def generate_profit_loss_by_batch(self, batch_id: str) -> Dict[str, Any]:
        """Generate detailed Profit & Loss analysis for a specific batch"""
        from ..models.inventory_batch import InventoryBatch
        
        inventory_model = InventoryBatch(self.db, self.user_id)
        batch = inventory_model.get_by_id(batch_id)
        
        if not batch:
            return {'error': 'Batch not found'}
        
        return self._analyze_batch_profitability(batch)
    
    def generate_profit_loss_by_ile_pack(self, batch_id: str, ile_number: int) -> Dict[str, Any]:
        """Generate Profit & Loss analysis for a specific ILE pack within a batch"""
        from ..models.inventory_batch import InventoryBatch
        
        inventory_model = InventoryBatch(self.db, self.user_id)
        batch = inventory_model.get_by_id(batch_id)
        
        if not batch:
            return {'error': 'Batch not found'}
        
        # Find the specific ILE group
        ile_group = None
        for group in batch.get('ile_groups', []):
            if group.get('ile_number') == ile_number:
                ile_group = group
                break
        
        if not ile_group:
            return {'error': 'ILE group not found'}
        
        return self._analyze_ile_group_profitability(batch, ile_group)
    
    def _analyze_batch_profitability(self, batch: Dict[str, Any], start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Analyze profitability for a specific batch"""
        batch_id = batch.get('id')
        vendor_name = batch.get('vendor_name', 'Unknown')
        purchase_cost = batch.get('purchase_cost', 0)
        total_pieces = batch.get('total_pieces', 0)
        
        # Calculate processing costs from production records and get ILE group details
        total_processing_cost = 0
        total_pieces_sold = 0
        total_sales_revenue = 0
        ile_groups_analysis = []
        
        for ile_group in batch.get('ile_groups', []):
            ile_analysis = self._analyze_ile_group_profitability(batch, ile_group, start_date, end_date)
            total_processing_cost += ile_analysis['processing_cost']
            total_pieces_sold += ile_analysis['pieces_sold']
            total_sales_revenue += ile_analysis['sales_revenue']
            
            # Add ILE group details for drill-down
            ile_groups_analysis.append(ile_analysis)
        
        # Sort ILE groups by ILE number (most recent first)
        ile_groups_analysis.sort(key=lambda x: x.get('ile_number', 0), reverse=True)
        
        total_costs = purchase_cost + total_processing_cost
        profit_loss = total_sales_revenue - total_costs
        profit_margin = (profit_loss / total_sales_revenue * 100) if total_sales_revenue > 0 else 0
        
        return {
            'batch_id': batch_id,
            'vendor_name': vendor_name,
            'purchase_cost': purchase_cost,
            'processing_cost': total_processing_cost,
            'total_costs': total_costs,
            'sales_revenue': total_sales_revenue,
            'pieces_purchased': total_pieces,
            'pieces_sold': total_pieces_sold,
            'profit_loss': profit_loss,
            'profit_margin': profit_margin,
            'purchase_date': batch.get('purchase_date'),
            'status': batch.get('status'),
            'ile_groups': ile_groups_analysis  # Add ILE group details
        }
    
    def _analyze_ile_group_profitability(self, batch: Dict[str, Any], ile_group: Dict[str, Any], start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Analyze profitability for a specific ILE group"""
        ile_number = ile_group.get('ile_number', 0)
        pieces_per_ile = batch.get('pieces_per_ile', 100)
        total_purchase_cost = batch.get('purchase_cost', 0)
        total_ile_packs = batch.get('total_ile', 1)
        batch_id = batch.get('id')
        
        # Calculate purchase cost per ILE pack
        purchase_cost_per_ile = total_purchase_cost / total_ile_packs if total_ile_packs > 0 else 0
        
        # Calculate processing costs from production records
        processing_cost = 0
        for prod_record in ile_group.get('production_records', []):
            prod_date = prod_record.get('production_date')
            if start_date and end_date:
                if prod_date and start_date <= prod_date <= end_date:
                    processing_cost += prod_record.get('processing_cost', 0)
            else:
                processing_cost += prod_record.get('processing_cost', 0)
        
        # Get sales revenue from journal entries (not from sales_records)
        sales_revenue = self._get_sales_revenue_for_ile_group(batch_id, ile_number, start_date, end_date)
        
        # Determine pieces sold based on status
        pieces_sold = pieces_per_ile if ile_group.get('status') == 'sold' else 0
        
        total_costs = purchase_cost_per_ile + processing_cost
        profit_loss = sales_revenue - total_costs
        profit_margin = (profit_loss / sales_revenue * 100) if sales_revenue > 0 else 0
        
        return {
            'ile_number': ile_number,
            'pieces_per_ile': pieces_per_ile,
            'purchase_cost': purchase_cost_per_ile,
            'processing_cost': processing_cost,
            'total_costs': total_costs,
            'sales_revenue': sales_revenue,
            'pieces_sold': pieces_sold,
            'profit_loss': profit_loss,
            'profit_margin': profit_margin,
            'status': ile_group.get('status', 'raw_material')
        }
    
    def generate_overall_profit_loss_summary(self, start_date: datetime = None, end_date: datetime = None, from_batch_id: str = None) -> Dict[str, Any]:
        """Generate overall Profit & Loss summary across all vendors and batches"""
        vendor_analysis = self.generate_profit_loss_by_vendor(start_date, end_date, from_batch_id)
        
        total_purchase_cost = sum(data['total_purchase_cost'] for data in vendor_analysis.values())
        total_processing_cost = sum(data['total_processing_cost'] for data in vendor_analysis.values())
        total_sales_revenue = sum(data['total_sales_revenue'] for data in vendor_analysis.values())
        total_pieces_sold = sum(data['total_pieces_sold'] for data in vendor_analysis.values())
        total_pieces_purchased = sum(data['total_pieces_purchased'] for data in vendor_analysis.values())
        
        total_costs = total_purchase_cost + total_processing_cost
        overall_profit_loss = total_sales_revenue - total_costs
        overall_profit_margin = (overall_profit_loss / total_sales_revenue * 100) if total_sales_revenue > 0 else 0
        
        # Generate period description
        period_desc = "All Time"
        if from_batch_id:
            from ..models.inventory_batch import InventoryBatch
            inventory_model = InventoryBatch(self.db, self.user_id)
            reference_batch = inventory_model.get_by_id(from_batch_id)
            if reference_batch:
                ref_date = reference_batch.get('created_at') or reference_batch.get('purchase_date')
                if ref_date:
                    period_desc = f"From {ref_date.strftime('%Y-%m-%d')} onwards"
        elif start_date and end_date:
            period_desc = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        return {
            'period': period_desc,
            'total_purchase_cost': total_purchase_cost,
            'total_processing_cost': total_processing_cost,
            'total_costs': total_costs,
            'total_sales_revenue': total_sales_revenue,
            'total_pieces_purchased': total_pieces_purchased,
            'total_pieces_sold': total_pieces_sold,
            'overall_profit_loss': overall_profit_loss,
            'overall_profit_margin': overall_profit_margin,
            'vendor_count': len(vendor_analysis),
            'vendor_analysis': vendor_analysis,
            'from_batch_id': from_batch_id
        }
    
    def _get_sales_revenue_for_ile_group(self, batch_id: str, ile_number: int, start_date: datetime = None, end_date: datetime = None) -> float:
        """Get sales revenue from journal entries for a specific batch and ILE group"""
        filters = [
            ('status', '==', 'posted'),
            ('batch_id', '==', batch_id),
            ('ile_number', '==', ile_number)
        ]
        
        if start_date and end_date:
            filters.extend([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
        
        entries = self.journal_entry_model.get_all(filters=filters)
        
        total_revenue = 0.0
        for entry in entries:
            for line in entry.get('entries', []):
                if line.get('account_code') == '4000':  # Sales Revenue account
                    total_revenue += line.get('credit', 0)
        
        return total_revenue
    
    def get_all_sales_transactions(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all sales transactions from journal entries"""
        from ..models.customer import Customer
        
        # Get all journal entries that contain sales revenue (account 4000)
        filters = [
            ('status', '==', 'posted')
        ]
        
        entries = self.journal_entry_model.get_all(filters=filters)
        
        # Get customer data for name lookup
        customer_model = Customer(self.db, self.user_id)
        all_customers = customer_model.get_all()
        customer_map = {customer['id']: customer['name'] for customer in all_customers}
        
        sales_transactions = []
        
        for entry in entries:
            # Check if this entry contains sales revenue
            has_sales_revenue = False
            sales_amount = 0
            customer_id = None
            batch_id = None
            ile_number = None
            
            for line in entry.get('entries', []):
                if line.get('account_code') == '4000':  # Sales Revenue account
                    has_sales_revenue = True
                    sales_amount = line.get('credit', 0)
                    break
            
            if has_sales_revenue:
                # Extract customer ID from description
                description = entry.get('description', '')
                if 'Sale to customer' in description:
                    # Extract customer ID from description like "Sale to customer 05af714e-941b-4e01-ac57-4d5f337a4e18 - Invoice INV123"
                    import re
                    match = re.search(r'Sale to customer ([a-f0-9-]+)', description)
                    if match:
                        customer_id = match.group(1)
                
                # Get batch and ILE info from journal entry
                batch_id = entry.get('batch_id')
                ile_number = entry.get('ile_number')
                
                # Get payment information
                payment_received = 0
                payment_method = 'unknown'
                
                for line in entry.get('entries', []):
                    if line.get('account_code') in ['1000', '1100']:  # Cash or Bank
                        payment_received += line.get('debit', 0)
                        payment_method = 'cash' if line.get('account_code') == '1000' else 'bank'
                    elif line.get('account_code') == '1200':  # Accounts Receivable
                        payment_received += line.get('debit', 0)
                        payment_method = 'credit'
                
                # Get customer name
                customer_name = customer_map.get(customer_id, 'Unknown Customer')
                
                sales_transactions.append({
                    'id': entry['id'],
                    'date': entry.get('date'),
                    'created_at': entry.get('created_at'),
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'batch_id': batch_id,
                    'ile_number': ile_number,
                    'sales_amount': sales_amount,
                    'payment_received': payment_received,
                    'outstanding_amount': sales_amount - payment_received,
                    'payment_method': payment_method,
                    'invoice_number': entry.get('reference', ''),
                    'description': description,
                    'status': 'completed' if payment_received >= sales_amount else 'partial'
                })
        
        # Sort by date (most recent first)
        sales_transactions.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # Apply limit if specified
        if limit:
            sales_transactions = sales_transactions[:limit]
        
        return sales_transactions
