"""
Alert Service for Accounting System
Provides comprehensive business alerts for various accounting scenarios
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum


class AlertType(Enum):
    """Types of alerts in the system"""
    CASH_FLOW = "cash_flow"
    INVENTORY = "inventory"
    CUSTOMER = "customer"
    VENDOR = "vendor"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertService:
    """Service for generating and managing accounting alerts"""
    
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts for the user"""
        alerts = []
        
        try:
            # Cash Flow Alerts
            alerts.extend(self._get_cash_flow_alerts())
        except Exception as e:
            print(f"Error generating cash flow alerts: {e}")
        
        try:
            # Inventory Alerts
            alerts.extend(self._get_inventory_alerts())
        except Exception as e:
            print(f"Error generating inventory alerts: {e}")
        
        try:
            # Customer Alerts
            alerts.extend(self._get_customer_alerts())
        except Exception as e:
            print(f"Error generating customer alerts: {e}")
        
        try:
            # Vendor Alerts
            alerts.extend(self._get_vendor_alerts())
        except Exception as e:
            print(f"Error generating vendor alerts: {e}")
        
        try:
            # Financial Health Alerts
            alerts.extend(self._get_financial_alerts())
        except Exception as e:
            print(f"Error generating financial alerts: {e}")
        
        try:
            # Operational Alerts
            alerts.extend(self._get_operational_alerts())
        except Exception as e:
            print(f"Error generating operational alerts: {e}")
        
        # Sort by severity and date
        alerts.sort(key=lambda x: (x['severity'].value, x['created_at']), reverse=True)
        
        return alerts
    
    def _get_cash_flow_alerts(self) -> List[Dict[str, Any]]:
        """Generate cash flow related alerts"""
        alerts = []
        
        # Import here to avoid circular imports
        from .accounting_service import AccountingService
        accounting_service = AccountingService(self.db, self.user_id)
        
        # Check cash balance
        cash_on_hand = accounting_service.get_account_balance("1000")
        bank_balance = accounting_service.get_account_balance("1100")
        total_cash = cash_on_hand + bank_balance
        
        # Low cash alert
        if total_cash < 10000:  # Less than ₦10,000
            alerts.append({
                'id': f'cash_low_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.CASH_FLOW,
                'severity': AlertSeverity.HIGH if total_cash < 5000 else AlertSeverity.MEDIUM,
                'title': 'Low Cash Balance',
                'message': f'Total cash balance is ₦{total_cash:,.2f}. Consider collecting receivables or reducing expenses.',
                'action_required': 'Review cash flow and consider immediate actions',
                'created_at': datetime.now(),
                'icon': 'fas fa-exclamation-triangle',
                'color': 'warning' if total_cash < 5000 else 'info'
            })
        
        # Negative cash alert
        if total_cash < 0:
            alerts.append({
                'id': f'cash_negative_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.CASH_FLOW,
                'severity': AlertSeverity.CRITICAL,
                'title': 'Negative Cash Balance',
                'message': f'Cash balance is negative: ₦{total_cash:,.2f}. Immediate action required!',
                'action_required': 'Urgent: Deposit funds or collect outstanding receivables',
                'created_at': datetime.now(),
                'icon': 'fas fa-exclamation-circle',
                'color': 'danger'
            })
        
        # High accounts receivable alert
        accounts_receivable = accounting_service.get_account_balance("1200")
        if accounts_receivable > total_cash * 2:  # AR is more than 2x cash
            alerts.append({
                'id': f'high_ar_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.CASH_FLOW,
                'severity': AlertSeverity.MEDIUM,
                'title': 'High Accounts Receivable',
                'message': f'Accounts Receivable (₦{accounts_receivable:,.2f}) is significantly higher than cash balance.',
                'action_required': 'Focus on collecting outstanding customer payments',
                'created_at': datetime.now(),
                'icon': 'fas fa-hand-holding-usd',
                'color': 'warning'
            })
        
        return alerts
    
    def _get_inventory_alerts(self) -> List[Dict[str, Any]]:
        """Generate inventory related alerts"""
        alerts = []
        
        from ..models.inventory_batch import InventoryBatch
        inventory_model = InventoryBatch(self.db, self.user_id)
        batches = inventory_model.get_all()
        
        # Check for old raw material batches
        old_batches = []
        for batch in batches:
            if batch.get('status') == 'raw_material':
                created_date = batch.get('created_at') or batch.get('purchase_date')
                if created_date:
                    # Handle timezone-aware datetime comparison
                    if created_date.tzinfo is not None:
                        # If created_date is timezone-aware, make now() timezone-aware too
                        from datetime import timezone
                        now = datetime.now(timezone.utc)
                    else:
                        # If created_date is naive, use naive now()
                        now = datetime.now()
                    
                    if (now - created_date).days > 30:
                        old_batches.append(batch)
        
        if old_batches:
            alerts.append({
                'id': f'old_raw_material_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.INVENTORY,
                'severity': AlertSeverity.MEDIUM,
                'title': 'Old Raw Material Inventory',
                'message': f'{len(old_batches)} batch(es) have been in raw material status for over 30 days.',
                'action_required': 'Consider processing or disposing of old inventory',
                'created_at': datetime.now(),
                'icon': 'fas fa-box-open',
                'color': 'warning'
            })
        
        # Check for low inventory levels
        total_pieces = sum(batch.get('current_pieces', 0) for batch in batches)
        if total_pieces < 1000:  # Less than 1000 pieces total
            alerts.append({
                'id': f'low_inventory_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.INVENTORY,
                'severity': AlertSeverity.MEDIUM,
                'title': 'Low Inventory Levels',
                'message': f'Total inventory is {total_pieces:,} pieces. Consider purchasing more raw materials.',
                'action_required': 'Plan inventory purchases to maintain stock levels',
                'created_at': datetime.now(),
                'icon': 'fas fa-shopping-cart',
                'color': 'info'
            })
        
        return alerts
    
    def _get_customer_alerts(self) -> List[Dict[str, Any]]:
        """Generate customer related alerts"""
        alerts = []
        
        from ..models.customer import Customer
        from ..services.customer_balance_service import CustomerBalanceService
        
        customer_model = Customer(self.db, self.user_id)
        balance_service = CustomerBalanceService(self.db, self.user_id)
        
        customers = customer_model.get_all()
        
        # Check for customers with high outstanding balances
        high_balance_customers = []
        for customer in customers:
            balance_info = balance_service.get_customer_balance_summary(customer['id'])
            if balance_info['current_balance'] < -50000:  # More than ₦50,000 debt (negative balance)
                high_balance_customers.append({
                    'name': customer['name'],
                    'balance': balance_info['current_balance']
                })
        
        if high_balance_customers:
            alerts.append({
                'id': f'high_customer_balance_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.CUSTOMER,
                'severity': AlertSeverity.MEDIUM,
                'title': 'High Customer Outstanding Balances',
                'message': f'{len(high_balance_customers)} customer(s) have outstanding balances over ₦50,000.',
                'action_required': 'Follow up with customers for payment collection',
                'created_at': datetime.now(),
                'icon': 'fas fa-users',
                'color': 'warning'
            })
        
        # Check for customers with no recent activity
        inactive_customers = []
        for customer in customers:
            # This would need to be implemented based on sales data
            # For now, we'll skip this check
            pass
        
        return alerts
    
    def _get_vendor_alerts(self) -> List[Dict[str, Any]]:
        """Generate vendor related alerts"""
        alerts = []
        
        from ..models.vendor_payment import VendorPayment
        from ..models.inventory_batch import InventoryBatch
        
        vendor_payment_model = VendorPayment(self.db, self.user_id)
        inventory_model = InventoryBatch(self.db, self.user_id)
        
        # Check for unpaid vendor invoices
        batches = inventory_model.get_all()
        unpaid_batches = []
        
        for batch in batches:
            total_paid = vendor_payment_model.get_total_paid_for_batch(batch['id'])
            purchase_cost = batch.get('purchase_cost', 0)
            outstanding = purchase_cost - total_paid
            
            if outstanding > 0:
                unpaid_batches.append({
                    'batch_id': batch['id'],
                    'vendor': batch.get('vendor_name', 'Unknown'),
                    'outstanding': outstanding
                })
        
        if unpaid_batches:
            total_outstanding = sum(batch['outstanding'] for batch in unpaid_batches)
            alerts.append({
                'id': f'unpaid_vendor_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.VENDOR,
                'severity': AlertSeverity.HIGH if total_outstanding > 100000 else AlertSeverity.MEDIUM,
                'title': 'Unpaid Vendor Invoices',
                'message': f'₦{total_outstanding:,.2f} outstanding to vendors across {len(unpaid_batches)} batch(es).',
                'action_required': 'Process vendor payments to maintain good relationships',
                'created_at': datetime.now(),
                'icon': 'fas fa-truck',
                'color': 'warning'
            })
        
        return alerts
    
    def _get_financial_alerts(self) -> List[Dict[str, Any]]:
        """Generate financial health alerts"""
        alerts = []
        
        from .accounting_service import AccountingService
        accounting_service = AccountingService(self.db, self.user_id)
        
        # Check profit margin trends (this would need historical data)
        # For now, we'll check current month performance
        
        # Check for high expenses
        total_expenses = accounting_service.get_account_balance("5400")  # Operating Expenses
        total_revenue = accounting_service.get_account_balance("4000")  # Sales Revenue
        
        if total_revenue > 0:
            expense_ratio = total_expenses / total_revenue
            if expense_ratio > 0.8:  # Expenses are more than 80% of revenue
                alerts.append({
                    'id': f'high_expense_ratio_{datetime.now().strftime("%Y%m%d")}',
                    'type': AlertType.FINANCIAL,
                    'severity': AlertSeverity.HIGH,
                    'title': 'High Expense Ratio',
                    'message': f'Operating expenses ({expense_ratio:.1%}) are very high relative to revenue.',
                    'action_required': 'Review and optimize operating expenses',
                    'created_at': datetime.now(),
                    'icon': 'fas fa-chart-line',
                    'color': 'danger'
                })
        
        return alerts
    
    def _get_operational_alerts(self) -> List[Dict[str, Any]]:
        """Generate operational alerts"""
        alerts = []
        
        # Check for recent system activity
        from ..models.journal_entry import JournalEntry
        journal_model = JournalEntry(self.db, self.user_id)
        
        # Get recent transactions (last 7 days)
        recent_date = datetime.now() - timedelta(days=7)
        recent_entries = journal_model.get_all(filters=[
            ('created_at', '>=', recent_date)
        ])
        
        if len(recent_entries) == 0:
            alerts.append({
                'id': f'no_recent_activity_{datetime.now().strftime("%Y%m%d")}',
                'type': AlertType.OPERATIONAL,
                'severity': AlertSeverity.LOW,
                'title': 'No Recent Activity',
                'message': 'No transactions recorded in the last 7 days.',
                'action_required': 'Ensure regular business operations are being recorded',
                'created_at': datetime.now(),
                'icon': 'fas fa-clock',
                'color': 'info'
            })
        
        return alerts
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss a specific alert (for future implementation)"""
        # This could store dismissed alerts in the database
        # For now, we'll just return True
        return True
    
    def get_alert_count_by_severity(self) -> Dict[str, int]:
        """Get count of alerts by severity level"""
        alerts = self.get_all_alerts()
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for alert in alerts:
            severity = alert['severity'].value
            counts[severity] += 1
        
        return counts
