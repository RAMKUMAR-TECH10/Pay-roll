from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from auth_models import User, NotificationPreference
from models import db
import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=remember)
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    """Admin creates user accounts (no public registration)"""
    if not current_user.has_permission('manage_users'):
        flash('Only admins can create user accounts.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'operator')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.create_user'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.create_user'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('auth.create_user'))
        
        # Only allow operator and viewer roles (not admin)
        if role not in ['operator', 'viewer']:
            role = 'operator'
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.create_user'))
        
        # Create user
        user = User(username=username, email=email, full_name=full_name, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create notification preferences
        prefs = NotificationPreference(user_id=user.id)
        db.session.add(prefs)
        db.session.commit()
        
        flash(f'User "{username}" created successfully as {role}!', 'success')
        return redirect(url_for('auth.users'))
    
    return render_template('auth/create_user.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile"""
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            confirm_password = request.form.get('confirm_password')
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.set_password(new_password)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Notification preferences"""
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    
    if request.method == 'POST':
        prefs.email_notifications = 'email_notifications' in request.form
        prefs.low_stock_alerts = 'low_stock_alerts' in request.form
        prefs.daily_summary = 'daily_summary' in request.form
        prefs.weekly_report = 'weekly_report' in request.form
        
        db.session.commit()
        flash('Preferences updated successfully!', 'success')
        return redirect(url_for('auth.preferences'))
    
    return render_template('auth/preferences.html', prefs=prefs)

# Admin routes
@auth_bp.route('/users')
@login_required
def users():
    """List all users (admin only)"""
    if not current_user.has_permission('manage_users'):
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    all_users = User.query.all()
    return render_template('auth/users.html', users=all_users)

@auth_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    """Toggle user active status (admin only)"""
    if not current_user.has_permission('manage_users'):
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('auth.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('auth.users'))

@auth_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_user_role(user_id):
    """Change user role (admin only)"""
    if not current_user.has_permission('manage_users'):
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['admin', 'operator', 'viewer']:
        flash('Invalid role.', 'danger')
        return redirect(url_for('auth.users'))
    
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('auth.users'))
    
    user.role = new_role
    db.session.commit()
    
    flash(f'User {user.username} role changed to {new_role}.', 'success')
    return redirect(url_for('auth.users'))
