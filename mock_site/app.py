from flask import Flask, request, render_template, redirect, url_for, jsonify
import uuid
import logging

# Suppress flask output for clean streamlit logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# In-memory database for the mock site
DATA = {
    "inventory": [
        {"id": "F101", "route": "HYD-DEL", "type": "flight", "departure": "08:00", "arrival": "10:30", "base_fare": 5000, "tax": 500, "currency": "INR", "rules": "Refundable up to 24h. 15kg baggage."},
        {"id": "F102", "route": "HYD-DEL", "type": "flight", "departure": "12:00", "arrival": "14:30", "base_fare": 4000, "tax": 500, "currency": "INR", "rules": "Non-refundable. 15kg baggage."},
        {"id": "T201", "route": "HYD-DEL", "type": "train", "departure": "18:00", "arrival": "08:00", "base_fare": 1500, "tax": 100, "currency": "INR", "rules": "Cancellation fee 100 INR. Unlimited baggage."}
    ],
    "drafts": {},      # mapping draft_id -> booking object pre-payment
    "bookings": {},    # mapping PNR -> confirmed booking object
    "config": {
        "fare_increase_active": False,
        "payment_pending_active": False
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    route = request.args.get('route', 'HYD-DEL').upper()
    mode = request.args.get('mode', 'any').lower()
    
    results = [item for item in DATA['inventory'] if item['route'] == route]
    if mode in ['flight', 'train']:
        results = [item for item in results if item['type'] == mode]
        
    return render_template('search.html', results=results, route=route)

@app.route('/book/<item_id>', methods=['GET', 'POST'])
def book(item_id):
    item = next((f for f in DATA['inventory'] if f['id'] == item_id), None)
    if not item:
        return "Item not found", 404

    if request.method == 'POST':
        pax_count = int(request.form.get('pax_count', 1))
        passengers = []
        for i in range(pax_count):
            passengers.append({
                "name": request.form.get(f'pax_name_{i}', ''),
                "age": request.form.get(f'pax_age_{i}', '')
            })
        
        draft_id = str(uuid.uuid4())
        DATA['drafts'][draft_id] = {
            "draft_id": draft_id,
            "item": item,
            "passengers": passengers,
            "status": "DRAFT"
        }
        return redirect(url_for('verify', draft_id=draft_id))
        
    return render_template('book.html', item=item)

@app.route('/verify/<draft_id>')
def verify(draft_id):
    draft = DATA['drafts'].get(draft_id)
    if not draft:
        return "Draft not found", 404
    
    base_fare = draft['item']['base_fare']
    tax = draft['item']['tax']
    
    # TC3 Simulation: Fare jumps before payment
    if DATA['config']['fare_increase_active']:
        base_fare += 2000
    
    total = (base_fare + tax) * len(draft['passengers'])
    
    return render_template('verify.html', draft=draft, base_fare=base_fare, tax=tax, total=total)

@app.route('/pay/<draft_id>', methods=['POST'])
def pay(draft_id):
    draft = DATA['drafts'].get(draft_id)
    if not draft:
        return "Draft not found", 404

    # TC4 Simulation: Payment gets stuck, no PNR generated immediately
    if DATA['config']['payment_pending_active']:
        draft['status'] = "PAYMENT_PENDING"
        return render_template('payment_pending.html', draft_id=draft_id)

    # Generate PNR and confirm
    pnr = "PNR" + str(uuid.uuid4())[:6].upper()
    DATA['bookings'][pnr] = {
        "pnr": pnr,
        "draft_id": draft_id,
        "item": draft['item'],
        "passengers": draft['passengers'],
        "status": "CONFIRMED"
    }
    draft['status'] = "CONFIRMED"
    draft['pnr'] = pnr
    
    return redirect(url_for('history'))

@app.route('/history')
def history():
    return render_template('history.html', bookings=DATA['bookings'].values())

@app.route('/admin/config', methods=['GET', 'POST'])
def admin_config():
    if request.method == 'POST':
        req = request.json
        if 'fare_increase_active' in req:
            DATA['config']['fare_increase_active'] = req['fare_increase_active']
        if 'payment_pending_active' in req:
            DATA['config']['payment_pending_active'] = req['payment_pending_active']
        return jsonify({"status": "success", "config": DATA['config']})
    return jsonify(DATA['config'])

if __name__ == '__main__':
    app.run(port=5000, threaded=True)