"""
Centralized Customer Balance Service

This service provides a single source of truth for all customer balance calculations.
All parts of the application should use this service to ensure consistency.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime


class CustomerBalanceService:
    """Centralized service for customer balance calculations"""
    
    def __init__(self, models: Dict):
        self.models = models
        self.journal_entry_model = models['journal_entry']
        self.customer_deposit_model = models['customer_deposit']
    
    def get_customer_balance(self, customer_id: str) -> Dict:
        """
        Get comprehensive balance information for a customer
        
        Returns:
            {
                'opening_balance': float,
                'opening_balance_type': str,  # 'debt', 'credit', 'none'
                'total_deposits': float,
                'total_sales': float,
                'total_payments_at_sale': float,
                'current_balance': float,
                'balance_breakdown': {
                    'opening_balance': float,
                    'deposits': float,
                    'payments_at_sale': float,
                    'sales_billed': float,
                    'net_balance': float
                }
            }
        """
        try:
            # Get customer data
            customer = self._get_customer_by_id(customer_id)
            if not customer:
                return self._empty_balance_result()
            
            # Get all journal entries
            all_entries = self.journal_entry_model.get_all()
            
            # Calculate opening balance from journal entries
            opening_balance_info = self._calculate_opening_balance(customer_id, customer, all_entries)
            
            # Calculate deposits
            deposits_info = self._calculate_deposits(customer_id)
            
            # Calculate sales and payments at sale
            sales_info = self._calculate_sales_and_payments(customer_id, all_entries)
            
            # Calculate current balance
            current_balance = self._calculate_current_balance(
                opening_balance_info['amount'],
                deposits_info['total'],
                sales_info['total_sales'],
                sales_info['total_payments_at_sale']
            )
            
            return {
                'opening_balance': opening_balance_info['amount'],
                'opening_balance_type': opening_balance_info['type'],
                'total_deposits': deposits_info['total'],
                'total_sales': sales_info['total_sales'],
                'total_payments_at_sale': sales_info['total_payments_at_sale'],
                'current_balance': current_balance,
                'balance_breakdown': {
                    'opening_balance': opening_balance_info['amount'],
                    'deposits': deposits_info['total'],
                    'payments_at_sale': sales_info['total_payments_at_sale'],
                    'sales_billed': sales_info['total_sales'],
                    'net_balance': current_balance
                },
                'deposits': deposits_info['deposits'],
                'sales': sales_info['sales']
            }
            
        except Exception as e:
            print(f"Error calculating customer balance for {customer_id}: {e}")
            return self._empty_balance_result()
    
    def get_all_customers_balance(self) -> List[Dict]:
        """Get balance information for all customers"""
        try:
            customers = self.models['customer'].get_all()
            results = []
            
            for customer in customers:
                try:
                    balance_info = self.get_customer_balance(customer['id'])
                    results.append({
                        'customer': customer,
                        'balance': balance_info
                    })
                except Exception as e:
                    print(f"Error getting balance for customer {customer.get('name', 'Unknown')}: {e}")
                    # Add customer with empty balance
                    results.append({
                        'customer': customer,
                        'balance': self._empty_balance_result()
                    })
            
            return results
        except Exception as e:
            print(f"Error in get_all_customers_balance: {e}")
            return []
    
    def _get_customer_by_id(self, customer_id: str) -> Optional[Dict]:
        """Get customer by ID"""
        customers = self.models['customer'].get_all()
        for customer in customers:
            if customer['id'] == customer_id:
                return customer
        return None
    
    def _calculate_opening_balance(self, customer_id: str, customer: Dict, all_entries: List[Dict]) -> Dict:
        """Calculate opening balance from journal entries"""
        opening_balance = 0.0
        opening_balance_type = customer.get('opening_balance_type', 'none')
        
        # Search for opening balance journal entries - ONLY by customer ID reference
        for entry in all_entries:
            reference = (entry.get('reference') or '').lower()
            
            # Check if this is an opening balance entry for this specific customer
            # Only match by reference to avoid cross-contamination
            is_opening_balance_entry = f"open-{customer_id}" in reference
            
            if is_opening_balance_entry:
                for line in entry.get('entries', []):
                    if line.get('account_code') == '1200':  # Accounts Receivable
                        debit_amount = float(line.get('debit', 0) or 0)
                        credit_amount = float(line.get('credit', 0) or 0)
                        opening_balance += debit_amount - credit_amount
        
        return {
            'amount': opening_balance,
            'type': opening_balance_type
        }
    
    def _calculate_deposits(self, customer_id: str) -> Dict:
        """Calculate customer deposits"""
        deposits = self.customer_deposit_model.get_all()
        customer_deposits = [d for d in deposits if d.get('customer_id') == customer_id]
        total_deposits = sum(d.get('amount', 0) for d in customer_deposits)
        
        return {
            'deposits': customer_deposits,
            'total': total_deposits
        }
    
    def _calculate_sales_and_payments(self, customer_id: str, all_entries: List[Dict]) -> Dict:
        """Calculate sales and payments at sale from journal entries"""
        customer_sales = []
        total_sales = 0
        total_payments_at_sale = 0
        
        for entry in all_entries:
            description = entry.get('description', '')
            
            # Check if this is a sale to this customer
            if f"Sale to customer {customer_id}" in description and "Invoice" in description:
                amount = 0
                payment_at_sale = 0
                
                for line in entry.get('entries', []):
                    if line.get('account_code') == '4000':  # Revenue account
                        amount = line.get('credit', 0)
                    if line.get('account_code') in ('1000', '1100'):  # Cash/Bank accounts
                        payment_at_sale += line.get('debit', 0) or 0
                
                if amount > 0:
                    customer_sales.append({
                        'date': entry.get('date'),
                        'created_at': entry.get('created_at', entry.get('date')),
                        'amount': amount,
                        'reference': entry.get('reference', ''),
                        'description': description,
                        'payment_at_sale': payment_at_sale
                    })
                    total_sales += amount
                    total_payments_at_sale += payment_at_sale
        
        return {
            'sales': customer_sales,
            'total_sales': total_sales,
            'total_payments_at_sale': total_payments_at_sale
        }
    
    def _calculate_current_balance(self, opening_balance: float, total_deposits: float, 
                                total_sales: float, total_payments_at_sale: float) -> float:
        """
        Calculate current balance using the centralized formula:
        Current Balance = Opening Balance + Deposits + Payments at Sale - Sales Billed
        """
        return opening_balance + total_deposits + total_payments_at_sale - total_sales
    
    def _empty_balance_result(self) -> Dict:
        """Return empty balance result for error cases"""
        return {
            'opening_balance': 0.0,
            'opening_balance_type': 'none',
            'total_deposits': 0.0,
            'total_sales': 0.0,
            'total_payments_at_sale': 0.0,
            'current_balance': 0.0,
            'balance_breakdown': {
                'opening_balance': 0.0,
                'deposits': 0.0,
                'payments_at_sale': 0.0,
                'sales_billed': 0.0,
                'net_balance': 0.0
            },
            'deposits': [],
            'sales': []
        }
    
    def get_customer_balance_summary(self, customer_id: str) -> Dict:
        """
        Get a simplified balance summary for API responses
        """
        balance_info = self.get_customer_balance(customer_id)
        return {
            'customer_id': customer_id,
            'current_balance': balance_info['current_balance'],
            'opening_balance': balance_info['opening_balance'],
            'opening_balance_type': balance_info['opening_balance_type']
        }
