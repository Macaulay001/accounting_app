"""
Inventory Batch Model
Manages inventory batches by vendor and ile groups for tracking raw materials through production to sales
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class InventoryBatch(BaseModel):
    """Model for tracking inventory batches by vendor and ile groups"""
    
    def get_collection_name(self) -> str:
        return "inventory_batches"
    
    def create_batch(self, 
                    vendor_id: str,
                    vendor_name: str,
                    raw_material_type: str = "cow_skin",
                    total_ile: int = 1,
                    pieces_per_ile: int = 100,
                    total_pieces: int = None,
                    purchase_date: datetime = None,
                    purchase_cost: float = 0.0,
                    payment_method: str = "accounts_payable",
                    reference: str = "",
                    status: str = "raw_material") -> str:
        """
        Create a new inventory batch
        
        Args:
            vendor_id: ID of the vendor
            vendor_name: Name of the vendor
            raw_material_type: Type of raw material (cow_skin, etc.)
            total_ile: Number of ile packs purchased
            pieces_per_ile: Pieces per ile (usually 100)
            total_pieces: Total pieces (calculated if not provided)
            purchase_date: Date of purchase
            purchase_cost: Total cost of the batch
            status: Current status (raw_material, in_production, finished_goods, sold)
        """
        if total_pieces is None:
            total_pieces = total_ile * pieces_per_ile
        
        if purchase_date is None:
            purchase_date = datetime.now()
        
        batch_data = {
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
            'raw_material_type': raw_material_type,
            'total_ile': total_ile,
            'pieces_per_ile': pieces_per_ile,
            'total_pieces': total_pieces,
            'purchase_date': purchase_date,
            'purchase_cost': purchase_cost,
            'payment_method': payment_method,
            'reference': reference,
            'status': status,
            'current_pieces': total_pieces,  # Track remaining pieces
            'ile_groups': self._create_ile_groups(total_ile, pieces_per_ile),
            'production_records': [],
            'sales_records': [],
            'expense_records': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return self.create(batch_data)
    
    def _create_ile_groups(self, total_ile: int, pieces_per_ile: int) -> List[Dict[str, Any]]:
        """Create ile group tracking structure"""
        ile_groups = []
        for i in range(total_ile):
            ile_groups.append({
                'ile_number': i + 1,
                'pieces': pieces_per_ile,
                'remaining_pieces': pieces_per_ile,
                'status': 'raw_material',  # raw_material, in_production, finished_goods, sold
                'production_date': None,
                'completion_date': None,
                'sales_date': None
            })
        return ile_groups
    
    def update_batch_status(self, batch_id: str, new_status: str) -> bool:
        """Update the overall batch status"""
        return self.update(batch_id, {'status': new_status, 'updated_at': datetime.utcnow()})
    
    def update_ile_group_status(self, batch_id: str, ile_number: int, new_status: str, 
                               production_date: datetime = None, completion_date: datetime = None) -> bool:
        """Update status of a specific ile group"""
        batch = self.get_by_id(batch_id)
        if not batch:
            return False
        
        ile_groups = batch.get('ile_groups', [])
        for ile_group in ile_groups:
            if ile_group['ile_number'] == ile_number:
                ile_group['status'] = new_status
                if production_date:
                    ile_group['production_date'] = production_date
                if completion_date:
                    ile_group['completion_date'] = completion_date
                break
        
        return self.update(batch_id, {
            'ile_groups': ile_groups,
            'updated_at': datetime.utcnow()
        })
    
    def record_production(self, batch_id: str, ile_number: int, pieces_used: int, 
                         production_date: datetime = None) -> bool:
        """Record production usage from a specific ile group"""
        if production_date is None:
            production_date = datetime.now()
        
        batch = self.get_by_id(batch_id)
        if not batch:
            return False
        
        ile_groups = batch.get('ile_groups', [])
        for ile_group in ile_groups:
            if ile_group['ile_number'] == ile_number:
                if ile_group['remaining_pieces'] < pieces_used:
                    raise ValueError(f"Not enough pieces in ile {ile_number}. Available: {ile_group['remaining_pieces']}, Requested: {pieces_used}")
                
                ile_group['remaining_pieces'] -= pieces_used
                ile_group['status'] = 'in_production'
                ile_group['production_date'] = production_date
                break
        
        # Update batch totals
        total_remaining = sum(ile['remaining_pieces'] for ile in ile_groups)
        
        return self.update(batch_id, {
            'ile_groups': ile_groups,
            'current_pieces': total_remaining,
            'updated_at': datetime.utcnow()
        })
    
    def record_sale(self, batch_id: str, ile_number: int, pieces_sold: int, 
                   sales_date: datetime = None) -> bool:
        """Record sales from a specific ile group"""
        if sales_date is None:
            sales_date = datetime.now()
        
        batch = self.get_by_id(batch_id)
        if not batch:
            return False
        
        ile_groups = batch.get('ile_groups', [])
        for ile_group in ile_groups:
            if ile_group['ile_number'] == ile_number:
                ile_group['status'] = 'sold'
                ile_group['sales_date'] = sales_date
                break
        
        return self.update(batch_id, {
            'ile_groups': ile_groups,
            'updated_at': datetime.utcnow()
        })
    
    def get_batches_by_vendor(self, vendor_id: str) -> List[Dict[str, Any]]:
        """Get all batches for a specific vendor"""
        return self.search('vendor_id', vendor_id)
    
    def get_active_batches(self) -> List[Dict[str, Any]]:
        """Get all batches that are not completely sold"""
        all_batches = self.get_all()
        active_batches = []
        
        for batch in all_batches:
            if batch.get('current_pieces', 0) > 0:
                active_batches.append(batch)
        
        return active_batches
    
    def get_ile_groups_for_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all ile groups for a specific batch"""
        batch = self.get_by_id(batch_id)
        if not batch:
            return []
        
        return batch.get('ile_groups', [])
    
    def get_available_ile_groups(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get ile groups that are available for production or sales"""
        ile_groups = self.get_ile_groups_for_batch(batch_id)
        available = []
        
        for ile_group in ile_groups:
            if ile_group['status'] in ['raw_material', 'finished_goods'] and ile_group['remaining_pieces'] > 0:
                available.append(ile_group)
        
        return available
    
    def calculate_batch_profitability(self, batch_id: str) -> Dict[str, Any]:
        """Calculate profitability metrics for a batch"""
        batch = self.get_by_id(batch_id)
        if not batch:
            return {}
        
        total_cost = batch.get('purchase_cost', 0)
        total_pieces = batch.get('total_pieces', 0)
        remaining_pieces = batch.get('current_pieces', 0)
        sold_pieces = total_pieces - remaining_pieces
        
        # This would need to be calculated from actual sales records
        # For now, return basic metrics
        return {
            'batch_id': batch_id,
            'vendor_name': batch.get('vendor_name'),
            'total_cost': total_cost,
            'total_pieces': total_pieces,
            'sold_pieces': sold_pieces,
            'remaining_pieces': remaining_pieces,
            'cost_per_piece': total_cost / total_pieces if total_pieces > 0 else 0,
            'completion_rate': (sold_pieces / total_pieces * 100) if total_pieces > 0 else 0
        }

    def record_production(self, 
                         batch_id: str,
                         ile_number: int,
                         pieces_processed: int,
                         production_date: datetime,
                         processing_cost: float = 0.0) -> bool:
        """
        Record production process for a specific ile group
        
        Args:
            batch_id: ID of the inventory batch
            ile_number: Number of the ile group within the batch
            pieces_processed: Number of pieces processed from this ile group
            production_date: Date of production
            processing_cost: Cost of processing (labor, utilities, etc.)
        """
        batch = self.get_by_id(batch_id)
        if not batch:
            raise ValueError("Batch not found.")

        # Find the ile group
        ile_group = None
        ile_group_index = None
        for i, ig in enumerate(batch.get('ile_groups', [])):
            if ig['ile_number'] == ile_number:
                ile_group = ig
                ile_group_index = i
                break

        if not ile_group:
            raise ValueError(f"Ile group {ile_number} not found in batch {batch_id}")

        # Check if there are enough pieces
        if ile_group['remaining_pieces'] < pieces_processed:
            raise ValueError(f"Not enough pieces in Ile group {ile_number}. Available: {ile_group['remaining_pieces']}")

        # Update the ile group
        ile_group['remaining_pieces'] -= pieces_processed
        ile_group['status'] = 'in_production' if ile_group['remaining_pieces'] > 0 else 'finished_goods'
        
        if not ile_group.get('production_records'):
            ile_group['production_records'] = []
        
        # Add production record
        production_record = {
            'production_date': production_date,
            'pieces_processed': pieces_processed,
            'processing_cost': processing_cost,
            'recorded_at': datetime.now()
        }
        
        ile_group['production_records'].append(production_record)
        
        # Update the batch
        batch['ile_groups'][ile_group_index] = ile_group
        batch['current_pieces'] = sum(ig['remaining_pieces'] for ig in batch['ile_groups'])
        batch['updated_at'] = datetime.now()
        
        # Update batch status
        if batch['current_pieces'] == 0:
            batch['status'] = 'finished_goods'
        elif any(ig['status'] == 'in_production' for ig in batch['ile_groups']):
            batch['status'] = 'in_production'
        
        return self.update(batch_id, batch)
