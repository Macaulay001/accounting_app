"""
Journal Entry Model
Represents double-entry bookkeeping journal entries
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel
from ..constants import AccountType, is_debit_account, is_credit_account

class JournalEntry(BaseModel):
    """Model for journal entries following double-entry bookkeeping"""
    
    def get_collection_name(self) -> str:
        return "journal_entries"
    
    def create_entry(self, 
                    date: datetime,
                    description: str,
                    reference: str,
                    entries: List[Dict[str, Any]]) -> str:
        """
        Create a journal entry with proper double-entry validation
        
        Args:
            date: Transaction date
            description: Description of the transaction
            reference: Reference number (invoice, receipt, etc.)
            entries: List of debit/credit entries
                    Format: [{"account_code": "1000", "debit": 100.00, "credit": 0.00}, ...]
        
        Returns:
            Journal entry ID
        """
        # Validate double-entry (total debits = total credits)
        total_debits = sum(entry.get('debit', 0) for entry in entries)
        total_credits = sum(entry.get('credit', 0) for entry in entries)
        
        if abs(total_debits - total_credits) > 0.01:  # Allow for small rounding differences
            raise ValueError(f"Journal entry not balanced. Debits: {total_debits}, Credits: {total_credits}")
        
        # Validate each entry has either debit or credit, not both
        for entry in entries:
            if entry.get('debit', 0) > 0 and entry.get('credit', 0) > 0:
                raise ValueError("Entry cannot have both debit and credit amounts")
            if entry.get('debit', 0) == 0 and entry.get('credit', 0) == 0:
                raise ValueError("Entry must have either debit or credit amount")
        
        # Create journal entry data
        journal_data = {
            'date': date,
            'description': description,
            'reference': reference,
            'entries': entries,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'status': 'posted'  # posted, draft, reversed
        }
        
        return self.create(journal_data)
    
    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get journal entries within a date range"""
        filters = [
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ]
        return self.get_all(filters=filters, order_by='date')
    
    def get_entries_by_account(self, account_code: str) -> List[Dict[str, Any]]:
        """Get all journal entries affecting a specific account"""
        all_entries = self.get_all()
        account_entries = []
        
        for entry in all_entries:
            for line in entry.get('entries', []):
                if line.get('account_code') == account_code:
                    account_entries.append(entry)
                    break
        
        return account_entries
    
    def reverse_entry(self, entry_id: str, reason: str) -> str:
        """Reverse a journal entry by creating a reversing entry"""
        original_entry = self.get_by_id(entry_id)
        if not original_entry:
            raise ValueError("Journal entry not found")
        
        if original_entry.get('status') == 'reversed':
            raise ValueError("Journal entry already reversed")
        
        # Create reversing entries (swap debits and credits)
        reversing_entries = []
        for line in original_entry.get('entries', []):
            reversing_entries.append({
                'account_code': line['account_code'],
                'debit': line.get('credit', 0),
                'credit': line.get('debit', 0)
            })
        
        # Create reversing journal entry
        reversing_data = {
            'date': datetime.utcnow(),
            'description': f"Reversal of {original_entry['description']} - {reason}",
            'reference': f"REV-{original_entry['reference']}",
            'entries': reversing_entries,
            'total_debits': original_entry['total_credits'],
            'total_credits': original_entry['total_debits'],
            'status': 'posted',
            'reverses_entry_id': entry_id
        }
        
        # Mark original entry as reversed
        self.update(entry_id, {'status': 'reversed', 'reversed_at': datetime.utcnow()})
        
        return self.create(reversing_data)
    
    def get_account_balance(self, account_code: str, as_of_date: Optional[datetime] = None) -> float:
        """Calculate account balance as of a specific date"""
        from ..constants import CHART_OF_ACCOUNTS
        
        filters = [('status', '==', 'posted')]
        if as_of_date:
            filters.append(('date', '<=', as_of_date))
        
        entries = self.get_all(filters=filters)
        
        # Determine account type for proper balance calculation
        account_info = CHART_OF_ACCOUNTS.get(account_code, {})
        account_type = account_info.get('type', 'asset')
        
        balance = 0.0
        for entry in entries:
            for line in entry.get('entries', []):
                if line.get('account_code') == account_code:
                    debit = line.get('debit', 0)
                    credit = line.get('credit', 0)
                    
                    # Calculate balance based on account type
                    if account_type in ['asset', 'expense']:
                        # Normal debit balance accounts
                        balance += debit - credit
                    else:
                        # Normal credit balance accounts (liability, equity, revenue)
                        balance += credit - debit
        
        return balance
    
    def get_trial_balance(self, as_of_date: Optional[datetime] = None) -> Dict[str, float]:
        """Generate trial balance for all accounts"""
        from ..constants import CHART_OF_ACCOUNTS
        
        trial_balance = {}
        
        for account_code in CHART_OF_ACCOUNTS.keys():
            balance = self.get_account_balance(account_code, as_of_date)
            if balance != 0:  # Only include accounts with non-zero balances
                trial_balance[account_code] = balance
        
        return trial_balance
