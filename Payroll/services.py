from models import db, RawMaterial, ProductionLog, MaterialTransaction, Recipe, SystemSettings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
import datetime

class ProductionService:
    """Service layer for production operations"""
    
    @staticmethod
    def get_active_recipe():
        """Get the current active recipe"""
        recipe_items = Recipe.query.filter_by(is_active=True).all()
        if not recipe_items:
            # Fallback to default recipe if none configured
            return {
                "Wood Splints": 0.25,
                "Chemical Paste": 0.7,
                "Cardboard Sheets": 0.12,
                "Glue": 0.0
            }
        
        recipe_dict = {}
        for item in recipe_items:
            if item.material:
                recipe_dict[item.material.name] = item.quantity_per_bundle
        return recipe_dict
    
    @staticmethod
    def check_material_availability(quantity):
        """Check if sufficient materials are available for production"""
        recipe = ProductionService.get_active_recipe()
        missing_materials = []
        
        for material_name, amount_per_bundle in recipe.items():
            required_amount = amount_per_bundle * quantity
            material_db = RawMaterial.query.filter_by(name=material_name).first()
            
            if not material_db or material_db.quantity < required_amount:
                current_stock = material_db.quantity if material_db else 0
                missing_materials.append({
                    'name': material_name,
                    'required': required_amount,
                    'available': current_stock,
                    'shortage': required_amount - current_stock
                })
        
        return len(missing_materials) == 0, missing_materials
    
    @staticmethod
    def create_production(quantity, notes=None):
        """Create a new production log and deduct materials"""
        try:
            # Check material availability
            can_produce, missing_materials = ProductionService.check_material_availability(quantity)
            
            if not can_produce:
                return False, missing_materials, None
            
            # Create production log
            new_log = ProductionLog(bundles_produced=quantity, notes=notes)
            db.session.add(new_log)
            db.session.flush()  # Get the ID without committing
            
            # Deduct materials and create transaction records
            recipe = ProductionService.get_active_recipe()
            for material_name, amount_per_bundle in recipe.items():
                material_db = RawMaterial.query.filter_by(name=material_name).first()
                if material_db:
                    quantity_before = material_db.quantity
                    deduction = amount_per_bundle * quantity
                    material_db.quantity -= deduction
                    
                    # Create transaction record
                    transaction = MaterialTransaction(
                        material_id=material_db.id,
                        transaction_type='production',
                        quantity_change=-deduction,
                        quantity_before=quantity_before,
                        quantity_after=material_db.quantity,
                        production_log_id=new_log.id,
                        notes=f'Production of {quantity} bundles'
                    )
                    db.session.add(transaction)
            
            db.session.commit()
            return True, None, new_log
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, [{'error': str(e)}], None
    
    @staticmethod
    def undo_production(production_log_id):
        """Undo a production log and restore materials"""
        try:
            log = ProductionLog.query.get(production_log_id)
            if not log or log.is_deleted:
                return False, "Production log not found or already deleted"
            
            # Get all material transactions for this production
            transactions = MaterialTransaction.query.filter_by(
                production_log_id=production_log_id,
                transaction_type='production'
            ).all()
            
            # Restore materials
            for transaction in transactions:
                material = RawMaterial.query.get(transaction.material_id)
                if material:
                    quantity_before = material.quantity
                    # Reverse the deduction
                    material.quantity -= transaction.quantity_change  # quantity_change is negative, so this adds back
                    
                    # Create reversal transaction
                    reversal = MaterialTransaction(
                        material_id=material.id,
                        transaction_type='adjustment',
                        quantity_change=-transaction.quantity_change,  # Opposite of original
                        quantity_before=quantity_before,
                        quantity_after=material.quantity,
                        production_log_id=production_log_id,
                        notes=f'Reversal of production log #{production_log_id}'
                    )
                    db.session.add(reversal)
            
            # Soft delete the production log
            log.is_deleted = True
            db.session.commit()
            return True, "Production undone successfully"
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def get_production_cost(production_log_id):
        """Calculate the cost of a production run"""
        transactions = MaterialTransaction.query.filter_by(
            production_log_id=production_log_id,
            transaction_type='production'
        ).all()
        
        total_cost = 0
        for transaction in transactions:
            if transaction.material:
                # Cost = quantity used * unit price
                quantity_used = abs(transaction.quantity_change)
                total_cost += quantity_used * transaction.material.unit_price
        
        return total_cost

class InventoryService:
    """Service layer for inventory operations"""
    
    @staticmethod
    def restock_material(material_id, quantity, notes=None):
        """Add stock to a material"""
        try:
            material = RawMaterial.query.get(material_id)
            if not material:
                return False, "Material not found"
            
            quantity_before = material.quantity
            material.quantity += quantity
            
            # Create transaction record
            transaction = MaterialTransaction(
                material_id=material_id,
                transaction_type='restock',
                quantity_change=quantity,
                quantity_before=quantity_before,
                quantity_after=material.quantity,
                notes=notes or f'Restocked {quantity} {material.unit}'
            )
            db.session.add(transaction)
            db.session.commit()
            
            return True, f'Added {quantity} {material.unit} of {material.name}'
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def get_low_stock_materials(threshold=20):
        """Get materials below stock threshold"""
        return RawMaterial.query.filter(RawMaterial.quantity < threshold).all()
    
    @staticmethod
    def predict_stockout(material_id, days=30):
        """Predict when a material will run out based on recent usage"""
        material = RawMaterial.query.get(material_id)
        if not material:
            return None
        
        # Get production transactions from last 30 days
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        recent_transactions = MaterialTransaction.query.filter(
            MaterialTransaction.material_id == material_id,
            MaterialTransaction.transaction_type == 'production',
            MaterialTransaction.created_at >= thirty_days_ago
        ).all()
        
        if not recent_transactions:
            return None
        
        # Calculate average daily consumption
        total_consumed = sum(abs(t.quantity_change) for t in recent_transactions)
        avg_daily_consumption = total_consumed / 30
        
        if avg_daily_consumption == 0:
            return None
        
        # Calculate days until stockout
        days_remaining = material.quantity / avg_daily_consumption
        
        return {
            'material': material.name,
            'current_stock': material.quantity,
            'avg_daily_consumption': round(avg_daily_consumption, 2),
            'days_remaining': round(days_remaining, 1),
            'estimated_stockout_date': (datetime.date.today() + datetime.timedelta(days=days_remaining)).isoformat()
        }

class ReportService:
    """Service layer for reports and analytics"""
    
    @staticmethod
    def get_production_summary(start_date=None, end_date=None):
        """Get production summary for a date range"""
        query = ProductionLog.query.filter_by(is_deleted=False)
        
        if start_date:
            query = query.filter(ProductionLog.date >= start_date)
        if end_date:
            query = query.filter(ProductionLog.date <= end_date)
        
        logs = query.all()
        
        total_bundles = sum(log.bundles_produced for log in logs)
        total_cost = sum(ProductionService.get_production_cost(log.id) for log in logs)
        
        return {
            'total_production_runs': len(logs),
            'total_bundles': total_bundles,
            'total_cost': round(total_cost, 2),
            'avg_bundles_per_run': round(total_bundles / len(logs), 2) if logs else 0,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        }
    
    @staticmethod
    def get_material_consumption(material_id, start_date=None, end_date=None):
        """Get consumption data for a specific material"""
        query = MaterialTransaction.query.filter_by(
            material_id=material_id,
            transaction_type='production'
        )
        
        if start_date:
            query = query.filter(MaterialTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(MaterialTransaction.created_at <= end_date)
        
        transactions = query.all()
        
        total_consumed = sum(abs(t.quantity_change) for t in transactions)
        
        material = RawMaterial.query.get(material_id)
        
        return {
            'material_name': material.name if material else 'Unknown',
            'total_consumed': round(total_consumed, 2),
            'unit': material.unit if material else '',
            'transaction_count': len(transactions),
            'total_cost': round(total_consumed * material.unit_price, 2) if material else 0
        }


class ProfitService:
    """Service layer for profit and analytics (admin only)"""
    
    @staticmethod
    def get_selling_price():
        """Get selling price per bundle from settings"""
        price = SystemSettings.get('selling_price_per_bundle', '90')
        return float(price)
    
    @staticmethod
    def set_selling_price(price):
        """Set selling price per bundle"""
        SystemSettings.set('selling_price_per_bundle', str(price), 
                          'Selling price per bundle of matchboxes in INR')
    
    @staticmethod
    def get_production_profit(production_log_id):
        """Calculate profit for a single production run"""
        log = ProductionLog.query.get(production_log_id)
        if not log:
            return None
        
        cost = ProductionService.get_production_cost(production_log_id)
        selling_price = ProfitService.get_selling_price()
        revenue = log.bundles_produced * selling_price
        profit = revenue - cost
        
        return {
            'production_id': production_log_id,
            'bundles': log.bundles_produced,
            'cost': round(cost, 2),
            'revenue': round(revenue, 2),
            'profit': round(profit, 2),
            'margin': round((profit / revenue * 100), 2) if revenue > 0 else 0
        }
    
    @staticmethod
    def get_daily_analytics(days=30):
        """Get daily profit/production analytics for charts"""
        today = datetime.date.today()
        data = []
        
        selling_price = ProfitService.get_selling_price()
        
        for i in range(days - 1, -1, -1):
            day = today - datetime.timedelta(days=i)
            
            logs = ProductionLog.query.filter(
                ProductionLog.date == day,
                ProductionLog.is_deleted == False
            ).all()
            
            day_bundles = sum(log.bundles_produced for log in logs)
            day_cost = sum(ProductionService.get_production_cost(log.id) for log in logs)
            day_revenue = day_bundles * selling_price
            day_profit = day_revenue - day_cost
            
            data.append({
                'date': day.isoformat(),
                'label': day.strftime('%d %b'),
                'bundles': day_bundles,
                'cost': round(day_cost, 2),
                'revenue': round(day_revenue, 2),
                'profit': round(day_profit, 2)
            })
        
        return data
    
    @staticmethod
    def get_weekly_analytics(weeks=12):
        """Get weekly aggregated analytics"""
        today = datetime.date.today()
        data = []
        
        selling_price = ProfitService.get_selling_price()
        
        for i in range(weeks - 1, -1, -1):
            week_end = today - datetime.timedelta(days=i * 7)
            week_start = week_end - datetime.timedelta(days=6)
            
            logs = ProductionLog.query.filter(
                ProductionLog.date >= week_start,
                ProductionLog.date <= week_end,
                ProductionLog.is_deleted == False
            ).all()
            
            week_bundles = sum(log.bundles_produced for log in logs)
            week_cost = sum(ProductionService.get_production_cost(log.id) for log in logs)
            week_revenue = week_bundles * selling_price
            week_profit = week_revenue - week_cost
            
            data.append({
                'label': f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}",
                'bundles': week_bundles,
                'cost': round(week_cost, 2),
                'revenue': round(week_revenue, 2),
                'profit': round(week_profit, 2)
            })
        
        return data
    
    @staticmethod
    def get_monthly_analytics(months=12):
        """Get monthly aggregated analytics"""
        today = datetime.date.today()
        data = []
        
        selling_price = ProfitService.get_selling_price()
        
        for i in range(months - 1, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            
            logs = ProductionLog.query.filter(
                db.extract('month', ProductionLog.date) == month,
                db.extract('year', ProductionLog.date) == year,
                ProductionLog.is_deleted == False
            ).all()
            
            month_bundles = sum(log.bundles_produced for log in logs)
            month_cost = sum(ProductionService.get_production_cost(log.id) for log in logs)
            month_revenue = month_bundles * selling_price
            month_profit = month_revenue - month_cost
            
            month_name = datetime.date(year, month, 1).strftime('%b %Y')
            data.append({
                'label': month_name,
                'bundles': month_bundles,
                'cost': round(month_cost, 2),
                'revenue': round(month_revenue, 2),
                'profit': round(month_profit, 2)
            })
        
        return data
    
    @staticmethod
    def get_yearly_analytics(years=3):
        """Get yearly aggregated analytics"""
        today = datetime.date.today()
        data = []
        
        selling_price = ProfitService.get_selling_price()
        
        for i in range(years - 1, -1, -1):
            year = today.year - i
            
            logs = ProductionLog.query.filter(
                db.extract('year', ProductionLog.date) == year,
                ProductionLog.is_deleted == False
            ).all()
            
            year_bundles = sum(log.bundles_produced for log in logs)
            year_cost = sum(ProductionService.get_production_cost(log.id) for log in logs)
            year_revenue = year_bundles * selling_price
            year_profit = year_revenue - year_cost
            
            data.append({
                'label': str(year),
                'bundles': year_bundles,
                'cost': round(year_cost, 2),
                'revenue': round(year_revenue, 2),
                'profit': round(year_profit, 2)
            })
        
        return data
    
    @staticmethod
    def get_overview():
        """Get overall profit overview for dashboard"""
        today = datetime.date.today()
        selling_price = ProfitService.get_selling_price()
        
        # Today
        today_logs = ProductionLog.query.filter(
            ProductionLog.date == today, ProductionLog.is_deleted == False
        ).all()
        today_bundles = sum(l.bundles_produced for l in today_logs)
        today_cost = sum(ProductionService.get_production_cost(l.id) for l in today_logs)
        today_revenue = today_bundles * selling_price
        
        # This week
        week_start = today - datetime.timedelta(days=today.weekday())
        week_logs = ProductionLog.query.filter(
            ProductionLog.date >= week_start, ProductionLog.date <= today,
            ProductionLog.is_deleted == False
        ).all()
        week_bundles = sum(l.bundles_produced for l in week_logs)
        week_cost = sum(ProductionService.get_production_cost(l.id) for l in week_logs)
        week_revenue = week_bundles * selling_price
        
        # This month
        month_start = today.replace(day=1)
        month_logs = ProductionLog.query.filter(
            ProductionLog.date >= month_start, ProductionLog.date <= today,
            ProductionLog.is_deleted == False
        ).all()
        month_bundles = sum(l.bundles_produced for l in month_logs)
        month_cost = sum(ProductionService.get_production_cost(l.id) for l in month_logs)
        month_revenue = month_bundles * selling_price
        
        return {
            'selling_price': selling_price,
            'today': {
                'bundles': today_bundles,
                'cost': round(today_cost, 2),
                'revenue': round(today_revenue, 2),
                'profit': round(today_revenue - today_cost, 2)
            },
            'week': {
                'bundles': week_bundles,
                'cost': round(week_cost, 2),
                'revenue': round(week_revenue, 2),
                'profit': round(week_revenue - week_cost, 2)
            },
            'month': {
                'bundles': month_bundles,
                'cost': round(month_cost, 2),
                'revenue': round(month_revenue, 2),
                'profit': round(month_revenue - month_cost, 2)
            }
        }

