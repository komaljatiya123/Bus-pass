from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///buspass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0.0)

class BusPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pass_type = db.Column(db.String(50))
    valid_until = db.Column(db.DateTime)

class UsageHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    route = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize DB
@app.before_first_request
def create_tables():
    db.create_all()

# APIs

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    user = User(name=data['name'], balance=0)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered", "user_id": user.id})

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    user = User.query.get(data['user_id'])
    if user:
        user.balance += data['amount']
        db.session.commit()
        return jsonify({"message": "Top-up successful", "new_balance": user.balance})
    return jsonify({"message": "User not found"}), 404

@app.route('/buy_pass', methods=['POST'])
def buy_pass():
    data = request.json
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({"message": "User not found"}), 404

    price = 100  # Example price
    if user.balance < price:
        return jsonify({"message": "Insufficient balance"}), 400

    user.balance -= price
    bus_pass = BusPass(user_id=user.id, pass_type=data['pass_type'], valid_until=datetime.utcnow())
    db.session.add(bus_pass)
    db.session.commit()
    return jsonify({"message": "Bus pass purchased", "remaining_balance": user.balance})

@app.route('/validate_pass', methods=['POST'])
def validate_pass():
    data = request.json
    bus_pass = BusPass.query.filter_by(user_id=data['user_id']).first()
    if bus_pass:
        usage = UsageHistory(user_id=data['user_id'], route=data['route'])
        db.session.add(usage)
        db.session.commit()
        return jsonify({"message": "Pass valid", "route": data['route']})
    return jsonify({"message": "No valid pass found"}), 404

@app.route('/history/<int:user_id>', methods=['GET'])
def history(user_id):
    records = UsageHistory.query.filter_by(user_id=user_id).all()
    result = [{"route": r.route, "time": r.timestamp} for r in records]
    return jsonify(result)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
