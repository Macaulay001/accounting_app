"""
Financial Statements Service
Handles generation of Trial Balance, Profit & Loss, and Balance Sheet
Following GAAP principles with high fidelity
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP

from ..constants.chart_of_accounts import (
    CHART_OF_ACCOUNTS, 
    AccountType, 
    AccountCategory,
    is_debit_account,
    is_credit_account
)

class FinancialStatementsService:
    """Service for generating accurate financial statements"""
    
    def __init__(self, journal_entry_model):
        self.journal_entry_model = journal_entry_model
    
    def get_trial_balance(self, as_of_date: datetime = None) -> Dict[str, Any]:
        """
        Generate Trial Balance as of specific date
        Returns all accounts with their debit and credit balances
        """
        # Get all journal entries up to the specified date
        all_entries = self.journal_entry_model.get_all()
        
        if as_of_date:
            # Filter entries by date
            all_entries = [entry for entry in all_entries 
                          if entry.get('date', datetime.min) <= as_of_date]
        
        # Initialize account balances
        account_balances = {}
        
        # Process all journal entries
        for entry in all_entries:
            for line in entry.get('entries', []):
                account_code = line.get('account_code')
                debit = line.get('debit', 0)
                credit = line.get('credit', 0)
                
                if account_code not in account_balances:
                    account_balances[account_code] = {
                        'debit_total': 0,
                        'credit_total': 0,
                        'account_name': CHART_OF_ACCOUNTS.get(account_code, {}).get('name', 'Unknown Account'),
                        'account_type': CHART_OF_ACCOUNTS.get(account_code, {}).get('type', AccountType.ASSET)
                    }
                
                account_balances[account_code]['debit_total'] += debit
                account_balances[account_code]['credit_total'] += credit
        
        # Calculate net balances for each account
        trial_balance_data = []
        total_debits = 0
        total_credits = 0
        
        for account_code, account_info in CHART_OF_ACCOUNTS.items():
            if account_code in account_balances:
                balance_info = account_balances[account_code]
                debit_total = balance_info['debit_total']
                credit_total = balance_info['credit_total']
                
                # Calculate net balance based on account type
                account_type = account_info['type']
                if is_debit_account(account_type):
                    # Assets and Expenses: Debit - Credit
                    net_balance = debit_total - credit_total
                    if net_balance >= 0:
                        debit_balance = net_balance
                        credit_balance = 0
                    else:
                        debit_balance = 0
                        credit_balance = abs(net_balance)
                else:
                    # Liabilities, Equity, Revenue: Credit - Debit
                    net_balance = credit_total - debit_total
                    if net_balance >= 0:
                        debit_balance = 0
                        credit_balance = net_balance
                    else:
                        debit_balance = abs(net_balance)
                        credit_balance = 0
                
                trial_balance_data.append({
                    'account_code': account_code,
                    'account_name': account_info['name'],
                    'account_type': account_type.value,
                    'debit_balance': debit_balance,
                    'credit_balance': credit_balance,
                    'net_balance': net_balance
                })
                
                total_debits += debit_balance
                total_credits += credit_balance
            else:
                # Account exists in chart but has no transactions
                trial_balance_data.append({
                    'account_code': account_code,
                    'account_name': account_info['name'],
                    'account_type': account_info['type'].value,
                    'debit_balance': 0,
                    'credit_balance': 0,
                    'net_balance': 0
                })
        
        # Sort by account code
        trial_balance_data.sort(key=lambda x: x['account_code'])
        
        return {
            'trial_balance': trial_balance_data,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': abs(total_debits - total_credits) < 0.01,  # Allow for rounding differences
            'as_of_date': as_of_date or datetime.now(),
            'generated_at': datetime.now()
        }
    
    def get_profit_loss_statement(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Generate Profit & Loss Statement for a specific period
        """
        # Get trial balance for the period
        trial_balance = self.get_trial_balance(end_date)
        
        # Extract revenue accounts (4000-4999)
        revenue_accounts = []
        total_revenue = 0
        
        for account in trial_balance['trial_balance']:
            if account['account_type'] == AccountType.REVENUE.value:
                revenue_amount = account['credit_balance'] - account['debit_balance']
                if revenue_amount > 0:  # Only include accounts with positive revenue
                    revenue_accounts.append({
                        'account_code': account['account_code'],
                        'account_name': account['account_name'],
                        'amount': revenue_amount
                    })
                    total_revenue += revenue_amount
        
        # Extract COGS accounts (5000-5999, category COST_OF_GOODS_SOLD)
        cogs_accounts = []
        total_cogs = 0
        
        for account in trial_balance['trial_balance']:
            account_code = account['account_code']
            account_info = CHART_OF_ACCOUNTS.get(account_code, {})
            if (account['account_type'] == AccountType.EXPENSE.value and 
                account_info.get('category') == AccountCategory.COST_OF_GOODS_SOLD):
                cogs_amount = account['debit_balance'] - account['credit_balance']
                if cogs_amount > 0:  # Only include accounts with positive COGS
                    cogs_accounts.append({
                        'account_code': account['account_code'],
                        'account_name': account['account_name'],
                        'amount': cogs_amount
                    })
                    total_cogs += cogs_amount
        
        # Calculate Gross Profit
        gross_profit = total_revenue - total_cogs
        
        # Extract Operating Expenses (5000-5999, category OPERATING_EXPENSE)
        operating_expenses = []
        total_operating_expenses = 0
        
        for account in trial_balance['trial_balance']:
            account_code = account['account_code']
            account_info = CHART_OF_ACCOUNTS.get(account_code, {})
            if (account['account_type'] == AccountType.EXPENSE.value and 
                account_info.get('category') == AccountCategory.OPERATING_EXPENSE):
                expense_amount = account['debit_balance'] - account['credit_balance']
                if expense_amount > 0:  # Only include accounts with positive expenses
                    operating_expenses.append({
                        'account_code': account['account_code'],
                        'account_name': account['account_name'],
                        'amount': expense_amount
                    })
                    total_operating_expenses += expense_amount
        
        # Calculate Net Profit/Loss
        net_profit_loss = gross_profit - total_operating_expenses
        
        return {
            'period_start': start_date,
            'period_end': end_date or datetime.now(),
            'generated_at': datetime.now(),
            'revenue': {
                'accounts': revenue_accounts,
                'total': total_revenue
            },
            'cost_of_goods_sold': {
                'accounts': cogs_accounts,
                'total': total_cogs
            },
            'gross_profit': gross_profit,
            'operating_expenses': {
                'accounts': operating_expenses,
                'total': total_operating_expenses
            },
            'net_profit_loss': net_profit_loss,
            'gross_profit_margin': (gross_profit / total_revenue * 100) if total_revenue > 0 else 0,
            'net_profit_margin': (net_profit_loss / total_revenue * 100) if total_revenue > 0 else 0
        }
    
    def get_balance_sheet(self, as_of_date: datetime = None) -> Dict[str, Any]:
        """
        Generate Balance Sheet as of specific date
        """
        # Get trial balance for the date
        trial_balance = self.get_trial_balance(as_of_date)
        
        # Extract Assets (1000-1999)
        current_assets = []
        fixed_assets = []
        total_current_assets = 0
        total_fixed_assets = 0
        
        for account in trial_balance['trial_balance']:
            if account['account_type'] == AccountType.ASSET.value:
                account_code = account['account_code']
                account_info = CHART_OF_ACCOUNTS.get(account_code, {})
                category = account_info.get('category')
                
                # Calculate net balance (Debit - Credit for assets)
                net_balance = account['debit_balance'] - account['credit_balance']
                
                if category == AccountCategory.CURRENT_ASSET:
                    current_assets.append({
                        'account_code': account_code,
                        'account_name': account['account_name'],
                        'amount': net_balance
                    })
                    total_current_assets += net_balance
                elif category == AccountCategory.FIXED_ASSET:
                    fixed_assets.append({
                        'account_code': account_code,
                        'account_name': account['account_name'],
                        'amount': net_balance
                    })
                    total_fixed_assets += net_balance
        
        total_assets = total_current_assets + total_fixed_assets
        
        # Extract Liabilities (2000-2999)
        current_liabilities = []
        long_term_liabilities = []
        total_current_liabilities = 0
        total_long_term_liabilities = 0
        
        for account in trial_balance['trial_balance']:
            if account['account_type'] == AccountType.LIABILITY.value:
                account_code = account['account_code']
                account_info = CHART_OF_ACCOUNTS.get(account_code, {})
                category = account_info.get('category')
                
                # Calculate net balance (Credit - Debit for liabilities)
                net_balance = account['credit_balance'] - account['debit_balance']
                
                if category == AccountCategory.CURRENT_LIABILITY:
                    current_liabilities.append({
                        'account_code': account_code,
                        'account_name': account['account_name'],
                        'amount': net_balance
                    })
                    total_current_liabilities += net_balance
                elif category == AccountCategory.LONG_TERM_LIABILITY:
                    long_term_liabilities.append({
                        'account_code': account_code,
                        'account_name': account['account_name'],
                        'amount': net_balance
                    })
                    total_long_term_liabilities += net_balance
        
        total_liabilities = total_current_liabilities + total_long_term_liabilities
        
        # Extract Equity (3000-3999)
        equity_accounts = []
        total_equity = 0
        
        for account in trial_balance['trial_balance']:
            if account['account_type'] == AccountType.EQUITY.value:
                account_code = account['account_code']
                account_info = CHART_OF_ACCOUNTS.get(account_code, {})
                
                # Calculate net balance (Credit - Debit for equity)
                net_balance = account['credit_balance'] - account['debit_balance']
                
                equity_accounts.append({
                    'account_code': account_code,
                    'account_name': account['account_name'],
                    'amount': net_balance
                })
                total_equity += net_balance
        
        # Calculate if balance sheet balances
        total_liabilities_and_equity = total_liabilities + total_equity
        is_balanced = abs(total_assets - total_liabilities_and_equity) < 0.01
        
        return {
            'as_of_date': as_of_date or datetime.now(),
            'generated_at': datetime.now(),
            'assets': {
                'current_assets': current_assets,
                'total_current_assets': total_current_assets,
                'fixed_assets': fixed_assets,
                'total_fixed_assets': total_fixed_assets,
                'total_assets': total_assets
            },
            'liabilities': {
                'current_liabilities': current_liabilities,
                'total_current_liabilities': total_current_liabilities,
                'long_term_liabilities': long_term_liabilities,
                'total_long_term_liabilities': total_long_term_liabilities,
                'total_liabilities': total_liabilities
            },
            'equity': {
                'accounts': equity_accounts,
                'total_equity': total_equity
            },
            'total_liabilities_and_equity': total_liabilities_and_equity,
            'is_balanced': is_balanced,
            'balancing_difference': total_assets - total_liabilities_and_equity
        }
    
    def get_financial_summary(self, as_of_date: datetime = None) -> Dict[str, Any]:
        """
        Get a comprehensive financial summary including all three statements
        """
        trial_balance = self.get_trial_balance(as_of_date)
        profit_loss = self.get_profit_loss_statement(start_date=None, end_date=as_of_date)
        balance_sheet = self.get_balance_sheet(as_of_date)
        
        return {
            'trial_balance': trial_balance,
            'profit_loss': profit_loss,
            'balance_sheet': balance_sheet,
            'summary': {
                'total_assets': balance_sheet['assets']['total_assets'],
                'total_liabilities': balance_sheet['liabilities']['total_liabilities'],
                'total_equity': balance_sheet['equity']['total_equity'],
                'net_profit_loss': profit_loss['net_profit_loss'],
                'total_revenue': profit_loss['revenue']['total'],
                'is_balanced': trial_balance['is_balanced'] and balance_sheet['is_balanced']
            }
        }
