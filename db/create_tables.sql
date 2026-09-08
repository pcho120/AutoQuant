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

-- ============================================================================
-- Paper Trading Accounts and Orders: Atomic simulated execution ledger
-- ============================================================================
CREATE TABLE IF NOT EXISTS paper_accounts (
    user_id TEXT PRIMARY KEY,
    cash_balance DOUBLE PRECISION NOT NULL DEFAULT 100000.0 CHECK (cash_balance >= 0),
    initial_cash DOUBLE PRECISION NOT NULL DEFAULT 100000.0 CHECK (initial_cash > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES paper_accounts(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
    requested_quantity DOUBLE PRECISION NOT NULL CHECK (requested_quantity > 0),
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    requested_price DOUBLE PRECISION,
    filled_price DOUBLE PRECISION NOT NULL CHECK (filled_price > 0),
    fee DOUBLE PRECISION NOT NULL CHECK (fee >= 0),
    quote_timestamp TIMESTAMPTZ NOT NULL,
    execution_session TEXT NOT NULL DEFAULT 'REGULAR' CHECK (execution_session IN ('REGULAR', 'CLOSED')),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS requested_quantity DOUBLE PRECISION;
UPDATE paper_orders SET requested_quantity = quantity WHERE requested_quantity IS NULL;
ALTER TABLE paper_orders ALTER COLUMN requested_quantity SET NOT NULL;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS execution_session TEXT NOT NULL DEFAULT 'REGULAR';

CREATE INDEX IF NOT EXISTS idx_paper_orders_user_executed
    ON paper_orders(user_id, executed_at DESC);

DROP FUNCTION IF EXISTS execute_paper_order(
    TEXT, TEXT, TEXT, TEXT, DOUBLE PRECISION, DOUBLE PRECISION,
    DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, TIMESTAMPTZ
);

CREATE OR REPLACE FUNCTION execute_paper_order(
    p_user_id TEXT,
    p_ticker TEXT,
    p_action TEXT,
    p_order_type TEXT,
    p_requested_quantity DOUBLE PRECISION,
    p_quantity DOUBLE PRECISION,
    p_requested_price DOUBLE PRECISION,
    p_filled_price DOUBLE PRECISION,
    p_fee_rate DOUBLE PRECISION,
    p_quote_timestamp TIMESTAMPTZ,
    p_execution_session TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    account_cash DOUBLE PRECISION;
    existing_quantity DOUBLE PRECISION;
    existing_buy_price DOUBLE PRECISION;
    trade_value DOUBLE PRECISION := p_quantity * p_filled_price;
    trade_fee DOUBLE PRECISION := trade_value * p_fee_rate;
    new_quantity DOUBLE PRECISION;
    new_buy_price DOUBLE PRECISION;
BEGIN
    IF p_action NOT IN ('BUY', 'SELL') OR p_order_type NOT IN ('MARKET', 'LIMIT')
        OR p_execution_session NOT IN ('REGULAR', 'CLOSED') THEN
        RAISE EXCEPTION 'Invalid paper order';
    END IF;
    IF p_requested_quantity <= 0 OR p_quantity <= 0 OR p_quantity > p_requested_quantity
        OR p_filled_price <= 0 OR p_fee_rate < 0 THEN
        RAISE EXCEPTION 'Invalid paper order values';
    END IF;

    INSERT INTO paper_accounts (user_id) VALUES (p_user_id)
    ON CONFLICT (user_id) DO NOTHING;

    SELECT cash_balance INTO account_cash
    FROM paper_accounts WHERE user_id = p_user_id FOR UPDATE;

    SELECT quantity, buy_price INTO existing_quantity, existing_buy_price
    FROM paper_portfolio
    WHERE user_id = p_user_id AND ticker = p_ticker
    FOR UPDATE;

    existing_quantity := COALESCE(existing_quantity, 0);
    existing_buy_price := COALESCE(existing_buy_price, 0);

    IF p_action = 'BUY' THEN
        IF account_cash < trade_value + trade_fee THEN
            RAISE EXCEPTION 'Insufficient cash';
        END IF;
        new_quantity := existing_quantity + p_quantity;
        new_buy_price := ((existing_quantity * existing_buy_price) + trade_value) / new_quantity;
        INSERT INTO paper_portfolio (user_id, ticker, quantity, buy_price, current_price)
        VALUES (p_user_id, p_ticker, new_quantity, new_buy_price, p_filled_price)
        ON CONFLICT (user_id, ticker) DO UPDATE SET
            quantity = EXCLUDED.quantity,
            buy_price = EXCLUDED.buy_price,
            current_price = EXCLUDED.current_price;
        account_cash := account_cash - trade_value - trade_fee;
    ELSE
        IF existing_quantity < p_quantity THEN
            RAISE EXCEPTION 'Insufficient quantity';
        END IF;
        new_quantity := existing_quantity - p_quantity;
        IF new_quantity = 0 THEN
            DELETE FROM paper_portfolio WHERE user_id = p_user_id AND ticker = p_ticker;
        ELSE
            UPDATE paper_portfolio
            SET quantity = new_quantity, current_price = p_filled_price
            WHERE user_id = p_user_id AND ticker = p_ticker;
        END IF;
        account_cash := account_cash + trade_value - trade_fee;
    END IF;

    UPDATE paper_accounts
    SET cash_balance = account_cash, updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id;

    INSERT INTO paper_orders (
        user_id, ticker, action, order_type, requested_quantity, quantity, requested_price,
        filled_price, fee, quote_timestamp, execution_session
    ) VALUES (
        p_user_id, p_ticker, p_action, p_order_type, p_requested_quantity, p_quantity, p_requested_price,
        p_filled_price, trade_fee, p_quote_timestamp, p_execution_session
    );

    RETURN jsonb_build_object(
        'status', 'SUCCESS',
        'remaining_cash', account_cash,
        'fee', trade_fee,
        'filled_price', p_filled_price,
        'requested_quantity', p_requested_quantity,
        'quantity', p_quantity,
        'partial_fill', p_quantity < p_requested_quantity,
        'execution_session', p_execution_session
    );
END;
$$;

-- ============================================================================
-- Market Data Collection: Raw OHLCV candles from external providers
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_prices (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    source TEXT DEFAULT 'yfinance',
    timeframe TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE market_prices ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT 'unknown';

CREATE UNIQUE INDEX IF NOT EXISTS idx_market_prices_ticker_timestamp
    ON market_prices(ticker, timestamp);
CREATE INDEX IF NOT EXISTS idx_market_prices_timestamp
    ON market_prices(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_prices_ticker_timestamp_desc
    ON market_prices(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_prices_timeframe_ticker_timestamp
    ON market_prices(timeframe, ticker, timestamp DESC);

-- ============================================================================
-- News Collection: Raw articles and separately generated structured analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_articles (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    source TEXT,
    title TEXT,
    description TEXT,
    url TEXT,
    author TEXT,
    provider_article_id TEXT,
    sentiment DOUBLE PRECISION,
    event_type TEXT,
    materiality DOUBLE PRECISION,
    impact TEXT,
    impact_horizon TEXT,
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMPTZ,
    analysis_version TEXT
);

ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS provider_article_id TEXT;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS analysis_version TEXT;

ALTER TABLE news_articles DROP CONSTRAINT IF EXISTS news_articles_url_key;
ALTER TABLE news_articles DROP CONSTRAINT IF EXISTS news_articles_provider_article_id_key;
DROP INDEX IF EXISTS idx_news_articles_url;
DROP INDEX IF EXISTS idx_news_articles_provider_id;
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_articles_ticker_url
    ON news_articles(ticker, url);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_articles_ticker_provider_id
    ON news_articles(ticker, provider_article_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_unprocessed
    ON news_articles(published_at) WHERE analyzed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_news_articles_ticker_published
    ON news_articles(ticker, published_at DESC);

-- ============================================================================
-- Prediction Features: Timestamp-safe snapshots built only from known data
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_features (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    rsi_14 DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_histogram DOUBLE PRECISION,
    sma_20 DOUBLE PRECISION,
    sma_50 DOUBLE PRECISION,
    sma_200 DOUBLE PRECISION,
    ema_12 DOUBLE PRECISION,
    ema_26 DOUBLE PRECISION,
    atr_14 DOUBLE PRECISION,
    atr_pct DOUBLE PRECISION,
    adx_14 DOUBLE PRECISION,
    bb_width DOUBLE PRECISION,
    relative_volume DOUBLE PRECISION,
    return_1d DOUBLE PRECISION,
    return_5d DOUBLE PRECISION,
    return_20d DOUBLE PRECISION,
    realized_volatility_20d DOUBLE PRECISION,
    spy_return_5d DOUBLE PRECISION,
    spy_return_20d DOUBLE PRECISION,
    qqq_return_5d DOUBLE PRECISION,
    qqq_return_20d DOUBLE PRECISION,
    sector_etf TEXT,
    sector_return_5d DOUBLE PRECISION,
    sector_return_20d DOUBLE PRECISION,
    vix DOUBLE PRECISION,
    vix_change DOUBLE PRECISION,
    market_trend TEXT,
    feature_version TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT prediction_features_snapshot_unique
        UNIQUE (ticker, timestamp, feature_version)
);

ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS rsi_14 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS macd DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS macd_signal DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS macd_histogram DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sma_20 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sma_50 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sma_200 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS ema_12 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS ema_26 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS atr_14 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS atr_pct DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS adx_14 DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS bb_width DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS relative_volume DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS return_1d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS return_5d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS return_20d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS realized_volatility_20d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS spy_return_5d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS spy_return_20d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS qqq_return_5d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS qqq_return_20d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sector_etf TEXT;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sector_return_5d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS sector_return_20d DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS vix DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS vix_change DOUBLE PRECISION;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS market_trend TEXT;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS feature_version TEXT;
ALTER TABLE prediction_features ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS idx_prediction_features_snapshot_unique
    ON prediction_features(ticker, timestamp, feature_version);

CREATE INDEX IF NOT EXISTS idx_prediction_features_ticker_timestamp
    ON prediction_features(ticker, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_features_version_timestamp
    ON prediction_features(feature_version, timestamp DESC);

-- ============================================================================
-- Model Registry: Scheduler-produced artifacts, metadata, and training bounds
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL UNIQUE,
    feature_version TEXT NOT NULL,
    horizon TEXT NOT NULL,
    classifier_name TEXT NOT NULL,
    regressor_name TEXT NOT NULL,
    calibration_method TEXT,
    artifact_base64 TEXT NOT NULL,
    training_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    trained_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_registry_horizon_trained
    ON model_registry(horizon, trained_at DESC);

-- ============================================================================
-- Predictions: Immutable, reproducible outputs served by FastAPI
-- ============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL,
    horizon TEXT NOT NULL,
    current_price DOUBLE PRECISION NOT NULL,
    expected_return DOUBLE PRECISION,
    predicted_price DOUBLE PRECISION,
    probability_up DOUBLE PRECISION,
    downside_risk DOUBLE PRECISION,
    risk_reward DOUBLE PRECISION,
    signal TEXT NOT NULL,
    reliability DOUBLE PRECISION,
    reliability_status TEXT NOT NULL,
    model_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    explanation JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT predictions_version_unique
        UNIQUE (ticker, prediction_timestamp, horizon, model_version)
);

CREATE INDEX IF NOT EXISTS idx_predictions_ticker_timestamp
    ON predictions(ticker, prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_horizon_timestamp
    ON predictions(horizon, prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_screener_return
    ON predictions(horizon, expected_return DESC, prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_screener_probability
    ON predictions(horizon, probability_up DESC, prediction_timestamp DESC);

-- ============================================================================
-- Model Evaluations: Out-of-sample walk-forward and ranking performance
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_evaluations (
    id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    horizon TEXT NOT NULL,
    train_start TIMESTAMPTZ NOT NULL,
    train_end TIMESTAMPTZ NOT NULL,
    validation_start TIMESTAMPTZ,
    validation_end TIMESTAMPTZ,
    test_start TIMESTAMPTZ NOT NULL,
    test_end TIMESTAMPTZ NOT NULL,
    sample_count INTEGER NOT NULL,
    auc DOUBLE PRECISION,
    brier_score DOUBLE PRECISION,
    log_loss DOUBLE PRECISION,
    directional_accuracy DOUBLE PRECISION,
    mae DOUBLE PRECISION,
    rmse DOUBLE PRECISION,
    top_5_mean_return DOUBLE PRECISION,
    top_10_mean_return DOUBLE PRECISION,
    top_20_mean_return DOUBLE PRECISION,
    spy_mean_return DOUBLE PRECISION,
    calibration_method TEXT,
    evaluation_details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT model_evaluations_window_unique
        UNIQUE (model_version, test_start, test_end)
);

CREATE INDEX IF NOT EXISTS idx_model_evaluations_version_created
    ON model_evaluations(model_version, created_at DESC);
