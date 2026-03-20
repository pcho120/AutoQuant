-- AutoQuant Database Schema: Portfolio and Paper Trading Tables
-- This script creates two identical table structures for portfolio management:
-- 1. 'portfolio' - Tracks real portfolio positions (primary)
-- 2. 'paper_portfolio' - Tracks paper trading simulation positions (separate sandbox)
--
-- EXECUTION GUIDE:
-- 1. Navigate to Supabase Dashboard: https://app.supabase.com/
-- 2. Select your AutoQuant project
-- 3. Go to SQL Editor (left sidebar)
-- 4. Create a new SQL script
-- 5. Copy and paste this entire file content
-- 6. Click "Run" button (or press Ctrl+Enter)
-- 7. Both tables will be created with proper indexes automatically
--
-- NOTE: These statements are idempotent (IF NOT EXISTS) and safe to re-run.

-- ============================================================================
-- Portfolio Table: Stores real portfolio positions
-- ============================================================================
CREATE TABLE IF NOT EXISTS portfolio (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    quantity FLOAT NOT NULL,
    buy_price FLOAT NOT NULL,
    current_price FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT portfolio_user_ticker_unique UNIQUE (user_id, ticker)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker);

-- ============================================================================
-- Paper Portfolio Table: Stores paper trading simulation positions
-- ============================================================================
CREATE TABLE IF NOT EXISTS paper_portfolio (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    quantity FLOAT NOT NULL,
    buy_price FLOAT NOT NULL,
    current_price FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT paper_portfolio_user_ticker_unique UNIQUE (user_id, ticker)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_paper_portfolio_user_id ON paper_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_portfolio_ticker ON paper_portfolio(ticker);
