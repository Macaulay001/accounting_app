"""
Customer Deposit Model

Tracks customer advance payments and deposits for goods.
Allows customers to make advance payments that can be applied to future purchases.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from .base import BaseModel


class CustomerDeposit(BaseModel):
    """Model for tracking customer deposits and advance payments"""
    
    def get_collection_name(self) -> str:
        """Return the Firestore collection name for this model"""
        return 'customer_deposits'
    
    def create_deposit(self, 
                       customer_id: str, 
                       amount: float, 
                       deposit_date: datetime,
                       payment_method: str = 'cash',
                       reference: str = None,
                       notes: str = '') -> str:
        """Create a new customer deposit record"""
        
        deposit_data = {
            'customer_id': customer_id,
            'amount': amount,
            'deposit_date': deposit_date,
            'payment_method': payment_method,
            'reference': reference or f"DEP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'notes': notes,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        return self.create(deposit_data)
    
    def get_customer_balance(self, customer_id: str) -> Dict[str, Any]:
        """Get current account balance for a customer using centralized service"""
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
            balance_info = balance_service.get_customer_balance(customer_id)
            
            return {
                'customer_id': customer_id,
                'current_balance': balance_info['current_balance'],
                'total_deposits': balance_info['total_deposits'],
                'total_used': balance_info['total_deposits'] - balance_info['current_balance'],
                'deposit_count': len(balance_info['deposits'])
            }
            
        except Exception as e:
            print(f"Error getting customer balance: {e}")
            return {
                'customer_id': customer_id,
                'current_balance': 0.0,
                'total_deposits': 0.0,
                'total_used': 0.0,
                'deposit_count': 0
            }
    
    def get_customer_deposits(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent deposits for a customer (most recent first)"""
        
        deposits = self.get_all(filters=[('customer_id', '==', customer_id)])
        
        if deposits:
            # Sort by created_at (most recent first)
            deposits.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            return deposits[:limit]
        
        return []
    
    def get_all_customer_balances(self) -> List[Dict[str, Any]]:
        """Get account balances for all customers"""
        
        # Get all deposits
        all_deposits = self.get_all()
        
        # Group by customer_id
        customer_deposits = {}
        for deposit in all_deposits:
            customer_id = deposit.get('customer_id')
            if customer_id not in customer_deposits:
                customer_deposits[customer_id] = []
            customer_deposits[customer_id].append(deposit)
        
        # Calculate balances for each customer
        customer_balances = []
        for customer_id, deposits in customer_deposits.items():
            balance_info = self.get_customer_balance(customer_id)
            customer_balances.append(balance_info)
        
        # Sort by current balance (highest credit first)
        customer_balances.sort(key=lambda x: x.get('current_balance', 0), reverse=True)
        
        return customer_balances
    
    def get_total_deposits(self) -> float:
        """Get total deposits across all customers"""
        all_deposits = self.get_all()
        return sum(deposit.get('amount', 0) for deposit in all_deposits)
    
    def record_deposit_usage(self, customer_id: str, amount: float, usage_date: datetime, reference: str = None) -> str:
        """Record usage of customer deposit (negative amount)"""
        usage_data = {
            'customer_id': customer_id,
            'amount': -amount,  # Negative amount for usage
            'deposit_date': usage_date,
            'payment_method': 'deposit_usage',
            'reference': reference or f"USE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'notes': f'Used for sale - {reference}',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        return self.create(usage_data)
