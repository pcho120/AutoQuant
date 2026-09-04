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
