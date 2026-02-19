from flask import Flask
from flask_login import LoginManager
from config import config
from models import db, RawMaterial, Recipe, SystemSettings, Employee, Attendance, Salary
from auth_models import User
from email_service import EmailService
import os
import threading
import time

# Initialize extensions
login_manager = LoginManager()
email_service = EmailService()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    email_service.init_app(app)
    
    # Register blueprints
    from routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    from auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    
    from employee_routes import emp_bp
    app.register_blueprint(emp_bp)
    
    # Create database tables and seed data
    with app.app_context():
        db.create_all()
        seed_database()
        create_default_admin()
        seed_default_settings()
        update_material_and_recipe_data()
        seed_sample_employees()
    
    # Start background email alert thread (for admin notifications)
    if app.config.get('EMAIL_ENABLED', False):
        start_background_alerts(app)
    
    return app

def create_default_admin():
    """Create default admin user if no users exist"""
    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@matchbox.local',
            full_name='System Administrator',
            role='admin'
        )
        admin.set_password('admin')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: username='admin', password='admin'")
        print("IMPORTANT: Change the admin password immediately!")

def seed_default_settings():
    """Seed default system settings"""
    if not SystemSettings.get('selling_price_per_bundle'):
        SystemSettings.set('selling_price_per_bundle', '25', 
                          'Selling price per bundle of matchboxes in INR')
        print("Default selling price set to Rs.25 per bundle")

def seed_database():
    """Seed initial data if database is empty"""
    # Seed raw materials
    if not RawMaterial.query.first():
        seed_materials = [
            RawMaterial(name="Wood Splints", quantity=500.0, unit="kg", unit_price=35),
            RawMaterial(name="Chemical Paste", quantity=100.0, unit="kg", unit_price=80),
            RawMaterial(name="Cardboard Sheets", quantity=1000.0, unit="kg", unit_price=46),
            RawMaterial(name="Glue", quantity=50.0, unit="kg", unit_price=130)
        ]    
        db.session.add_all(seed_materials)
        db.session.commit()
        print("Database seeded with raw materials.")
    
    # Seed recipe
    if not Recipe.query.first():
        # Get materials
        wood = RawMaterial.query.filter_by(name="Wood Splints").first()
        chemical = RawMaterial.query.filter_by(name="Chemical Paste").first()
        cardboard = RawMaterial.query.filter_by(name="Cardboard Sheets").first()
        glue = RawMaterial.query.filter_by(name="Glue").first()
        
        if wood and chemical and cardboard and glue:
            seed_recipe = [
                Recipe(material_id=wood.id, quantity_per_bundle=0.25, is_active=True),
                Recipe(material_id=chemical.id, quantity_per_bundle=0.7, is_active=True),
                Recipe(material_id=cardboard.id, quantity_per_bundle=0.12, is_active=True),
                Recipe(material_id=glue.id, quantity_per_bundle=0.0, is_active=True)
            ]
            db.session.add_all(seed_recipe)
            db.session.commit()
            print("Database seeded with recipe.")

def update_material_and_recipe_data():
    """Update existing material and recipe records to match current intended values"""
    # Correct material data: name -> (unit, unit_price)
    correct_materials = {
        "Wood Splints": ("kg", 35),
        "Chemical Paste": ("kg", 80),
        "Cardboard Sheets": ("kg", 46),
        "Glue": ("kg", 130)
    }
    
    updated = False
    for name, (unit, price) in correct_materials.items():
        material = RawMaterial.query.filter_by(name=name).first()
        if material and (material.unit != unit or material.unit_price != price):
            material.unit = unit
            material.unit_price = price
            updated = True
    
    # Correct recipe data: material_name -> quantity_per_bundle
    correct_recipe = {
        "Wood Splints": 0.25,
        "Chemical Paste": 0.7,
        "Cardboard Sheets": 0.12,
        "Glue": 0.0
    }
    
    for material_name, qty in correct_recipe.items():
        material = RawMaterial.query.filter_by(name=material_name).first()
        if material:
            recipe_item = Recipe.query.filter_by(material_id=material.id, is_active=True).first()
            if recipe_item and recipe_item.quantity_per_bundle != qty:
                recipe_item.quantity_per_bundle = qty
                updated = True
    
    if updated:
        db.session.commit()
        print("Material and recipe data updated to match current values.")

def seed_sample_employees():
    """Seed sample employee, attendance, and salary data for prototype/demo purposes"""
    from datetime import datetime, timedelta, date
    
    # Check if employees already exist
    if Employee.query.count() > 0:
        return
    
    # Sample employee data
    sample_employees = [
        {
            'employee_id': 'EMP0001',
            'first_name': 'Rajesh',
            'last_name': 'Kumar',
            'email': 'rajesh.kumar@matchbox.com',
            'phone': '9876543210',
            'department': 'Production',
            'position': 'Machine Operator',
            'hire_date': date(2023, 1, 15),
            'base_salary': 28000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0002',
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'email': 'priya.sharma@matchbox.com',
            'phone': '9876543211',
            'department': 'Quality',
            'position': 'Quality Inspector',
            'hire_date': date(2022, 6, 20),
            'base_salary': 26000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0003',
            'first_name': 'Amit',
            'last_name': 'Patel',
            'email': 'amit.patel@matchbox.com',
            'phone': '9876543212',
            'department': 'Production',
            'position': 'Supervisor',
            'hire_date': date(2021, 3, 10),
            'base_salary': 35000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0004',
            'first_name': 'Deepika',
            'last_name': 'Singh',
            'email': 'deepika.singh@matchbox.com',
            'phone': '9876543213',
            'department': 'Packaging',
            'position': 'Packing Operator',
            'hire_date': date(2023, 5, 12),
            'base_salary': 24000,
            'employment_type': 'contract',
        },
        {
            'employee_id': 'EMP0005',
            'first_name': 'Vikram',
            'last_name': 'Gupta',
            'email': 'vikram.gupta@matchbox.com',
            'phone': '9876543214',
            'department': 'Production',
            'position': 'Machine Technician',
            'hire_date': date(2020, 8, 5),
            'base_salary': 32000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0006',
            'first_name': 'Anjali',
            'last_name': 'Desai',
            'email': 'anjali.desai@matchbox.com',
            'phone': '9876543215',
            'department': 'Quality',
            'position': 'QA Analyst',
            'hire_date': date(2022, 9, 15),
            'base_salary': 27000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0007',
            'first_name': 'Suresh',
            'last_name': 'Reddy',
            'email': 'suresh.reddy@matchbox.com',
            'phone': '9876543216',
            'department': 'Packaging',
            'position': 'Lead Operator',
            'hire_date': date(2021, 11, 22),
            'base_salary': 31000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0008',
            'first_name': 'Neha',
            'last_name': 'Verma',
            'email': 'neha.verma@matchbox.com',
            'phone': '9876543217',
            'department': 'Production',
            'position': 'Machine Operator',
            'hire_date': date(2023, 2, 28),
            'base_salary': 25000,
            'employment_type': 'contract',
        },
        {
            'employee_id': 'EMP0009',
            'first_name': 'Mohan',
            'last_name': 'Kumar',
            'email': 'mohan.kumar@matchbox.com',
            'phone': '9876543218',
            'department': 'Maintenance',
            'position': 'Maintenance Engineer',
            'hire_date': date(2020, 4, 10),
            'base_salary': 33000,
            'employment_type': 'permanent',
        },
        {
            'employee_id': 'EMP0010',
            'first_name': 'Sneha',
            'last_name': 'Joshi',
            'email': 'sneha.joshi@matchbox.com',
            'phone': '9876543219',
            'department': 'Quality',
            'position': 'Quality Checker',
            'hire_date': date(2023, 7, 30),
            'base_salary': 23000,
            'employment_type': 'temporary',
        },
    ]
    
    # Create employees
    created_employees = []
    for emp_data in sample_employees:
        employee = Employee(**emp_data)
        db.session.add(employee)
        created_employees.append(employee)
    
    db.session.commit()
    print(f"Created {len(created_employees)} sample employees")
    
    # Create attendance records for last 30 days
    base_date = date.today() - timedelta(days=30)
    attendance_statuses = ['present', 'present', 'present', 'present', 'absent', 'late', 'leave']
    
    attendance_records = []
    for emp in created_employees:
        for i in range(30):
            current_date = base_date + timedelta(days=i)
            # Skip weekends
            if current_date.weekday() >= 5:
                continue
            
            status = attendance_statuses[i % len(attendance_statuses)]
            
            # Create clock in/out times for present and late statuses
            clock_in = None
            clock_out = None
            hours_worked = 0
            
            if status in ['present', 'late']:
                if status == 'present':
                    clock_in = datetime.combine(current_date, datetime.strptime('09:00', '%H:%M').time())
                else:  # late
                    clock_in = datetime.combine(current_date, datetime.strptime('10:30', '%H:%M').time())
                
                clock_out = datetime.combine(current_date, datetime.strptime('17:30', '%H:%M').time())
                hours_worked = 8.0 if status == 'present' else 7.0
            
            attendance = Attendance(
                employee_id=emp.id,
                date=current_date,
                status=status,
                clock_in=clock_in,
                clock_out=clock_out,
                hours_worked=hours_worked
            )
            attendance_records.append(attendance)
            db.session.add(attendance)
    
    db.session.commit()
    print(f"Created attendance records for {len(created_employees)} employees")
    
    # Create salary records for last 3 months
    current_month = date.today().replace(day=1)
    for emp in created_employees:
        for month_offset in range(3):
            salary_month = current_month - timedelta(days=month_offset * 30)
            salary_month = salary_month.replace(day=1)
            
            # Calculate bonus based on attendance
            start_date = salary_month
            end_date = (salary_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            attendance_count = Attendance.query.filter(
                Attendance.employee_id == emp.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).count()
            
            # Attendance bonus
            bonus = (attendance_count / 20) * 1000 if attendance_count >= 18 else 0
            
            salary = Salary(
                employee_id=emp.id,
                month=salary_month,
                gross_salary=emp.base_salary,
                bonus=bonus,
                deductions=emp.base_salary * 0.05,  # 5% deductions
                tax=emp.base_salary * 0.10,  # 10% tax
                payment_status='paid' if month_offset > 0 else 'pending',
                payment_method='bank_transfer',
                payment_date=start_date + timedelta(days=5) if month_offset > 0 else None
            )
            salary.calculate_net_salary()
            db.session.add(salary)
    
    db.session.commit()
    print(f"Created salary records for {len(created_employees)} employees")

def start_background_alerts(app):
    """Start a background thread to send periodic email alerts to admin"""
    def alert_loop():
        while True:
            try:
                with app.app_context():
                    # Check for low stock and send alerts
                    from services import InventoryService
                    low_stock = InventoryService.get_low_stock_materials(threshold=20)
                    
                    if low_stock:
                        admin_users = User.query.filter_by(role='admin', is_active=True).all()
                        admin_emails = [u.email for u in admin_users if u.email and '@' in u.email]
                        
                        if admin_emails:
                            email_service.check_and_send_low_stock_alerts(admin_emails)
                            print(f"Low stock alerts sent to: {', '.join(admin_emails)}")
                    
                    # Send daily summary at end of day (simplified: runs every cycle)
                    admin_email = app.config.get('ADMIN_EMAIL', '')
                    if admin_email:
                        # Just log it - actual email sending happens via EmailService
                        print(f"Background alert check complete. Admin: {admin_email}")
                        
            except Exception as e:
                print(f"Background alert error: {e}")
            
            # Check every 6 hours
            time.sleep(6 * 60 * 60)
    
    thread = threading.Thread(target=alert_loop, daemon=True)
    thread.start()
    print("Background email alert thread started")

if __name__ == '__main__':
    # Get environment (default to development)
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Ensure instance folder exists
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    app = create_app(env)
    app.run(debug=True)
