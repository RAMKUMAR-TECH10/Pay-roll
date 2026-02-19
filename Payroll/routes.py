from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, RawMaterial, ProductionLog, MaterialTransaction, Recipe, Employee
from services import ProductionService, InventoryService, ReportService, ProfitService
import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def dashboard():
    """Dashboard with overview statistics"""
    today = datetime.date.today()
    try:
        raw_materials = RawMaterial.query.all()
        
        # Production today
        production_today = db.session.query(db.func.sum(ProductionLog.bundles_produced))\
            .filter(ProductionLog.date == today, ProductionLog.is_deleted == False)\
            .scalar() or 0
        
        # Weekly Production Data for Chart
        weekly_production = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_total = db.session.query(db.func.sum(ProductionLog.bundles_produced))\
                .filter(ProductionLog.date == day, ProductionLog.is_deleted == False)\
                .scalar() or 0
            weekly_production.append({'day': day.strftime('%a'), 'total': day_total})
        
        # Get low stock alerts
        low_stock_materials = InventoryService.get_low_stock_materials()
        
        # Get profit overview for admin
        profit_overview = None
        if current_user.role == 'admin':
            profit_overview = ProfitService.get_overview()

    except Exception as e:
        print(f"Error loading dashboard: {e}")
        raw_materials = []
        production_today = 0
        weekly_production = []
        low_stock_materials = []
        profit_overview = None
    
    return render_template('dashboard.html', 
                         raw_materials=raw_materials,
                         production_today=production_today,
                         weekly_production=weekly_production,
                         low_stock_materials=low_stock_materials,
                         profit_overview=profit_overview)

@bp.route('/production', methods=['GET', 'POST'])
@login_required
def production():
    """Production logging page - Workers create, Supervisors verify"""
    if request.method == 'POST':
        try:
            quantity = int(request.form.get('quantity'))
            employee_id_str = request.form.get('employee_id', '').strip()
            supervisor_id_str = request.form.get('supervisor_id', '').strip()
            employee_id = int(employee_id_str) if employee_id_str else None
            supervisor_id = int(supervisor_id_str) if supervisor_id_str else None
            notes = request.form.get('notes', '').strip() or None
            
            if quantity <= 0:
                flash('Quantity must be greater than 0.', 'danger')
                return redirect(url_for('main.production'))
            
            # Validate that employee is a Worker
            if not employee_id:
                flash('Please select a worker.', 'danger')
                return redirect(url_for('main.production'))
            
            worker = Employee.query.get(employee_id)
            if not worker or worker.position != 'Worker':
                flash('Only Workers can log production. Please select a Worker.', 'danger')
                return redirect(url_for('main.production'))
            
            # Optional: Validate supervisor is actually a Supervisor (if provided)
            if supervisor_id:
                supervisor = Employee.query.get(supervisor_id)
                if not supervisor or supervisor.position != 'Supervisor':
                    flash('Supervisor must have Supervisor position.', 'danger')
                    return redirect(url_for('main.production'))
            
            # Use service layer for production (only deducts materials for workers)
            success, error_data, production_log = ProductionService.create_production(quantity, notes)
            
            if success:
                # Assign worker and supervisor
                if production_log:
                    production_log.employee_id = employee_id
                    production_log.supervisor_id = supervisor_id
                    db.session.commit()
                flash(f'Successfully logged {quantity} bundles by {worker.get_full_name()}!', 'success')
                    db.session.commit()
                flash(f'Successfully produced {quantity} bundles!', 'success')
            else:
                if error_data and isinstance(error_data, list):
                    missing_info = ', '.join([
                        f"{m['name']} (Need: {m['required']}, Have: {m['available']})" 
                        for m in error_data if 'name' in m
                    ])
                    flash(f"Production Failed: Not enough materials! Missing: {missing_info}", 'danger')
                else:
                    flash('Production failed due to an error.', 'danger')
                    
        except ValueError as ve:
            flash('Invalid input. Please check quantity and employee selection.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('main.production'))
    
    # GET request - show form and recent logs
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        pagination = ProductionLog.query.filter_by(is_deleted=False)\
            .order_by(ProductionLog.date.desc(), ProductionLog.id.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        # Fetch active recipe for display
        recipe = ProductionService.get_active_recipe()
        recipe_display = []
        for material_name, qty in recipe.items():
            material = RawMaterial.query.filter_by(name=material_name).first()
            if material:
                recipe_display.append({
                    'name': material_name,
                    'quantity': qty,
                    'unit': material.unit
                })
        
        # Get active employees
        employees = Employee.query.filter_by(status='active').order_by(Employee.last_name).all()
        
        return render_template('production.html', 
                             logs=pagination.items,
                             pagination=pagination,
                             recipe=recipe_display,
                             employees=employees)
    except Exception as e:
        flash(f'Error loading production page: {str(e)}', 'danger')
        return render_template('production.html', 
                             logs=[],
                             pagination=None,
                             recipe=[],
                             employees=[])

@bp.route('/production/undo/<int:id>', methods=['POST'])
@login_required
def undo_production(id):
    """Undo a production log"""
    success, message = ProductionService.undo_production(id)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'danger')
    
    return redirect(url_for('main.production'))

@bp.route('/production/delete/<int:id>')
@login_required
def delete_production(id):
    """Delete (soft delete) a production log"""
    try:
        log = ProductionLog.query.get_or_404(id)
        log.is_deleted = True
        db.session.commit()
        flash('Production log deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting log: {str(e)}', 'danger')
    
    return redirect(url_for('main.production'))

@bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    """Inventory management page"""
    if request.method == 'POST':
        material_id = request.form.get('material_id')
        try:
            added_quantity = float(request.form.get('quantity'))
            notes = request.form.get('notes', '').strip() or None
            
            if added_quantity <= 0:
                flash('Quantity must be greater than 0.', 'danger')
                return redirect(url_for('main.inventory'))
            
            success, message = InventoryService.restock_material(material_id, added_quantity, notes)
            
            if success:
                flash(message, 'success')
            else:
                flash(f'Error: {message}', 'danger')
                
        except ValueError:
            flash('Invalid quantity.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            
        return redirect(url_for('main.inventory'))
    
    raw_materials = RawMaterial.query.all()
    return render_template('inventory.html', raw_materials=raw_materials)

@bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    try:
        # Get date range from query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            # If date parsing fails, use default
            pass
        
        # Default to last 30 days if no dates provided
        if not start_date and not end_date:
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=30)
        
        production_summary = ReportService.get_production_summary(start_date, end_date)
        
        # Get material consumption for all materials
        materials = RawMaterial.query.all()
        material_consumption = []
        for material in materials:
            consumption = ReportService.get_material_consumption(material.id, start_date, end_date)
            if consumption['total_consumed'] > 0:
                material_consumption.append(consumption)
        
        return render_template('reports.html',
                             production_summary=production_summary,
                             material_consumption=material_consumption,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        # Return default report for last 30 days
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        production_summary = ReportService.get_production_summary(start_date, end_date)
        materials = RawMaterial.query.all()
        material_consumption = []
        for material in materials:
            consumption = ReportService.get_material_consumption(material.id, start_date, end_date)
            if consumption['total_consumed'] > 0:
                material_consumption.append(consumption)
        
        return render_template('reports.html',
                             production_summary=production_summary,
                             material_consumption=material_consumption,
                             start_date=start_date,
                             end_date=end_date)

# Export Routes

@bp.route('/export/production/csv')
@login_required
def export_production_csv():
    """Export production logs to CSV"""
    from export_service import ExportService
    from flask import make_response
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    csv_data = ExportService.export_production_to_csv(start_date, end_date)
    
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=production_logs_{datetime.date.today()}.csv'
    
    return response

@bp.route('/export/inventory/csv')
@login_required
def export_inventory_csv():
    """Export inventory to CSV"""
    from export_service import ExportService
    from flask import make_response
    
    csv_data = ExportService.export_inventory_to_csv()
    
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_{datetime.date.today()}.csv'
    
    return response

@bp.route('/export/transactions/csv')
@login_required
def export_transactions_csv():
    """Export material transactions to CSV"""
    from export_service import ExportService
    from flask import make_response
    
    material_id = request.args.get('material_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    csv_data = ExportService.export_material_transactions_to_csv(material_id, start_date, end_date)
    
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=transactions_{datetime.date.today()}.csv'
    
    return response

@bp.route('/export/production/pdf')
@login_required
def export_production_pdf():
    """Export production report to PDF"""
    from export_service import ExportService
    from flask import make_response
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    pdf_data = ExportService.export_production_report_to_pdf(start_date, end_date)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=production_report_{datetime.date.today()}.pdf'
    
    return response

@bp.route('/export/inventory/pdf')
@login_required
def export_inventory_pdf():
    """Export inventory report to PDF"""
    from export_service import ExportService
    from flask import make_response
    
    pdf_data = ExportService.export_inventory_report_to_pdf()
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_report_{datetime.date.today()}.pdf'
    
    return response

# API Routes for AJAX/JSON responses

@bp.route('/api/materials')
@login_required
def api_materials():
    """Get all materials as JSON"""
    materials = RawMaterial.query.all()
    return jsonify([m.to_dict() for m in materials])

@bp.route('/api/materials/<int:id>')
@login_required
def api_material(id):
    """Get a specific material"""
    material = RawMaterial.query.get_or_404(id)
    return jsonify(material.to_dict())

@bp.route('/api/production')
@login_required
def api_production():
    """Get production logs as JSON"""
    logs = ProductionLog.query.filter_by(is_deleted=False)\
        .order_by(ProductionLog.date.desc())\
        .limit(100)\
        .all()
    return jsonify([log.to_dict() for log in logs])

@bp.route('/api/production/<int:id>/cost')
@login_required
def api_production_cost(id):
    """Get cost of a production run"""
    cost = ProductionService.get_production_cost(id)
    return jsonify({'production_id': id, 'cost': round(cost, 2)})

@bp.route('/api/materials/<int:id>/stockout-prediction')
@login_required
def api_stockout_prediction(id):
    """Get stockout prediction for a material"""
    prediction = InventoryService.predict_stockout(id)
    if prediction:
        return jsonify(prediction)
    else:
        return jsonify({'error': 'Unable to predict stockout'}), 404

# === ADMIN-ONLY: Analytics & Profit Routes ===

@bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard with charts (admin only)"""
    if current_user.role != 'admin':
        flash('Only admins can access analytics.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    overview = ProfitService.get_overview()
    return render_template('analytics.html', overview=overview)

@bp.route('/analytics/settings', methods=['POST'])
@login_required
def analytics_settings():
    """Update analytics settings like selling price (admin only)"""
    if current_user.role != 'admin':
        flash('Only admins can change settings.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    selling_price = request.form.get('selling_price', type=float)
    if selling_price and selling_price > 0:
        ProfitService.set_selling_price(selling_price)
        flash(f'Selling price updated to Rs.{selling_price} per bundle.', 'success')
    else:
        flash('Invalid selling price.', 'danger')
    
    return redirect(url_for('main.analytics'))

@bp.route('/api/analytics/daily')
@login_required
def api_analytics_daily():
    """Daily analytics data (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    days = request.args.get('days', 7, type=int)
    return jsonify(ProfitService.get_daily_analytics(days))

@bp.route('/api/analytics/weekly')
@login_required
def api_analytics_weekly():
    """Weekly analytics data (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    weeks = request.args.get('weeks', 12, type=int)
    return jsonify(ProfitService.get_weekly_analytics(weeks))

@bp.route('/api/analytics/monthly')
@login_required
def api_analytics_monthly():
    """Monthly analytics data (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    months = request.args.get('months', 12, type=int)
    return jsonify(ProfitService.get_monthly_analytics(months))

@bp.route('/api/analytics/yearly')
@login_required
def api_analytics_yearly():
    """Yearly analytics data (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    years = request.args.get('years', 3, type=int)
    return jsonify(ProfitService.get_yearly_analytics(years))

@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('errors/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500
