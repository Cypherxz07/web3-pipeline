from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import threading

from whale_tracker.main import start_worker

db_path = os.path.join(os.path.dirname(__file__), 'whale_tracker.db')

app = Flask(__name__)
CORS(app)

worker_thread = threading.Thread(target=start_worker, daemon=True)
worker_thread.start()

@app.route('/', methods=['GET'])
def index():
    return send_from_directory(os.path.dirname(__file__), 'dashboard.html')

@app.route('/api/whales', methods=['GET'])
def get_whales():
    chain = request.args.get('chain', 'ethereum')
    min_amount = float(request.args.get('min_amount', 1))  # Default to $1, not 100k
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT tx_hash, block_number, from_address, to_address, token_symbol, amount_usd, chain
    FROM transfers
    WHERE amount_usd >= ? AND chain = ?
    ORDER BY block_number DESC
    LIMIT 100
    """, (min_amount, chain))
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

if __name__ == "__main__":
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)