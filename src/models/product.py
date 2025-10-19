"""
Product Model
Manages product information and pricing
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseModel

class Product(BaseModel):
    """Model for product management"""
    
    def get_collection_name(self) -> str:
        return "products"
    
    def create_product(self, 
                      name: str,
                      description: Optional[str] = None,
                      wholesale_price: float = 0.0,
                      retail_price: float = 0.0,
                      is_active: bool = True) -> str:
        """Create a new product"""
        product_data = {
            'name': name,
            'description': description,
            'wholesale_price': wholesale_price,  # Owo price
            'retail_price': retail_price,        # Piece price
            'is_active': is_active,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return self.create(product_data)
    
    def update_product(self, product_id: str, data: Dict[str, Any]) -> bool:
        """Update product information"""
        data['updated_at'] = datetime.utcnow()
        return self.update(product_id, data)
    
    def get_active_products(self) -> List[Dict[str, Any]]:
        """Get all active products"""
        return self.search('is_active', True)
    
    
    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search products by name or description"""
        all_products = self.get_all()
        results = []
        
        query_lower = query.lower()
        for product in all_products:
            if (query_lower in product.get('name', '').lower() or
                query_lower in product.get('description', '').lower()):
                results.append(product)
        
        return results
    
    def update_pricing(self, product_id: str, wholesale_price: float, retail_price: float) -> bool:
        """Update product pricing"""
        return self.update(product_id, {
            'wholesale_price': wholesale_price,
            'retail_price': retail_price,
            'updated_at': datetime.utcnow()
        })
    
    def deactivate_product(self, product_id: str) -> bool:
        """Deactivate a product"""
        return self.update(product_id, {
            'is_active': False,
            'updated_at': datetime.utcnow()
        })
    
    def get_product_summary(self, product_id: str) -> Dict[str, Any]:
        """Get product summary information"""
        product = self.get_by_id(product_id)
        if not product:
            return {}
        
        return {
            'product_id': product_id,
            'name': product.get('name'),
            'description': product.get('description'),
            'wholesale_price': product.get('wholesale_price', 0.0),
            'retail_price': product.get('retail_price', 0.0),
            'unit_of_measure': product.get('unit_of_measure'),
            'category': product.get('category'),
            'is_active': product.get('is_active', True)
        }
