from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

@app.route('/api/whales', methods=['GET'])
def get_whales():
    chain = request.args.get('chain', 'ethereum')
    min_amount = float(request.args.get('min_amount', 100000))
    
    conn = sqlite3.connect('./whale_tracker/whale_tracker.db')
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
    app.run(debug=True, port=5000)