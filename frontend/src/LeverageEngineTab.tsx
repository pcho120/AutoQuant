import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Activity, Gauge, Play, Shield, TrendingDown, Zap } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { LeverageHelp } from './AnalysisHelp'
import { fetchJson } from './api'

type Benchmark = 'QQQ' | '^NDX'
type ExecutionPrice = 'open' | 'close'
type Signal = {
  as_of: string
  benchmark: Benchmark
  state: 'BULL' | 'BEAR'
  allocation: 'TQQQ' | 'QQQ_QLD' | 'CASH'
  weights: Record<'QQQ' | 'QLD' | 'TQQQ' | 'CASH', number>
  indicators: { ndx_close: number; ndx_sma250: number; vix_ma10: number; mdd_52w: number }
}
type Metrics = {
  cagr: number
  mdd: number
  sharpe_ratio: number
  sortino_ratio: number
  ulcer_index: number
  total_rebalances: number
  total_return: number
  start_date: string
  end_date: string
}
type Backtest = {
  benchmark: Benchmark
  one_x_proxy: Benchmark
  data_period_years: number
  synthetic_assets: string[]
  metrics: Metrics
  latest_signal: Signal
  equity_curve: Array<{ date: string; equity: number; drawdown: number; allocation: string }>
  trades: Array<{ signal_date: string; execution_date: string; execution_price: string; allocation: string; turnover: number; cost: number }>
}

const percent = (value: number) => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
const money = (value: number) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export function LeverageEngineTab() {
  const [benchmark, setBenchmark] = useState<Benchmark>('QQQ')
  const [period, setPeriod] = useState('max')
  const [executionPrice, setExecutionPrice] = useState<ExecutionPrice>('close')
  const [commissionPct, setCommissionPct] = useState(0.05)
  const [slippagePct, setSlippagePct] = useState(0.05)

  const signal = useQuery({
    queryKey: ['leverage-signal', benchmark],
    queryFn: () => fetchJson<Signal>(`/api/leverage/signal?benchmark=${encodeURIComponent(benchmark)}`),
    staleTime: 15 * 60_000,
    retry: false,
  })
  const backtest = useMutation({
    mutationFn: () => fetchJson<Backtest>('/api/leverage/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        benchmark,
        period,
        executionPrice,
        commissionRate: commissionPct / 100,
        slippageRate: slippagePct / 100,
      }),
    }),
  })
  const result = backtest.data
  const curve = result?.equity_curve.filter((_, index, values) => {
    const stride = Math.max(1, Math.ceil(values.length / 700))
    return index % stride === 0 || index === values.length - 1
  }) ?? []

  return (
    <main className="feature-page leverage-page">
      <section className="feature-heading">
        <div><span className="feature-kicker">Independent allocation engine</span><h1>Leverage Engine</h1><p>NASDAQ trend, volatility, and drawdown regime switching with next-day execution.</p></div>
        <div className="feature-heading-tools"><div className="model-badge"><Zap size={20} /><span>Tripod strategy<strong>3x · 1.5x · cash switching</strong></span></div><LeverageHelp /></div>
      </section>

      <section className="leverage-signal-band">
        <div className="signal-summary"><span>Current regime</span><strong>{signal.data?.state ?? (signal.isLoading ? 'Loading' : 'Unavailable')}</strong><small>{signal.data ? `As of ${new Date(signal.data.as_of).toLocaleDateString()}` : signal.error?.message}</small></div>
        <div className="signal-summary primary"><span>Target allocation</span><strong>{signal.data?.allocation.replace('_', ' + ') ?? 'Unavailable'}</strong><small>Calculated after market close</small></div>
        <div className="allocation-weights">
          {(['QQQ', 'QLD', 'TQQQ', 'CASH'] as const).map((asset) => <div key={asset}><span>{asset}</span><strong>{((signal.data?.weights[asset] ?? 0) * 100).toFixed(0)}%</strong></div>)}
        </div>
      </section>

      {signal.data && <section className="tripod-indicators" aria-label="Tripod indicators">
        <div><Activity size={15} /><span>Benchmark close<strong>{signal.data.indicators.ndx_close.toFixed(2)}</strong></span></div>
        <div><TrendingDown size={15} /><span>SMA 250<strong>{signal.data.indicators.ndx_sma250.toFixed(2)}</strong></span></div>
        <div><Gauge size={15} /><span>VIX MA 10<strong>{signal.data.indicators.vix_ma10.toFixed(2)}</strong></span></div>
        <div><Shield size={15} /><span>52-week drawdown<strong>{percent(signal.data.indicators.mdd_52w)}</strong></span></div>
      </section>}

      <section className="feature-card backtest-console">
        <div className="feature-card-heading"><div><h2>Backtest Console</h2><p>Signals calculated at T close execute at the selected T+1 price.</p></div></div>
        <div className="backtest-controls">
          <label><span>Benchmark</span><select value={benchmark} onChange={(event) => setBenchmark(event.target.value as Benchmark)}><option value="QQQ">QQQ</option><option value="^NDX">NASDAQ-100 (^NDX)</option></select></label>
          <label><span>History</span><select value={period} onChange={(event) => setPeriod(event.target.value)}><option value="max">Maximum available</option><option value="10y">10 years</option><option value="5y">5 years</option><option value="2y">2 years</option></select></label>
          <label><span>T+1 execution</span><select value={executionPrice} onChange={(event) => setExecutionPrice(event.target.value as ExecutionPrice)}><option value="close">Close</option><option value="open">Open</option></select></label>
          <label><span>Commission (%)</span><input type="number" min="0" max="5" step="0.01" value={commissionPct} onChange={(event) => setCommissionPct(Number(event.target.value))} /></label>
          <label><span>Slippage (%)</span><input type="number" min="0" max="5" step="0.01" value={slippagePct} onChange={(event) => setSlippagePct(Number(event.target.value))} /></label>
          <button className="predict-button" disabled={backtest.isPending} onClick={() => backtest.mutate()}><Play size={16} />{backtest.isPending ? 'Running...' : 'Run backtest'}</button>
        </div>
        {backtest.isError && <div className="inline-error">{backtest.error.message}</div>}
      </section>

      {result && <>
        <section className="leverage-metrics">
          <div><span>CAGR</span><strong>{percent(result.metrics.cagr)}</strong></div>
          <div><span>Total return</span><strong>{percent(result.metrics.total_return)}</strong></div>
          <div><span>Maximum drawdown</span><strong className="loss">{percent(result.metrics.mdd)}</strong></div>
          <div><span>Sharpe</span><strong>{result.metrics.sharpe_ratio.toFixed(2)}</strong></div>
          <div><span>Sortino</span><strong>{result.metrics.sortino_ratio.toFixed(2)}</strong></div>
          <div><span>Ulcer index</span><strong>{result.metrics.ulcer_index.toFixed(2)}</strong></div>
          <div><span>Rebalances</span><strong>{result.metrics.total_rebalances}</strong></div>
        </section>

        <section className="feature-card leverage-chart-panel">
          <div className="feature-card-heading"><div><h2>Strategy Equity</h2><p>{result.data_period_years} years · 1x proxy {result.one_x_proxy} · synthetic {result.synthetic_assets.join(' / ')} · {money(result.equity_curve.at(-1)?.equity ?? 0)}</p></div></div>
          <div className="leverage-chart">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={curve}><CartesianGrid stroke="var(--line-soft)" vertical={false} /><XAxis dataKey="date" tickFormatter={(value) => String(value).slice(0, 4)} minTickGap={40} /><YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`} width={58} /><Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleDateString()} formatter={(value) => [money(Number(value)), 'Equity']} /><Line type="monotone" dataKey="equity" stroke="var(--teal)" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer>
          </div>
        </section>

        <section className="feature-card leverage-trades">
          <div className="feature-card-heading"><div><h2>Recent Rebalances</h2><p>Signal and execution dates are separated to prevent look-ahead bias.</p></div></div>
          <div className="table-scroll"><table className="feature-table"><thead><tr><th>Signal date</th><th>Execution date</th><th>Price</th><th>Allocation</th><th>Turnover</th><th>Cost</th></tr></thead><tbody>{result.trades.slice(-12).reverse().map((trade) => <tr key={trade.execution_date}><td>{trade.signal_date.slice(0, 10)}</td><td>{trade.execution_date.slice(0, 10)}</td><td>{trade.execution_price}</td><td>{trade.allocation.replace('_', ' + ')}</td><td>{percent(trade.turnover)}</td><td>{money(trade.cost)}</td></tr>)}</tbody></table></div>
        </section>
      </>}
    </main>
  )
}