"""
Base model class for all database models
Provides common functionality for Firestore operations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.cloud import firestore
import uuid

class BaseModel(ABC):
    """Base model class with common Firestore operations"""
    
    def __init__(self, db: firestore.Client, user_id: str):
        self.db = db
        self.user_id = user_id
        self.collection_name = self.get_collection_name()
        self.collection_ref = db.collection(f"user_data_{user_id}").document("accounting").collection(self.collection_name)
    
    @abstractmethod
    def get_collection_name(self) -> str:
        """Return the Firestore collection name for this model"""
        pass
    
    def create(self, data: Dict[str, Any]) -> str:
        """Create a new document in Firestore"""
        # Add metadata
        data.update({
            'id': str(uuid.uuid4()),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'user_id': self.user_id
        })
        
        # Create document
        doc_ref = self.collection_ref.document(data['id'])
        doc_ref.set(data)
        return data['id']
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        doc_ref = self.collection_ref.document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    
    def get_all(self, filters: Optional[List[tuple]] = None, order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all documents with optional filters and ordering"""
        query = self.collection_ref
        
        # Apply filters
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        # Apply ordering
        if order_by:
            query = query.order_by(order_by)
        
        # Execute query
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update a document"""
        # Add update timestamp
        data['updated_at'] = datetime.utcnow()
        
        doc_ref = self.collection_ref.document(doc_id)
        doc_ref.update(data)
        return True
    
    def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        doc_ref = self.collection_ref.document(doc_id)
        doc_ref.delete()
        return True
    
    def exists(self, doc_id: str) -> bool:
        """Check if a document exists"""
        doc_ref = self.collection_ref.document(doc_id)
        doc = doc_ref.get()
        return doc.exists
    
    def count(self, filters: Optional[List[tuple]] = None) -> int:
        """Count documents with optional filters"""
        query = self.collection_ref
        
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        return len(list(query.stream()))
    
    def search(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """Search for documents by field value"""
        query = self.collection_ref.where(field, "==", value)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
