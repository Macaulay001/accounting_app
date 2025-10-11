"""
Customer Model
Manages customer information and account balances
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class Customer(BaseModel):
    """Model for customer management"""
    
    def get_collection_name(self) -> str:
        return "customers"
    
    def create_customer(self, 
                       name: str,
                       phone_number: Optional[str] = None,
                       email: Optional[str] = None,
                       address: Optional[str] = None,
                       credit_limit: float = 0.0) -> str:
        """Create a new customer"""
        customer_data = {
            'name': name,
            'phone_number': phone_number,
            'email': email,
            'address': address,
            'credit_limit': credit_limit,
            'current_balance': 0.0,  # Will be calculated from journal entries
            'total_sales': 0.0,
            'total_payments': 0.0,
            'last_transaction_date': None
        }
        
        return self.create(customer_data)
    
    def update_customer(self, customer_id: str, data: Dict[str, Any]) -> bool:
        """Update customer information"""
        return self.update(customer_id, data)
    
    def get_customer_balance(self, customer_id: str) -> float:
        """Get customer's current account balance"""
        customer = self.get_by_id(customer_id)
        if not customer:
            return 0.0
        
        # Calculate balance from journal entries
        from ..services.accounting_service import AccountingService
        accounting_service = AccountingService(self.db, self.user_id)
        
        # Get all sales to this customer
        sales_balance = accounting_service.get_account_balance("1200")  # Accounts Receivable
        
        # This is a simplified calculation - in practice, you'd track per-customer
        return customer.get('current_balance', 0.0)
    
    def get_customer_sales_summary(self, customer_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get sales summary for a customer"""
        # This would typically query journal entries for sales to this specific customer
        # For now, return basic customer info
        customer = self.get_by_id(customer_id)
        if not customer:
            return {}
        
        return {
            'customer_id': customer_id,
            'customer_name': customer.get('name'),
            'current_balance': self.get_customer_balance(customer_id),
            'credit_limit': customer.get('credit_limit', 0.0),
            'total_sales': customer.get('total_sales', 0.0),
            'total_payments': customer.get('total_payments', 0.0)
        }
    
    def search_customers(self, query: str) -> List[Dict[str, Any]]:
        """Search customers by name, phone, or email"""
        # This is a simplified search - in practice, you'd use Firestore's text search
        all_customers = self.get_all()
        results = []
        
        query_lower = query.lower()
        for customer in all_customers:
            if (query_lower in customer.get('name', '').lower() or
                query_lower in customer.get('phone_number', '').lower() or
                query_lower in customer.get('email', '').lower()):
                results.append(customer)
        
        return results
