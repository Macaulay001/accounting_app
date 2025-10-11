from typing import Optional, List, Dict
from datetime import datetime
from .base import BaseModel


class Expense(BaseModel):
    """Model for managing business expenses"""
    
    def get_collection_name(self) -> str:
        return "expenses"
    
    def create_expense(self, 
                      expense_type_id: str,
                      amount: float,
                      description: str,
                      date: datetime,
                      payment_method: str = "cash",
                      reference: Optional[str] = None,
                      vendor_id: Optional[str] = None) -> str:
        """Create a new expense record"""
        expense_data = {
            'expense_type_id': expense_type_id,
            'amount': amount,
            'description': description,
            'date': date,
            'payment_method': payment_method,
            'reference': reference or f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'vendor_id': vendor_id
        }
        
        return self.create(expense_data)
    
    def get_expenses_by_type(self, expense_type_id: str) -> List[Dict]:
        """Get all expenses for a specific expense type"""
        all_expenses = self.get_all()
        return [exp for exp in all_expenses if exp.get('expense_type_id') == expense_type_id]
    
    def get_expenses_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get expenses within a date range"""
        all_expenses = self.get_all()
        filtered_expenses = []
        
        for expense in all_expenses:
            expense_date = expense.get('date')
            if expense_date:
                # Handle both datetime and date objects
                if hasattr(expense_date, 'date'):
                    expense_date = expense_date.date()
                elif hasattr(expense_date, 'date'):
                    expense_date = expense_date.date()
                
                if start_date.date() <= expense_date <= end_date.date():
                    filtered_expenses.append(expense)
        
        return filtered_expenses
    
    def get_expenses_by_vendor(self, vendor_id: str) -> List[Dict]:
        """Get all expenses for a specific vendor"""
        all_expenses = self.get_all()
        return [exp for exp in all_expenses if exp.get('vendor_id') == vendor_id]
    
    def get_total_expenses_by_type(self, expense_type_id: str) -> float:
        """Get total amount for a specific expense type"""
        expenses = self.get_expenses_by_type(expense_type_id)
        return sum(exp.get('amount', 0) for exp in expenses)
    
    def get_total_expenses_by_date_range(self, start_date: datetime, end_date: datetime) -> float:
        """Get total expenses within a date range"""
        expenses = self.get_expenses_by_date_range(start_date, end_date)
        return sum(exp.get('amount', 0) for exp in expenses)
    
    def get_expenses_summary(self) -> Dict:
        """Get summary of all expenses"""
        all_expenses = self.get_all()
        
        total_amount = sum(exp.get('amount', 0) for exp in all_expenses)
        
        # Group by payment method
        payment_methods = {}
        for exp in all_expenses:
            method = exp.get('payment_method', 'cash')
            payment_methods[method] = payment_methods.get(method, 0) + exp.get('amount', 0)
        
        # Group by expense type
        expense_types = {}
        for exp in all_expenses:
            exp_type_id = exp.get('expense_type_id')
            if exp_type_id:
                expense_types[exp_type_id] = expense_types.get(exp_type_id, 0) + exp.get('amount', 0)
        
        return {
            'total_expenses': total_amount,
            'total_count': len(all_expenses),
            'by_payment_method': payment_methods,
            'by_expense_type': expense_types
        }
    
    def update_expense(self, expense_id: str, 
                      expense_type_id: Optional[str] = None,
                      amount: Optional[float] = None,
                      description: Optional[str] = None,
                      date: Optional[datetime] = None,
                      payment_method: Optional[str] = None,
                      reference: Optional[str] = None,
                      vendor_id: Optional[str] = None) -> bool:
        """Update an expense record"""
        update_data = {}
        
        if expense_type_id is not None:
            update_data['expense_type_id'] = expense_type_id
        if amount is not None:
            update_data['amount'] = amount
        if description is not None:
            update_data['description'] = description
        if date is not None:
            update_data['date'] = date
        if payment_method is not None:
            update_data['payment_method'] = payment_method
        if reference is not None:
            update_data['reference'] = reference
        if vendor_id is not None:
            update_data['vendor_id'] = vendor_id
        
        return self.update(expense_id, update_data)
