"""
Vendor Deposit Model
Manages advance payments/deposits made to vendors before goods are received
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class VendorDeposit(BaseModel):
    """Model for vendor deposit/advance payment management"""
    
    def get_collection_name(self) -> str:
        return "vendor_deposits"
    
    def create_deposit(self, 
                      vendor_id: str,
                      amount: float,
                      deposit_date: datetime,
                      payment_method: str = "bank_transfer",
                      reference: str = "",
                      notes: str = "",
                      status: str = "pending") -> str:
        """Create a new vendor deposit"""
        deposit_data = {
            'vendor_id': vendor_id,
            'amount': amount,
            'deposit_date': deposit_date,
            'payment_method': payment_method,
            'reference': reference,
            'notes': notes,
            'status': status,  # pending, applied, refunded
            'applied_amount': 0.0,  # Amount applied to batches
            'remaining_amount': amount,  # Amount still available
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return self.create(deposit_data)
    
    def update_deposit(self, deposit_id: str, data: Dict[str, Any]) -> bool:
        """Update deposit information"""
        data['updated_at'] = datetime.utcnow()
        return self.update(deposit_id, data)
    
    def get_deposits_by_vendor(self, vendor_id: str) -> List[Dict[str, Any]]:
        """Get all deposits for a specific vendor"""
        return self.search('vendor_id', vendor_id)
    
    def get_pending_deposits(self) -> List[Dict[str, Any]]:
        """Get all pending deposits"""
        return self.search('status', 'pending')
    
    def apply_deposit_to_batch(self, deposit_id: str, batch_id: str, amount: float) -> bool:
        """Apply deposit amount to a specific batch"""
        deposit = self.get_by_id(deposit_id)
        if not deposit:
            return False
        
        if amount > deposit['remaining_amount']:
            return False
        
        # Update deposit
        new_applied_amount = deposit['applied_amount'] + amount
        new_remaining_amount = deposit['remaining_amount'] - amount
        
        update_data = {
            'applied_amount': new_applied_amount,
            'remaining_amount': new_remaining_amount,
            'status': 'applied' if new_remaining_amount == 0 else 'partial'
        }
        
        return self.update_deposit(deposit_id, update_data)
    
    def get_vendor_total_deposits(self, vendor_id: str) -> Dict[str, float]:
        """Get total deposit summary for a vendor"""
        deposits = self.get_deposits_by_vendor(vendor_id)
        
        total_deposits = sum(deposit['amount'] for deposit in deposits)
        total_applied = sum(deposit['applied_amount'] for deposit in deposits)
        total_remaining = sum(deposit['remaining_amount'] for deposit in deposits)
        
        return {
            'total_deposits': total_deposits,
            'total_applied': total_applied,
            'total_remaining': total_remaining
        }
