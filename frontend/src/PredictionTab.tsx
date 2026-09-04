import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BrainCircuit, Newspaper, Search, ShieldAlert, Target, TrendingUp } from 'lucide-react'
import { PredictionHelp } from './AnalysisHelp'
import { fetchJson } from './api'
import { TickerSearch } from './TickerSearch'

type SortMode = 'expected_return' | 'probability_up'
type Explanation = {
  bullish_factors?: string[]
  risk_factors?: string[]
  technical?: Record<string, number | null>
  market_regime?: Record<string, number | string | null>
}
type NewsArticle = {
  published_at: string
  source?: string
  title?: string
  url?: string
  sentiment?: number
  event_type?: string
  materiality?: number
}
type Prediction = {
  ticker: string
  horizon: '5d'
  predictionTimestamp: string
  currentPrice: number
  expectedReturn: number | null
  predictedPrice: number | null
  probabilityUp: number | null
  downsideRisk: number | null
  riskReward: number | null
  signal: 'BUY' | 'HOLD' | 'SELL'
  modelReliability: number | null
  reliabilityStatus: string
  modelVersion: string
  featureVersion: string
  stale: boolean
  explanation: Explanation
  recentNews: NewsArticle[]
}

const money = (value: number | null) => value == null ? 'Unavailable' : value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
const percent = (value: number | null, signed = false) => value == null ? 'Unavailable' : `${signed && value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
const metric = (value: number | string | null | undefined) => typeof value === 'number' ? value.toFixed(3) : value ?? 'Unavailable'

export function PredictionTab() {
  const [ticker, setTicker] = useState('')
  const [analyzedTicker, setAnalyzedTicker] = useState('')
  const [sort, setSort] = useState<SortMode>('expected_return')

  const screener = useQuery({
    queryKey: ['prediction-screener', sort],
    queryFn: () => fetchJson<{ results: Prediction[] }>(`/api/predictions/screener?sort=${sort}&horizon=5d&limit=20`),
  })
  const detail = useQuery({
    queryKey: ['prediction-detail', analyzedTicker],
    queryFn: () => fetchJson<Prediction>(`/api/predictions/${encodeURIComponent(analyzedTicker)}?horizon=5d`),
    enabled: Boolean(analyzedTicker),
    retry: false,
  })
  const result = detail.data

  const analyze = () => {
    const normalized = ticker.trim().toUpperCase()
    if (normalized === analyzedTicker) void detail.refetch()
    else setAnalyzedTicker(normalized)
  }

  return (
    <main className="feature-page">
      <section className="feature-heading prediction-heading">
        <div><span className="feature-kicker">Validated market intelligence</span><h1>AI Prediction</h1><p>Five-trading-day forecasts calculated offline from timestamp-safe market data and served from Supabase.</p></div>
        <div className="feature-heading-tools"><div className="model-badge"><BrainCircuit size={20} /><span>Production model<strong>Calibrated probability · independent return model</strong></span></div><PredictionHelp /></div>
      </section>

      <section className="prediction-command feature-card">
        <div className="prediction-inputs"><TickerSearch label="Individual stock" value={ticker} onChange={setTicker} /><label><span>Prediction horizon</span><select value="5d" disabled><option value="5d">5 trading days</option></select></label></div>
        <button className="predict-button" disabled={!ticker.trim() || detail.isFetching} onClick={analyze}><Search size={17} />{detail.isFetching ? `Loading ${ticker.toUpperCase()}...` : 'Analyze'}</button>
      </section>
      {detail.isError && <div className="inline-error">{detail.error.message.includes('Insufficient') ? 'Insufficient historical validation data' : detail.error.message}</div>}

      {result && <section className="prediction-result">
        <div className="prediction-result-heading"><div><span>Latest validated outlook · {new Date(result.predictionTimestamp).toLocaleString()}</span><h2>{result.ticker} · 5 trading days</h2></div><span className={`outlook-badge ${result.signal === 'BUY' ? 'positive' : result.signal === 'SELL' ? 'negative' : ''}`}>{result.signal}</span></div>
        {result.stale && <div className="prediction-warning"><ShieldAlert size={15} />This prediction is stale. The scheduled market update may require attention.</div>}
        <div className="prediction-metrics">
          <div><span>Current price</span><strong>{money(result.currentPrice)}</strong></div>
          <div><span>Predicted price</span><strong>{money(result.predictedPrice)}</strong></div>
          <div><span>Expected return</span><strong className={(result.expectedReturn ?? 0) >= 0 ? 'gain' : 'loss'}>{percent(result.expectedReturn, true)}</strong></div>
          <div title="Calibrated estimate that the return after five trading days will be positive."><span>Probability Up</span><strong>{percent(result.probabilityUp)}</strong></div>
          <div title="Out-of-sample Brier skill versus historical prevalence. This is not this trade's probability of success."><span>Model reliability</span><strong>{result.reliabilityStatus === 'validated' ? percent(result.modelReliability) : 'Insufficient historical validation data'}</strong></div>
          <div title="Estimated loss magnitude from the 10th percentile of out-of-sample regression residuals."><span>Downside risk</span><strong>{percent(result.downsideRisk)}</strong><small>Risk / reward {result.riskReward == null ? 'Unavailable' : result.riskReward.toFixed(2)}</small></div>
        </div>

        <div className="analysis-grid">
          <section><div className="analysis-title"><TrendingUp size={16} /><h3>Observed bullish factors</h3></div><ul>{!result.explanation.bullish_factors?.length && <li>No bullish feature conditions identified.</li>}{result.explanation.bullish_factors?.map((factor) => <li key={factor}>{factor}</li>)}</ul></section>
          <section><div className="analysis-title"><ShieldAlert size={16} /><h3>Observed risk factors</h3></div><ul>{!result.explanation.risk_factors?.length && <li>No elevated feature risks identified.</li>}{result.explanation.risk_factors?.map((factor) => <li key={factor}>{factor}</li>)}</ul></section>
          <section><div className="analysis-title"><Target size={16} /><h3>Technical snapshot</h3></div><dl>{Object.entries(result.explanation.technical ?? {}).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{metric(value)}</dd></div>)}</dl></section>
          <section><div className="analysis-title"><BrainCircuit size={16} /><h3>Market regime</h3></div><dl>{Object.entries(result.explanation.market_regime ?? {}).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{metric(value)}</dd></div>)}</dl></section>
        </div>

        <section className="news-strip"><div className="analysis-title"><Newspaper size={16} /><h3>Recent analyzed news</h3><span>Not used for ML until sufficient timestamp-safe history accumulates</span></div>{!result.recentNews.length && <p>No analyzed news was available at the prediction timestamp.</p>}<div className="news-list">{result.recentNews.map((article) => <a key={`${article.published_at}-${article.url ?? article.title}`} href={article.url} target="_blank" rel="noreferrer"><strong>{article.title ?? 'Untitled article'}</strong><span>{article.source ?? 'Unknown source'} · {article.event_type ?? 'general'} · sentiment {metric(article.sentiment)}</span></a>)}</div></section>
        <footer className="prediction-version">{result.modelVersion} · {result.featureVersion}</footer>
      </section>}

      <section className="feature-card screener-panel prediction-screener">
        <div className="feature-card-heading"><div><h2>Market Screener</h2><p>Latest stored predictions. No model training occurs in this browser request.</p></div><div className="screener-sort" aria-label="Screener ranking"><button className={sort === 'expected_return' ? 'active' : ''} onClick={() => setSort('expected_return')}>Highest expected return</button><button className={sort === 'probability_up' ? 'active' : ''} onClick={() => setSort('probability_up')}>Highest probability</button></div></div>
        {screener.isLoading && <div className="scanner-empty"><span className="scan-pulse" /><strong>Loading stored predictions</strong></div>}
        {screener.isError && <div className="table-state error-text">{screener.error.message}</div>}
        {screener.data && <div className="table-scroll"><table className="feature-table scan-table"><thead><tr><th>Rank</th><th>Ticker</th><th>Price</th><th>Expected return</th><th>Probability Up</th><th>Downside risk</th><th>Signal</th></tr></thead><tbody>{!screener.data.results.length && <tr><td colSpan={7} className="table-state">Insufficient historical validation data</td></tr>}{screener.data.results.map((item, index) => <tr key={item.ticker} className="screener-row" onClick={() => { setTicker(item.ticker); setAnalyzedTicker(item.ticker) }}><td>{index + 1}</td><td><strong>{item.ticker}</strong>{item.stale && <small>Stale</small>}</td><td>{money(item.currentPrice)}</td><td className={(item.expectedReturn ?? 0) >= 0 ? 'gain' : 'loss'}>{percent(item.expectedReturn, true)}</td><td>{percent(item.probabilityUp)}</td><td>{percent(item.downsideRisk)}</td><td><span className={`signal-status ${item.signal === 'BUY' ? 'cross' : ''}`}>{item.signal}</span></td></tr>)}</tbody></table></div>}
      </section>
    </main>
  )
}