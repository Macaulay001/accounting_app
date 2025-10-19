"""
Vendor Model
Manages vendor information and purchase history
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class Vendor(BaseModel):
    """Model for vendor management"""
    
    def get_collection_name(self) -> str:
        return "vendors"
    
    def create_vendor(self, 
                     name: str,
                     phone_number: Optional[str] = None,
                     email: Optional[str] = None,
                     address: Optional[str] = None,
                     contact_person: Optional[str] = None,
                     payment_terms: str = "cash") -> str:
        """Create a new vendor"""
        vendor_data = {
            'name': name,
            'phone_number': phone_number,
            'email': email,
            'address': address,
            'contact_person': contact_person,
            'payment_terms': payment_terms,
            'current_balance': 0.0,  # Will be calculated from journal entries
            'total_purchases': 0.0,
            'total_payments': 0.0,
            'last_transaction_date': None,
            'is_active': True
        }
        
        return self.create(vendor_data)
    
    def update_vendor(self, vendor_id: str, data: Dict[str, Any]) -> bool:
        """Update vendor information"""
        return self.update(vendor_id, data)
    
    def get_vendor_balance(self, vendor_id: str) -> float:
        """Get vendor's current account balance"""
        vendor = self.get_by_id(vendor_id)
        if not vendor:
            return 0.0
        
        # Calculate balance from journal entries
        from ..services.accounting_service import AccountingService
        accounting_service = AccountingService(self.db, self.user_id)
        
        # Get accounts payable balance
        payables_balance = accounting_service.get_account_balance("2000")  # Accounts Payable
        
        # This is a simplified calculation - in practice, you'd track per-vendor
        return vendor.get('current_balance', 0.0)
    
    def get_vendor_purchase_summary(self, vendor_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get purchase summary for a vendor"""
        vendor = self.get_by_id(vendor_id)
        if not vendor:
            return {}
        
        return {
            'vendor_id': vendor_id,
            'vendor_name': vendor.get('name'),
            'current_balance': self.get_vendor_balance(vendor_id),
            'payment_terms': vendor.get('payment_terms'),
            'total_purchases': vendor.get('total_purchases', 0.0),
            'total_payments': vendor.get('total_payments', 0.0),
            'is_active': vendor.get('is_active', True)
        }
    
    def get_active_vendors(self) -> List[Dict[str, Any]]:
        """Get all active vendors"""
        return self.search('is_active', True)
    
    def search_vendors(self, query: str) -> List[Dict[str, Any]]:
        """Search vendors by name, phone, or email"""
        all_vendors = self.get_all()
        results = []
        
        query_lower = query.lower()
        for vendor in all_vendors:
            if (query_lower in vendor.get('name', '').lower() or
                query_lower in vendor.get('phone_number', '').lower() or
                query_lower in vendor.get('email', '').lower()):
                results.append(vendor)
        
        return results
