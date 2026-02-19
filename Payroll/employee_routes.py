from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Employee, Attendance, Salary
from datetime import datetime, date, timedelta
import calendar

emp_bp = Blueprint('employee', __name__, url_prefix='/employees')

# ==================== EMPLOYEE MANAGEMENT ====================

@emp_bp.route('/')
@login_required
def list_employees():
    """List all employees"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        
        query = Employee.query
        if search:
            query = query.filter(
                db.or_(
                    Employee.employee_id.contains(search),
                    Employee.first_name.contains(search),
                    Employee.last_name.contains(search),
                    Employee.email.contains(search),
                    Employee.department.contains(search)
                )
            )
        
        employees = query.order_by(Employee.employee_id).paginate(page=page, per_page=20)
        total_active = Employee.query.filter_by(status='active').count()
        total_employees = Employee.query.count()
        
        return render_template('employee/list.html', 
                             employees=employees, 
                             search=search,
                             total_employees=total_employees,
                             total_active=total_active)
    except Exception as e:
        flash(f'Error loading employees: {str(e)}', 'danger')
        return render_template('employee/list.html', employees=[], search='')

@emp_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    """Add new employee"""
    if not current_user.has_permission('create'):
        flash('You do not have permission to add employees.', 'danger')
        return redirect(url_for('employee.list_employees'))
    
    if request.method == 'POST':
        try:
            # Generate employee ID
            last_employee = Employee.query.order_by(Employee.id.desc()).first()
            emp_id = f"EMP{int(last_employee.id) + 1 if last_employee else 1:04d}"
            
            employee = Employee(
                employee_id=emp_id,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                department=request.form.get('department'),
                position=request.form.get('position'),
                hire_date=datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date(),
                base_salary=float(request.form.get('base_salary', 0)),
                employment_type=request.form.get('employment_type', 'permanent'),
                address=request.form.get('address')
            )
            
            db.session.add(employee)
            db.session.commit()
            
            flash(f'Employee {emp_id} added successfully!', 'success')
            return redirect(url_for('employee.view_employee', emp_id=employee.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding employee: {str(e)}', 'danger')
    
    return render_template('employee/add.html')

@emp_bp.route('/<int:emp_id>')
@login_required
def view_employee(emp_id):
    """View employee details"""
    employee = Employee.query.get_or_404(emp_id)
    
    # Get recent attendance
    recent_attendance = Attendance.query.filter_by(employee_id=emp_id)\
        .order_by(Attendance.date.desc()).limit(30).all()
    
    # Get salary records
    salary_records = Salary.query.filter_by(employee_id=emp_id)\
        .order_by(Salary.month.desc()).limit(12).all()
    
    # Calculate statistics
    current_month = date.today().replace(day=1)
    attendance_stats = {
        'present': Attendance.query.filter(
            Attendance.employee_id == emp_id,
            Attendance.date >= current_month,
            Attendance.status == 'present'
        ).count(),
        'absent': Attendance.query.filter(
            Attendance.employee_id == emp_id,
            Attendance.date >= current_month,
            Attendance.status == 'absent'
        ).count(),
        'late': Attendance.query.filter(
            Attendance.employee_id == emp_id,
            Attendance.date >= current_month,
            Attendance.status == 'late'
        ).count()
    }
    
    return render_template('employee/view.html', 
                         employee=employee,
                         recent_attendance=recent_attendance,
                         salary_records=salary_records,
                         attendance_stats=attendance_stats)

@emp_bp.route('/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
    """Edit employee details"""
    if not current_user.has_permission('edit'):
        flash('You do not have permission to edit employees.', 'danger')
        return redirect(url_for('employee.view_employee', emp_id=emp_id))
    
    employee = Employee.query.get_or_404(emp_id)
    
    if request.method == 'POST':
        try:
            employee.first_name = request.form.get('first_name')
            employee.last_name = request.form.get('last_name')
            employee.email = request.form.get('email')
            employee.phone = request.form.get('phone')
            employee.department = request.form.get('department')
            employee.position = request.form.get('position')
            employee.hire_date = datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date()
            employee.base_salary = float(request.form.get('base_salary', 0))
            employee.employment_type = request.form.get('employment_type')
            employee.status = request.form.get('status')
            employee.address = request.form.get('address')
            
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employee.view_employee', emp_id=emp_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'danger')
    
    return render_template('employee/edit.html', employee=employee)

@emp_bp.route('/<int:emp_id>/delete', methods=['POST'])
@login_required
def delete_employee(emp_id):
    """Delete employee (soft delete)"""
    if not current_user.has_permission('delete'):
        flash('You do not have permission to delete employees.', 'danger')
        return redirect(url_for('employee.list_employees'))
    
    try:
        employee = Employee.query.get_or_404(emp_id)
        employee.status = 'terminated'
        db.session.commit()
        flash(f'Employee {employee.employee_id} terminated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error terminating employee: {str(e)}', 'danger')
    
    return redirect(url_for('employee.list_employees'))

# ==================== ATTENDANCE MANAGEMENT ====================

@emp_bp.route('/bulk-attendance', methods=['GET', 'POST'])
@login_required
def bulk_attendance():
    """Bulk mark attendance for all employees at once"""
    if not current_user.has_permission('create'):
        flash('You do not have permission to mark attendance.', 'danger')
        return redirect(url_for('employee.attendance_list'))
    
    if request.method == 'POST':
        try:
            attendance_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            
            # Get all active employees
            employees = Employee.query.filter_by(status='active').all()
            attendance_count = 0
            
            for emp in employees:
                # Get the status from form for this employee
                status_key = f'status_{emp.id}'
                status = request.form.get(status_key, 'present')
                
                # Check if already exists
                existing = Attendance.query.filter_by(
                    employee_id=emp.id,
                    date=attendance_date
                ).first()
                
                if existing:
                    # Update existing
                    existing.status = status
                    existing.notes = f"Bulk marked as {status}"
                else:
                    # Create new
                    attendance = Attendance(
                        employee_id=emp.id,
                        date=attendance_date,
                        status=status,
                        notes="Bulk marked"
                    )
                    db.session.add(attendance)
                
                if status == 'present':
                    attendance_count += 1
            
            db.session.commit()
            flash(f'Bulk attendance marked for {len(employees)} employees ({attendance_count} present).', 'success')
            return redirect(url_for('employee.bulk_attendance'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error marking bulk attendance: {str(e)}', 'danger')
    
    # GET request - show form
    attendance_date = request.args.get('date', date.today().isoformat(), type=str)
    employees = Employee.query.filter_by(status='active').order_by(Employee.last_name).all()
    
    # Get existing attendance for this date
    att_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
    existing_attendance = {}
    for att in Attendance.query.filter_by(date=att_date).all():
        existing_attendance[att.employee_id] = att.status
    
    return render_template('employee/bulk_attendance.html',
                         employees=employees,
                         attendance_date=attendance_date,
                         existing_attendance=existing_attendance)

@emp_bp.route('/attendance')
@login_required
def attendance_list():
    """List attendance records"""
    try:
        page = request.args.get('page', 1, type=int)
        emp_id = request.args.get('emp_id', '', type=int)
        from_date = request.args.get('from_date', '', type=str)
        to_date = request.args.get('to_date', '', type=str)
        
        query = Attendance.query
        
        if emp_id:
            query = query.filter_by(employee_id=emp_id)
        
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date <= to_date_obj)
        
        attendance = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=50)
        employees = Employee.query.order_by(Employee.last_name).all()
        
        return render_template('employee/attendance_list.html',
                             attendance=attendance,
                             employees=employees,
                             selected_emp_id=emp_id,
                             from_date=from_date,
                             to_date=to_date)
    except Exception as e:
        flash(f'Error loading attendance: {str(e)}', 'danger')
        return render_template('employee/attendance_list.html', attendance=[], employees=[])

@emp_bp.route('/attendance/add/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def add_attendance(emp_id):
    """Add attendance record"""
    if not current_user.has_permission('create'):
        flash('You do not have permission to add attendance.', 'danger')
        return redirect(url_for('employee.attendance_list'))
    
    employee = Employee.query.get_or_404(emp_id)
    
    if request.method == 'POST':
        try:
            attendance_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            
            # Check if attendance already exists for this date
            existing = Attendance.query.filter_by(
                employee_id=emp_id,
                date=attendance_date
            ).first()
            
            if existing:
                flash('Attendance already recorded for this date.', 'warning')
                return render_template('employee/add_attendance.html', employee=employee)
            
            attendance = Attendance(
                employee_id=emp_id,
                date=attendance_date,
                status=request.form.get('status', 'present')
            )
            
            if request.form.get('clock_in'):
                attendance.clock_in = datetime.strptime(
                    f"{attendance_date} {request.form.get('clock_in')}", 
                    '%Y-%m-%d %H:%M'
                )
            
            if request.form.get('clock_out'):
                attendance.clock_out = datetime.strptime(
                    f"{attendance_date} {request.form.get('clock_out')}", 
                    '%Y-%m-%d %H:%M'
                )
            
            attendance.notes = request.form.get('notes')
            attendance.calculate_hours_worked()
            
            db.session.add(attendance)
            db.session.commit()
            
            flash('Attendance record added successfully!', 'success')
            return redirect(url_for('employee.view_employee', emp_id=emp_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding attendance: {str(e)}', 'danger')
    
    return render_template('employee/add_attendance.html', employee=employee)

@emp_bp.route('/attendance/<int:att_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_attendance(att_id):
    """Edit attendance record"""
    if not current_user.has_permission('edit'):
        flash('You do not have permission to edit attendance.', 'danger')
        return redirect(url_for('employee.attendance_list'))
    
    attendance = Attendance.query.get_or_404(att_id)
    
    if request.method == 'POST':
        try:
            attendance.status = request.form.get('status', 'present')
            
            if request.form.get('clock_in'):
                attendance.clock_in = datetime.strptime(
                    f"{attendance.date} {request.form.get('clock_in')}", 
                    '%Y-%m-%d %H:%M'
                )
            else:
                attendance.clock_in = None
            
            if request.form.get('clock_out'):
                attendance.clock_out = datetime.strptime(
                    f"{attendance.date} {request.form.get('clock_out')}", 
                    '%Y-%m-%d %H:%M'
                )
            else:
                attendance.clock_out = None
            
            attendance.notes = request.form.get('notes')
            attendance.calculate_hours_worked()
            
            db.session.commit()
            flash('Attendance record updated successfully!', 'success')
            return redirect(url_for('employee.view_employee', emp_id=attendance.employee_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating attendance: {str(e)}', 'danger')
    
    return render_template('employee/edit_attendance.html', attendance=attendance)

# ==================== SALARY MANAGEMENT ====================

@emp_bp.route('/salary')
@login_required
def salary_list():
    """List salary records"""
    try:
        page = request.args.get('page', 1, type=int)
        emp_id = request.args.get('emp_id', '', type=int)
        status = request.args.get('status', '', type=str)
        
        query = Salary.query
        
        if emp_id:
            query = query.filter_by(employee_id=emp_id)
        
        if status:
            query = query.filter_by(payment_status=status)
        
        salary = query.order_by(Salary.month.desc()).paginate(page=page, per_page=30)
        employees = Employee.query.filter_by(status='active').order_by(Employee.last_name).all()
        
        # Get salary statistics
        total_paid = db.session.query(db.func.sum(Salary.net_salary))\
            .filter(Salary.payment_status == 'paid').scalar() or 0
        total_pending = db.session.query(db.func.sum(Salary.net_salary))\
            .filter(Salary.payment_status == 'pending').scalar() or 0
        
        return render_template('employee/salary_list.html',
                             salary=salary,
                             employees=employees,
                             selected_emp_id=emp_id,
                             selected_status=status,
                             total_paid=total_paid,
                             total_pending=total_pending)
    except Exception as e:
        flash(f'Error loading salary: {str(e)}', 'danger')
        return render_template('employee/salary_list.html', salary=[], employees=[])

@emp_bp.route('/salary/add/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def add_salary(emp_id):
    """Add salary record"""
    if not current_user.has_permission('create'):
        flash('You do not have permission to add salary records.', 'danger')
        return redirect(url_for('employee.salary_list'))
    
    employee = Employee.query.get_or_404(emp_id)
    
    if request.method == 'POST':
        try:
            month_date = datetime.strptime(request.form.get('month'), '%Y-%m').replace(day=1).date()
            
            # Check if salary already exists for this month
            existing = Salary.query.filter_by(
                employee_id=emp_id,
                month=month_date
            ).first()
            
            if existing:
                flash('Salary already recorded for this month.', 'warning')
                return render_template('employee/add_salary.html', employee=employee)
            
            salary = Salary(
                employee_id=emp_id,
                month=month_date,
                gross_salary=float(request.form.get('gross_salary', employee.base_salary)),
                bonus=float(request.form.get('bonus', 0)),
                deductions=float(request.form.get('deductions', 0)),
                tax=float(request.form.get('tax', 0)),
                payment_method=request.form.get('payment_method'),
                notes=request.form.get('notes')
            )
            
            salary.calculate_net_salary()
            
            db.session.add(salary)
            db.session.commit()
            
            flash('Salary record added successfully!', 'success')
            return redirect(url_for('employee.view_salary', salary_id=salary.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding salary record: {str(e)}', 'danger')
    
    return render_template('employee/add_salary.html', employee=employee)

@emp_bp.route('/salary/<int:salary_id>')
@login_required
def view_salary(salary_id):
    """View salary record details"""
    salary = Salary.query.get_or_404(salary_id)
    
    # Get corresponding attendance for the month
    start_date = salary.month
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == salary.employee_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date).all()
    
    return render_template('employee/view_salary.html', 
                         salary=salary,
                         attendance_records=attendance_records)

@emp_bp.route('/salary/<int:salary_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_salary(salary_id):
    """Edit salary record"""
    if not current_user.has_permission('edit'):
        flash('You do not have permission to edit salary records.', 'danger')
        return redirect(url_for('employee.salary_list'))
    
    salary = Salary.query.get_or_404(salary_id)
    
    if request.method == 'POST':
        try:
            salary.gross_salary = float(request.form.get('gross_salary', 0))
            salary.bonus = float(request.form.get('bonus', 0))
            salary.deductions = float(request.form.get('deductions', 0))
            salary.tax = float(request.form.get('tax', 0))
            salary.payment_status = request.form.get('payment_status', 'pending')
            salary.payment_method = request.form.get('payment_method')
            
            if request.form.get('payment_date'):
                salary.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
            
            salary.notes = request.form.get('notes')
            salary.calculate_net_salary()
            
            db.session.commit()
            flash('Salary record updated successfully!', 'success')
            return redirect(url_for('employee.view_salary', salary_id=salary_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating salary record: {str(e)}', 'danger')
    
    return render_template('employee/edit_salary.html', salary=salary)

@emp_bp.route('/salary/<int:salary_id>/delete', methods=['POST'])
@login_required
def delete_salary(salary_id):
    """Delete salary record"""
    if not current_user.has_permission('delete'):
        flash('You do not have permission to delete salary records.', 'danger')
        return redirect(url_for('employee.salary_list'))
    
    try:
        salary = Salary.query.get_or_404(salary_id)
        emp_id = salary.employee_id
        db.session.delete(salary)
        db.session.commit()
        flash('Salary record deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting salary record: {str(e)}', 'danger')
    
    return redirect(url_for('employee.view_employee', emp_id=emp_id))

# ==================== REPORTS ====================

@emp_bp.route('/attendance-report')
@login_required
def attendance_report():
    """Generate attendance report"""
    from_date = request.args.get('from_date', '', type=str)
    to_date = request.args.get('to_date', '', type=str)
    
    query = Attendance.query
    
    if from_date:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        query = query.filter(Attendance.date >= from_date_obj)
    
    if to_date:
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
        query = query.filter(Attendance.date <= to_date_obj)
    
    attendance_data = query.order_by(Attendance.employee_id, Attendance.date).all()
    
    # Group by employee
    employee_attendance = {}
    for record in attendance_data:
        emp = record.employee
        if emp.id not in employee_attendance:
            employee_attendance[emp.id] = {
                'employee': emp,
                'records': [],
                'present': 0,
                'absent': 0,
                'late': 0,
                'total_hours': 0
            }
        employee_attendance[emp.id]['records'].append(record)
        if record.status == 'present':
            employee_attendance[emp.id]['present'] += 1
        elif record.status == 'absent':
            employee_attendance[emp.id]['absent'] += 1
        elif record.status == 'late':
            employee_attendance[emp.id]['late'] += 1
        employee_attendance[emp.id]['total_hours'] += record.hours_worked
    
    return render_template('employee/attendance_report.html',
                         employee_attendance=employee_attendance,
                         from_date=from_date,
                         to_date=to_date)

@emp_bp.route('/payroll-report')
@login_required
def payroll_report():
    """Generate payroll report"""
    month = request.args.get('month', date.today().strftime('%Y-%m'), type=str)
    
    try:
        month_date = datetime.strptime(month, '%Y-%m').replace(day=1).date()
    except:
        month_date = date.today().replace(day=1)
    
    salary_records = Salary.query.filter_by(month=month_date).all()
    
    # Calculate totals
    total_gross = sum(s.gross_salary for s in salary_records)
    total_bonus = sum(s.bonus for s in salary_records)
    total_deductions = sum(s.deductions for s in salary_records)
    total_tax = sum(s.tax for s in salary_records)
    total_net = sum(s.net_salary for s in salary_records)
    total_paid = sum(s.net_salary for s in salary_records if s.payment_status == 'paid')
    
    return render_template('employee/payroll_report.html',
                         salary_records=salary_records,
                         month=month,
                         month_display=month_date.strftime('%B %Y'),
                         total_gross=total_gross,
                         total_bonus=total_bonus,
                         total_deductions=total_deductions,
                         total_tax=total_tax,
                         total_net=total_net,
                         total_paid=total_paid)
