from typing import Optional, List, Dict
from .base import BaseModel


class ExpenseType(BaseModel):
    """Model for managing expense categories/types"""
    
    def get_collection_name(self) -> str:
        return "expense_types"
    
    def create_expense_type(self, 
                           name: str,
                           description: Optional[str] = None,
                           account_code: Optional[str] = None) -> str:
        """Create a new expense type"""
        expense_type_data = {
            'name': name,
            'description': description or '',
            'account_code': account_code or '5000',  # Default to general expenses
            'is_active': True
        }
        
        return self.create(expense_type_data)
    
    def get_active_types(self) -> List[Dict]:
        """Get all active expense types"""
        all_types = self.get_all()
        return [exp_type for exp_type in all_types if exp_type.get('is_active', True)]
    
    def update_expense_type(self, expense_type_id: str, 
                           name: Optional[str] = None,
                           description: Optional[str] = None,
                           account_code: Optional[str] = None,
                           is_active: Optional[bool] = None) -> bool:
        """Update an expense type"""
        update_data = {}
        
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if account_code is not None:
            update_data['account_code'] = account_code
        if is_active is not None:
            update_data['is_active'] = is_active
        
        return self.update(expense_type_id, update_data)
    
    def deactivate_expense_type(self, expense_type_id: str) -> bool:
        """Deactivate an expense type (soft delete)"""
        return self.update_expense_type(expense_type_id, is_active=False)
    
    def get_expense_type_by_name(self, name: str) -> Optional[Dict]:
        """Get expense type by name (case-insensitive)"""
        all_types = self.get_all()
        name_lower = name.lower().strip()
        
        for exp_type in all_types:
            if exp_type.get('name', '').lower().strip() == name_lower:
                return exp_type
        return None
