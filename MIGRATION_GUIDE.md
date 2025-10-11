# Migration Guide: From Current App to Standard Accounting Practice

## 🚀 **Migration Steps**

### **Phase 1: Backup and Preparation**
1. **Backup Current Data**
   ```bash
   # Export current Firestore data
   gcloud firestore export gs://your-bucket/backup-$(date +%Y%m%d)
   ```

2. **Install New Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### **Phase 2: Data Migration**
1. **Create Migration Script**
   ```python
   # migrate_data.py
   from src.services.accounting_service import AccountingService
   from src.models.customer import Customer
   from src.models.vendor import Vendor
   from src.models.product import Product
   
   def migrate_existing_data():
       # Migrate customers
       # Migrate vendors  
       # Migrate products
       # Convert transactions to journal entries
       pass
   ```

2. **Run Migration**
   ```bash
   python migrate_data.py
   ```

### **Phase 3: Update Templates**
1. **Update Sales Template** - Use new accounting service
2. **Update Reports** - Generate proper financial statements
3. **Update Dashboard** - Show accounting metrics

### **Phase 4: Testing**
1. **Test All Transactions**
2. **Verify Journal Entries**
3. **Check Financial Reports**
4. **Validate Data Integrity**

## 📊 **Key Changes Made**

### **1. Double-Entry Bookkeeping**
- ✅ Every transaction now has proper debits and credits
- ✅ Journal entries are balanced
- ✅ Complete audit trail

### **2. Standard Chart of Accounts**
- ✅ Assets (1000-1999)
- ✅ Liabilities (2000-2999)  
- ✅ Equity (3000-3999)
- ✅ Revenue (4000-4999)
- ✅ Expenses (5000-5999)

### **3. Proper Financial Statements**
- ✅ Profit & Loss Statement
- ✅ Balance Sheet
- ✅ Trial Balance
- ✅ Cash Flow Statement

### **4. Clean Architecture**
- ✅ Separation of concerns
- ✅ Service layer for business logic
- ✅ Model layer for data access
- ✅ Controller layer for HTTP handling

## 🔄 **Transaction Mapping**

### **Old System → New System**

| Old Transaction | New Journal Entry |
|----------------|-------------------|
| Sale | DEBIT: Cash/AR, CREDIT: Revenue + DEBIT: COGS, CREDIT: Inventory |
| Purchase | DEBIT: Inventory, CREDIT: Cash/AP |
| Deposit | DEBIT: Cash, CREDIT: AR |
| Expense | DEBIT: Expense Account, CREDIT: Cash |
| Production | DEBIT: COGS/WIP, CREDIT: Inventory + DEBIT: FG, CREDIT: WIP |

## 🎯 **Benefits of New System**

1. **Professional Accounting**: Follows GAAP standards
2. **Audit Trail**: Complete transaction history
3. **Financial Reporting**: Standard financial statements
4. **Scalability**: Can handle multiple businesses
5. **Compliance**: Meets accounting standards
6. **Maintainability**: Clean, modular code
7. **Extensibility**: Easy to add new features

## 🚨 **Important Notes**

1. **Data Backup**: Always backup before migration
2. **Testing**: Test thoroughly in development
3. **User Training**: Users need to understand new workflow
4. **Gradual Rollout**: Consider phased deployment
5. **Support**: Have support plan ready

## 📞 **Support**

For migration assistance, refer to:
- `PROJECT_STRUCTURE.md` - Architecture overview
- `src/constants/chart_of_accounts.py` - Account definitions
- `src/services/accounting_service.py` - Core business logic
