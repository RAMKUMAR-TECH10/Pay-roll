from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()


class RawMaterial(db.Model):
    """Raw material inventory model"""
    __tablename__ = 'raw_material'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    quantity = db.Column(db.Float, default=0.0, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_price = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Add check constraint for non-negative quantity
    __table_args__ = (
        db.CheckConstraint('quantity >= 0', name='check_quantity_positive'),
        db.CheckConstraint('unit_price >= 0', name='check_price_positive'),
    )

    def __repr__(self):
        return f'<RawMaterial {self.name}: {self.quantity} {self.unit}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_price': self.unit_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def stock_status(self):
        """Get stock status based on quantity"""
        if self.quantity < 20:
            return 'low'
        elif self.quantity < 50:
            return 'medium'
        else:
            return 'good'


class ProductionLog(db.Model):
    """Production log model"""
    __tablename__ = 'production_log'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False)  # Worker who made it
    supervisor_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=True)  # Supervisor overseeing
    date = db.Column(db.Date, default=datetime.date.today,
                     nullable=False, index=True)
    bundles_produced = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationships to Employee
    employee = db.relationship('Employee', foreign_keys=[
                               employee_id], backref=db.backref('produced_bundles', lazy='dynamic'))
    supervisor = db.relationship('Employee', foreign_keys=[
                                 supervisor_id], backref=db.backref('supervised_production', lazy='dynamic'))

    # Add check constraint for positive bundles
    __table_args__ = (
        db.CheckConstraint('bundles_produced > 0',
                           name='check_bundles_positive'),
    )

    def __repr__(self):
        return f'<ProductionLog {self.date}: {self.bundles_produced} bundles>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.get_full_name() if self.employee else None,
            'supervisor_id': self.supervisor_id,
            'supervisor_name': self.supervisor.get_full_name() if self.supervisor else None,
            'date': self.date.isoformat() if self.date else None,
            'bundles_produced': self.bundles_produced,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class MaterialTransaction(db.Model):
    """Track all material transactions for audit trail"""
    __tablename__ = 'material_transaction'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        'raw_material.id'), nullable=False)
    # 'restock', 'production', 'adjustment'
    transaction_type = db.Column(db.String(20), nullable=False)
    # Positive for additions, negative for deductions
    quantity_change = db.Column(db.Float, nullable=False)
    quantity_before = db.Column(db.Float, nullable=False)
    quantity_after = db.Column(db.Float, nullable=False)
    production_log_id = db.Column(
        db.Integer, db.ForeignKey('production_log.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, index=True)

    material = db.relationship(
        'RawMaterial', backref=db.backref('transactions', lazy='dynamic'))
    production_log = db.relationship('ProductionLog', backref=db.backref(
        'material_transactions', lazy='dynamic'))

    def __repr__(self):
        return f'<MaterialTransaction {self.transaction_type}: {self.quantity_change}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'material_id': self.material_id,
            'material_name': self.material.name if self.material else None,
            'transaction_type': self.transaction_type,
            'quantity_change': self.quantity_change,
            'quantity_before': self.quantity_before,
            'quantity_after': self.quantity_after,
            'production_log_id': self.production_log_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemSettings(db.Model):
    """System-wide settings (key-value store)"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @staticmethod
    def get(key, default=None):
        """Get a setting value by key"""
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set(key, value, description=None):
        """Set a setting value"""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = SystemSettings(key=key, value=str(
                value), description=description)
            db.session.add(setting)
        db.session.commit()

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'


class Recipe(db.Model):
    """Configurable recipe for production"""
    __tablename__ = 'recipe'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey(
        'raw_material.id'), nullable=False)
    quantity_per_bundle = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    material = db.relationship(
        'RawMaterial', backref=db.backref('recipe_items', lazy='dynamic'))

    __table_args__ = (
        db.CheckConstraint('quantity_per_bundle >= 0',
                           name='check_recipe_quantity_non_negative'),
    )

    def __repr__(self):
        return f'<Recipe {self.material.name if self.material else "Unknown"}: {self.quantity_per_bundle}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'material_id': self.material_id,
            'material_name': self.material.name if self.material else None,
            'quantity_per_bundle': self.quantity_per_bundle,
            'is_active': self.is_active
        }


class Employee(db.Model):
    """Employee model for payroll system"""
    __tablename__ = 'employee'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True,
                            nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    base_salary = db.Column(db.Float, default=0.0, nullable=False)
    # permanent, contract, temporary
    employment_type = db.Column(db.String(20), default='permanent')
    # active, inactive, terminated
    status = db.Column(db.String(20), default='active')
    address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    attendance_records = db.relationship(
        'Attendance', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    salary_records = db.relationship(
        'Salary', backref='employee', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint('base_salary >= 0', name='check_salary_positive'),
    )

    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.first_name} {self.last_name}>'

    def get_full_name(self):
        """Get full name"""
        return f'{self.first_name} {self.last_name}'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'position': self.position,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'base_salary': self.base_salary,
            'employment_type': self.employment_type,
            'status': self.status,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Attendance(db.Model):
    """Attendance tracking model"""
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    clock_in = db.Column(db.DateTime, nullable=True)
    clock_out = db.Column(db.DateTime, nullable=True)
    # present, absent, late, half-day, sick, leave
    status = db.Column(db.String(20), default='present')
    hours_worked = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date',
                            name='unique_employee_date'),
        db.CheckConstraint('hours_worked >= 0', name='check_hours_positive'),
    )

    def __repr__(self):
        return f'<Attendance {self.employee_id}: {self.date} - {self.status}>'

    def calculate_hours_worked(self):
        """Calculate hours worked if clock times are available"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            self.hours_worked = duration.total_seconds() / 3600  # Convert to hours
        return self.hours_worked

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.get_full_name() if self.employee else None,
            'date': self.date.isoformat() if self.date else None,
            'clock_in': self.clock_in.isoformat() if self.clock_in else None,
            'clock_out': self.clock_out.isoformat() if self.clock_out else None,
            'status': self.status,
            'hours_worked': self.hours_worked,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Salary(db.Model):
    """Salary and payroll model"""
    __tablename__ = 'salary'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False, index=True)
    month = db.Column(db.Date, nullable=False)  # First day of the month
    gross_salary = db.Column(db.Float, default=0.0, nullable=False)
    bonus = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0, nullable=False)
    # pending, paid, partial
    payment_status = db.Column(db.String(20), default='pending')
    payment_date = db.Column(db.Date, nullable=True)
    # bank transfer, cash, check
    payment_method = db.Column(db.String(50), nullable=True)
    amount_paid = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'month',
                            name='unique_employee_month'),
        db.CheckConstraint('gross_salary >= 0',
                           name='check_gross_salary_positive'),
        db.CheckConstraint('bonus >= 0', name='check_bonus_positive'),
        db.CheckConstraint('deductions >= 0',
                           name='check_deductions_positive'),
        db.CheckConstraint('tax >= 0', name='check_tax_positive'),
        db.CheckConstraint('net_salary >= 0',
                           name='check_net_salary_positive'),
    )

    def __repr__(self):
        return f'<Salary {self.employee_id}: {self.month.strftime("%Y-%m")}>'

    def calculate_net_salary(self):
        """Calculate net salary from gross, bonus, deductions and tax"""
        self.net_salary = self.gross_salary + self.bonus - self.deductions - self.tax
        if self.net_salary < 0:
            self.net_salary = 0
        return self.net_salary

    @property
    def pending_amount(self):
        """Calculate pending amount"""
        return max(0, self.net_salary - self.amount_paid)

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.get_full_name() if self.employee else None,
            'month': self.month.isoformat() if self.month else None,
            'month_display': self.month.strftime("%B %Y") if self.month else None,
            'gross_salary': self.gross_salary,
            'bonus': self.bonus,
            'deductions': self.deductions,
            'tax': self.tax,
            'net_salary': self.net_salary,
            'amount_paid': self.amount_paid,
            'pending_amount': self.pending_amount,
            'payment_status': self.payment_status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
