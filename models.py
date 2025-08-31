from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    passes = db.relationship('BusPass', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class BusPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    qr_code_data = db.Column(db.String(500), unique=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='bus_pass', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pass_id = db.Column(db.Integer, db.ForeignKey('bus_pass.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20))  # 'purchase', 'topup', 'fare_deduction'
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')  # 'completed', 'failed'

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)
    fare = db.Column(db.Float, nullable=False)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='route', lazy=True)

class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    driver_name = db.Column(db.String(100))
    current_route = db.Column(db.Integer, db.ForeignKey('route.id'))
    
    # Relationships
    transactions = db.relationship('Transaction', backref='bus', lazy=True)