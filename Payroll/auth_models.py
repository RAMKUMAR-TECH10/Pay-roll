from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
import datetime

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='operator')  # admin, operator, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permissions = {
            'admin': ['view', 'create', 'edit', 'delete', 'manage_users'],
            'operator': ['view', 'create', 'edit'],
            'viewer': ['view']
        }
        return permission in permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class NotificationPreference(db.Model):
    """User notification preferences"""
    __tablename__ = 'notification_preference'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_notifications = db.Column(db.Boolean, default=True)
    low_stock_alerts = db.Column(db.Boolean, default=True)
    daily_summary = db.Column(db.Boolean, default=False)
    weekly_report = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('notification_preferences', lazy=True))
    
    def __repr__(self):
        return f'<NotificationPreference for User {self.user_id}>'
