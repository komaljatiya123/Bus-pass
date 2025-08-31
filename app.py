from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from models import db, User, BusPass, Transaction, Route, Bus
from config import Config
from datetime import datetime, timedelta
import qrcode
import io
import json

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)

# Create tables
with app.app_context():
    db.create_all()

# Helper function to generate QR code
def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# Routes
@app.route('/')
def home():
    return jsonify({"message": "Bus Pass System API"})

# User registration
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "User already exists"}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=data['password']  # In production, hash this password
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=new_user.id)
        
        return jsonify({
            "message": "User created successfully",
            "access_token": access_token,
            "user_id": new_user.id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# User login
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        
        if user and user.password == data['password']:  # In production, use proper password checking
            access_token = create_access_token(identity=user.id)
            return jsonify({
                "message": "Login successful",
                "access_token": access_token,
                "user_id": user.id
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create a new bus pass
@app.route('/api/passes', methods=['POST'])
@jwt_required()
def create_pass():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Check if user already has an active pass
        existing_pass = BusPass.query.filter_by(
            user_id=current_user_id, 
            is_active=True
        ).first()
        
        if existing_pass:
            return jsonify({"error": "User already has an active pass"}), 400
        
        # Create QR code data
        qr_data = json.dumps({
            "user_id": current_user_id,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Calculate expiration date (30 days from now)
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Create new pass
        new_pass = BusPass(
            user_id=current_user_id,
            balance=data.get('initial_balance', 0),
            expires_at=expires_at,
            qr_code_data=qr_data
        )
        
        db.session.add(new_pass)
        
        # Record transaction
        if data.get('initial_balance', 0) > 0:
            transaction = Transaction(
                user_id=current_user_id,
                pass_id=new_pass.id,
                amount=data.get('initial_balance', 0),
                transaction_type='purchase'
            )
            db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({
            "message": "Pass created successfully",
            "pass_id": new_pass.id,
            "balance": new_pass.balance,
            "expires_at": new_pass.expires_at.isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Top up pass balance
@app.route('/api/passes/topup', methods=['POST'])
@jwt_required()
def topup_pass():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400
        
        # Get user's active pass
        bus_pass = BusPass.query.filter_by(
            user_id=current_user_id, 
            is_active=True
        ).first()
        
        if not bus_pass:
            return jsonify({"error": "No active pass found"}), 404
        
        # Update balance
        bus_pass.balance += amount
        
        # Record transaction
        transaction = Transaction(
            user_id=current_user_id,
            pass_id=bus_pass.id,
            amount=amount,
            transaction_type='topup'
        )
        db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({
            "message": "Top-up successful",
            "new_balance": bus_pass.balance
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Validate pass (for bus conductors)
@app.route('/api/validate', methods=['POST'])
def validate_pass():
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return jsonify({"error": "QR data required"}), 400
        
        # Parse QR data
        try:
            qr_info = json.loads(qr_data)
            user_id = qr_info.get('user_id')
        except:
            return jsonify({"error": "Invalid QR code"}), 400
        
        # Get user and pass
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        bus_pass = BusPass.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not bus_pass:
            return jsonify({"error": "No active pass found"}), 404
        
        # Check if pass has expired
        if bus_pass.expires_at < datetime.utcnow():
            return jsonify({"error": "Pass has expired"}), 400
        
        # Check balance
        route_id = data.get('route_id')
        route = Route.query.get(route_id) if route_id else None
        fare = route.fare if route else 10.0  # Default fare
        
        if bus_pass.balance < fare:
            return jsonify({"error": "Insufficient balance"}), 400
        
        # Deduct fare
        bus_pass.balance -= fare
        
        # Record transaction
        transaction = Transaction(
            user_id=user_id,
            pass_id=bus_pass.id,
            amount=fare,
            transaction_type='fare_deduction',
            route_id=route_id,
            bus_id=data.get('bus_id')
        )
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            "valid": True,
            "user": user.username,
            "balance": bus_pass.balance,
            "message": "Pass validated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get user pass info
@app.route('/api/user/pass', methods=['GET'])
@jwt_required()
def get_user_pass():
    try:
        current_user_id = get_jwt_identity()
        
        bus_pass = BusPass.query.filter_by(
            user_id=current_user_id, 
            is_active=True
        ).first()
        
        if not bus_pass:
            return jsonify({"error": "No active pass found"}), 404
        
        return jsonify({
            "pass_id": bus_pass.id,
            "balance": bus_pass.balance,
            "is_active": bus_pass.is_active,
            "expires_at": bus_pass.expires_at.isoformat(),
            "created_at": bus_pass.created_at.isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get user transactions
@app.route('/api/user/transactions', methods=['GET'])
@jwt_required()
def get_user_transactions():
    try:
        current_user_id = get_jwt_identity()
        
        transactions = Transaction.query.filter_by(
            user_id=current_user_id
        ).order_by(Transaction.created_at.desc()).all()
        
        result = []
        for t in transactions:
            result.append({
                "id": t.id,
                "amount": t.amount,
                "type": t.transaction_type,
                "route_id": t.route_id,
                "bus_id": t.bus_id,
                "created_at": t.created_at.isoformat()
            })
        
        return jsonify({"transactions": result}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Generate QR code image
@app.route('/api/qrcode', methods=['GET'])
@jwt_required()
def get_qr_code():
    try:
        current_user_id = get_jwt_identity()
        
        bus_pass = BusPass.query.filter_by(
            user_id=current_user_id, 
            is_active=True
        ).first()
        
        if not bus_pass:
            return jsonify({"error": "No active pass found"}), 404
        
        qr_img = generate_qr_code(bus_pass.qr_code_data)
        return send_file(qr_img, mimetype='image/png')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Admin analytics
@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    try:
        # Total users
        total_users = User.query.count()
        
        # Active passes
        active_passes = BusPass.query.filter_by(is_active=True).count()
        
        # Total revenue
        revenue = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(['purchase', 'topup'])
        ).scalar() or 0
        
        # Recent transactions (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_transactions = Transaction.query.filter(
            Transaction.created_at >= week_ago
        ).count()
        
        return jsonify({
            "total_users": total_users,
            "active_passes": active_passes,
            "total_revenue": revenue,
            "recent_transactions": recent_transactions
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)