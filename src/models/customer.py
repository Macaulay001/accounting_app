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
                       credit_limit: float = 0.0,
                       opening_balance_type: str = 'none',
                       opening_balance_amount: float = 0.0) -> str:
        """Create a new customer"""
        customer_data = {
            'name': name,
            'phone_number': phone_number,
            'email': email,
            'address': address,
            'credit_limit': credit_limit,
            'opening_balance_type': opening_balance_type,
            'opening_balance_amount': opening_balance_amount,
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
        """Get customer's current account balance using centralized service"""
        try:
            from ..services.customer_balance_service import CustomerBalanceService
            from ..models.customer import Customer
            from ..models.vendor import Vendor
            from ..models.product import Product
            from ..models.journal_entry import JournalEntry
            from ..models.inventory_batch import InventoryBatch
            from ..models.customer_deposit import CustomerDeposit
            
            # Create models dict for the service
            models = {
                'customer': Customer(self.db, self.user_id),
                'vendor': Vendor(self.db, self.user_id),
                'product': Product(self.db, self.user_id),
                'journal_entry': JournalEntry(self.db, self.user_id),
                'inventory_batch': InventoryBatch(self.db, self.user_id),
                'customer_deposit': CustomerDeposit(self.db, self.user_id)
            }
            
            # Use centralized service
            balance_service = CustomerBalanceService(models)
            balance_info = balance_service.get_customer_balance_summary(customer_id)
            return balance_info['current_balance']
            
        except Exception as e:
            print(f"Error getting customer balance: {e}")
            return 0.0
    
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
