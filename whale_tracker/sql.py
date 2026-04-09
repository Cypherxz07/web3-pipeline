import sqlite3

conn = sqlite3.connect('whale_tracker.db')
cursor = conn.cursor()

schema = """
CREATE TABLE transfers (
    id INTEGER PRIMARY KEY,
    tx_hash TEXT UNIQUE,
    block_number INTEGER,
    timestamp INTEGER,
    from_address TEXT,
    to_address TEXT,
    token_address TEXT,
    token_symbol TEXT,
    amount TEXT,
    amount_usd REAL,
    chain TEXT DEFAULT 'ethereum',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

cursor.execute(schema)
conn.commit()
print("Database created")