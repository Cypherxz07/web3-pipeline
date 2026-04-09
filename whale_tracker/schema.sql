CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    tx_hash VARCHAR(255) UNIQUE NOT NULL,
    block_number BIGINT NOT NULL,
    timestamp BIGINT NOT NULL,
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    token_address VARCHAR(255) NOT NULL,
    token_symbol VARCHAR(20),
    amount DECIMAL(38, 18),
    amount_usd DECIMAL(18, 2),
    chain VARCHAR(50) DEFAULT 'ethereum',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX(timestamp),
    INDEX(token_address),
    INDEX(from_address)
);