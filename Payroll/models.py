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
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
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
    date = db.Column(db.Date, default=datetime.date.today, nullable=False, index=True)
    bundles_produced = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Add check constraint for positive bundles
    __table_args__ = (
        db.CheckConstraint('bundles_produced > 0', name='check_bundles_positive'),
    )
    
    def __repr__(self):
        return f'<ProductionLog {self.date}: {self.bundles_produced} bundles>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'bundles_produced': self.bundles_produced,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MaterialTransaction(db.Model):
    """Track all material transactions for audit trail"""
    __tablename__ = 'material_transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'restock', 'production', 'adjustment'
    quantity_change = db.Column(db.Float, nullable=False)  # Positive for additions, negative for deductions
    quantity_before = db.Column(db.Float, nullable=False)
    quantity_after = db.Column(db.Float, nullable=False)
    production_log_id = db.Column(db.Integer, db.ForeignKey('production_log.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    
    material = db.relationship('RawMaterial', backref=db.backref('transactions', lazy='dynamic'))
    production_log = db.relationship('ProductionLog', backref=db.backref('material_transactions', lazy='dynamic'))
    
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

class Recipe(db.Model):
    """Configurable recipe for production"""
    __tablename__ = 'recipe'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False)
    quantity_per_bundle = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    material = db.relationship('RawMaterial', backref=db.backref('recipe_items', lazy='dynamic'))
    
    __table_args__ = (
        db.CheckConstraint('quantity_per_bundle > 0', name='check_recipe_quantity_positive'),
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
