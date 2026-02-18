from flask import Flask
from flask_login import LoginManager
from config import config
from models import db, RawMaterial, Recipe, SystemSettings
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
    
    # Create database tables and seed data
    with app.app_context():
        db.create_all()
        seed_database()
        create_default_admin()
        seed_default_settings()
    
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
            RawMaterial(name="Wood Splints", quantity=500.0, unit="kg", unit_price=10),
            RawMaterial(name="Chemical Paste", quantity=100.0, unit="kg", unit_price=50),
            RawMaterial(name="Cardboard Sheets", quantity=1000.0, unit="pcs", unit_price=2),
            RawMaterial(name="Glue", quantity=50.0, unit="liters", unit_price=15)
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
                Recipe(material_id=wood.id, quantity_per_bundle=0.5, is_active=True),
                Recipe(material_id=chemical.id, quantity_per_bundle=0.1, is_active=True),
                Recipe(material_id=cardboard.id, quantity_per_bundle=5, is_active=True),
                Recipe(material_id=glue.id, quantity_per_bundle=0.05, is_active=True)
            ]
            db.session.add_all(seed_recipe)
            db.session.commit()
            print("Database seeded with recipe.")

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
