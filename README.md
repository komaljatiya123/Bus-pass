# Smart Bus Pass System (Python Flask)

## Steps to Run

1. Install dependencies:
   pip install -r requirements.txt

2. Run the app:
   python app.py

3. Use Postman or browser to test APIs:
   - Register: POST /register { "name": "Komal" }
   - Top-up: POST /topup { "user_id": 1, "amount": 500 }
   - Buy Pass: POST /buy_pass { "user_id": 1, "pass_type": "Monthly" }
   - Validate Pass: POST /validate_pass { "user_id": 1, "route": "Route 101" }
   - Usage History: GET /history/1
