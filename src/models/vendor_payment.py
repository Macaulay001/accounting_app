"""
Vendor Payment Model
Tracks payments made to vendors for specific inventory batches
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class VendorPayment(BaseModel):
    """Model for tracking vendor payments for inventory batches"""
    
    def get_collection_name(self) -> str:
        return "vendor_payments"
    
    def create_payment(self,
                      batch_id: str,
                      vendor_id: str,
                      payment_amount: float,
                      payment_date: datetime,
                      payment_method: str = "cash",
                      reference: str = "",
                      notes: str = "") -> str:
        """
        Create a vendor payment record
        
        Args:
            batch_id: ID of the inventory batch
            vendor_id: ID of the vendor
            payment_amount: Amount paid
            payment_date: Date of payment
            payment_method: How payment was made (cash, bank_transfer, check, etc.)
            reference: Payment reference (check number, transfer ref, etc.)
            notes: Additional notes about the payment
        """
        payment_data = {
            'batch_id': batch_id,
            'vendor_id': vendor_id,
            'payment_amount': payment_amount,
            'payment_date': payment_date,
            'payment_method': payment_method,
            'reference': reference,
            'notes': notes,
            'status': 'completed',  # completed, pending, failed
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return self.create(payment_data)
    
    def get_payments_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all payments for a specific batch"""
        return self.search('batch_id', batch_id)
    
    def get_payments_by_vendor(self, vendor_id: str) -> List[Dict[str, Any]]:
        """Get all payments for a specific vendor"""
        return self.search('vendor_id', vendor_id)
    
    def get_total_paid_for_batch(self, batch_id: str) -> float:
        """Calculate total amount paid for a specific batch"""
        payments = self.get_payments_by_batch(batch_id)
        return sum(payment.get('payment_amount', 0) for payment in payments)
    
    def get_total_paid_to_vendor(self, vendor_id: str) -> float:
        """Calculate total amount paid to a specific vendor"""
        payments = self.get_payments_by_vendor(vendor_id)
        return sum(payment.get('payment_amount', 0) for payment in payments)
    
    def get_outstanding_balance_for_batch(self, batch_id: str, batch_purchase_cost: float) -> float:
        """Calculate outstanding balance for a specific batch"""
        total_paid = self.get_total_paid_for_batch(batch_id)
        return max(0, batch_purchase_cost - total_paid)
    
    def get_payment_summary_by_vendor(self, vendor_id: str) -> Dict[str, Any]:
        """Get payment summary for a vendor including all their batches"""
        payments = self.get_payments_by_vendor(vendor_id)
        
        # Group payments by batch
        batch_payments = {}
        for payment in payments:
            batch_id = payment.get('batch_id')
            if batch_id not in batch_payments:
                batch_payments[batch_id] = []
            batch_payments[batch_id].append(payment)
        
        # Calculate totals
        total_paid = sum(payment.get('payment_amount', 0) for payment in payments)
        total_batches = len(batch_payments)
        
        return {
            'vendor_id': vendor_id,
            'total_paid': total_paid,
            'total_batches': total_batches,
            'batch_payments': batch_payments,
            'payment_count': len(payments)
        }
    
    def get_recent_payments(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent payments ordered by created_at (most recent first)"""
        all_payments = self.get_all(order_by='created_at')
        if all_payments:
            # Sort by created_at (most recent first) and take the first 'limit' items
            all_payments.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            return all_payments[:limit]
        return []
