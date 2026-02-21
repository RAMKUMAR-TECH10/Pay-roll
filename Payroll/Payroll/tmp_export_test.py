import sys
sys.path.insert(0, r"Z:\Mini projects\Payroll")
from app import create_app
app = create_app('default')
with app.app_context():
    from export_service import ExportService
    print('production csv length:', len(ExportService.export_production_to_csv()))
    print('inventory csv length:', len(ExportService.export_inventory_to_csv()))
    print('transactions csv length:', len(ExportService.export_material_transactions_to_csv()))
