import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Bell,
  Check,
  ChevronDown,
  CloudDownload,
  CloudSun,
  Moon,
  RefreshCw,
  Save,
  Search,
  Settings,
  Sun,
} from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { MarketCharts } from './MarketCharts'
import { PaperTradingTab } from './PaperTradingTab'
import { PredictionTab } from './PredictionTab'
import { fetchJson } from './api'
import './App.css'
import './FeatureTabs.css'

type Position = {
  ticker: string
  quantity: number
  buyPrice: number
  currentPrice: number
}

type SortKey = 'ticker' | 'quantity' | 'buyPrice' | 'currentPrice' | 'marketValue' | 'pnl' | 'pnlPercent'
type SortDirection = 'asc' | 'desc'

export type Theme = 'light' | 'dark'

export type MarketPayload = {
  ticker: string
  period: string
  interval: string
  lastUpdated: string
  candles: Array<{ time: number; open: number; high: number; low: number; close: number }>
  volume: Array<{ time: number; value: number; color: string }>
  rsi: Array<{ time: number; value: number }>
  macd: Array<{ time: number; macd: number; signal: number; histogram: number }>
}

const USER_ID = 'default_user'
const COMPANY_NAMES: Record<string, string> = {
  AAPL: 'Apple Inc.',
  GOOGL: 'Alphabet Inc.',
  TSLA: 'Tesla Inc.',
}
const COLORS = ['#235a91', '#2f7d73', '#e29a3f', '#9a6fb0', '#d2645a', '#7390ad']
const TABS = ['Portfolio', 'Paper Trading', 'AI Prediction', 'Settings']
const TIMEFRAMES = [
  { label: '1D', period: '1d', interval: '5m' },
  { label: '1W', period: '5d', interval: '15m' },
  { label: '1M', period: '1mo', interval: '1h' },
  { label: '3M', period: '3mo', interval: '1d' },
  { label: '6M', period: '6mo', interval: '1d' },
  { label: '1Y', period: '1y', interval: '1d' },
]
const INTERVALS = ['5m', '15m', '1h', '1d']
const POSITION_COLUMNS: Array<{ key: SortKey; label: string }> = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'quantity', label: 'Quantity' },
  { key: 'buyPrice', label: 'Buy Price' },
  { key: 'currentPrice', label: 'Current Price' },
  { key: 'marketValue', label: 'Market Value' },
  { key: 'pnl', label: 'P/L ($)' },
  { key: 'pnlPercent', label: 'P/L (%)' },
]

const money = (value: number) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

function App() {
  const queryClient = useQueryClient()
  const [theme, setTheme] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem('autoquant-theme')
    if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  const [activeTab, setActiveTab] = useState('Portfolio')
  const [selectedTicker, setSelectedTicker] = useState('')
  const [drafts, setDrafts] = useState<Record<string, Pick<Position, 'quantity' | 'buyPrice'>>>({})
  const [timeframe, setTimeframe] = useState(TIMEFRAMES[2])
  const [interval, setInterval] = useState('1h')
  const [now, setNow] = useState(0)
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection } | null>(null)

  useEffect(() => {
    if (activeTab !== 'Portfolio') return
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1_000)
    return () => window.clearInterval(timer)
  }, [activeTab])

  useEffect(() => {
    localStorage.setItem('autoquant-theme', theme)
    document.documentElement.style.colorScheme = theme
  }, [theme])

  const portfolioQuery = useQuery({
    queryKey: ['portfolio', USER_ID],
    queryFn: () => fetchJson<{ positions: Position[] }>(`/api/portfolio/${USER_ID}`),
    enabled: activeTab === 'Portfolio',
    refetchInterval: 30_000,
  })

  const positions = (portfolioQuery.data?.positions ?? []).map((position) => ({
    ...position,
    ...drafts[position.ticker],
  }))
  const sortedPositions = sort ? [...positions].sort((left, right) => {
    const getValue = (position: Position) => {
      const marketValue = position.quantity * position.currentPrice
      const pnl = marketValue - position.quantity * position.buyPrice
      const values: Record<SortKey, string | number> = {
        ticker: position.ticker,
        quantity: position.quantity,
        buyPrice: position.buyPrice,
        currentPrice: position.currentPrice,
        marketValue,
        pnl,
        pnlPercent: position.buyPrice ? ((position.currentPrice - position.buyPrice) / position.buyPrice) * 100 : 0,
      }
      return values[sort.key]
    }
    const leftValue = getValue(left)
    const rightValue = getValue(right)
    const comparison = typeof leftValue === 'string' && typeof rightValue === 'string'
      ? leftValue.localeCompare(rightValue, undefined, { numeric: true, sensitivity: 'base' })
      : Number(leftValue) - Number(rightValue)
    return (comparison || left.ticker.localeCompare(right.ticker)) * (sort.direction === 'asc' ? 1 : -1)
  }) : positions
  const activeTicker = selectedTicker || positions[0]?.ticker || ''

  const marketQuery = useQuery({
    queryKey: ['market', activeTicker, timeframe.period, interval],
    queryFn: () => fetchJson<MarketPayload>(
      `/api/market/${encodeURIComponent(activeTicker)}?period=${timeframe.period}&interval=${interval}`,
    ),
    enabled: activeTab === 'Portfolio' && Boolean(activeTicker),
    refetchInterval: 10_000,
  })

  const saveMutation = useMutation({
    mutationFn: () => fetchJson(`/api/portfolio/${USER_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        positions: positions.map(({ ticker, quantity, buyPrice }) => ({ ticker, quantity, buyPrice })),
      }),
    }),
    onSuccess: async () => {
      setDrafts({})
      await queryClient.invalidateQueries({ queryKey: ['portfolio', USER_ID] })
    },
  })

  const webullSyncMutation = useMutation({
    mutationFn: () => fetchJson<{ accounts: number; synced: number }>(
      `/api/portfolio/${USER_ID}/sync-webull`,
      { method: 'POST' },
    ),
    onSuccess: () => {
      setDrafts({})
      setSelectedTicker('')
      void queryClient.invalidateQueries({ queryKey: ['portfolio', USER_ID] })
    },
  })

  const allocation = positions.map((position, index) => ({
    ...position,
    name: position.ticker,
    value: position.quantity * position.currentPrice,
    color: COLORS[index % COLORS.length],
  }))
  const totalValue = allocation.reduce((total, position) => total + position.value, 0)
  const totalCost = positions.reduce((total, position) => total + position.quantity * position.buyPrice, 0)
  const totalPnl = totalValue - totalCost
  const totalPnlPercent = totalCost ? (totalPnl / totalCost) * 100 : 0
  const lastUpdatedSeconds = portfolioQuery.dataUpdatedAt
    ? Math.max(0, Math.floor((now - portfolioQuery.dataUpdatedAt) / 1_000))
    : 0

  const updateDraft = (ticker: string, field: 'quantity' | 'buyPrice', value: number) => {
    const original = positions.find((position) => position.ticker === ticker)
    if (!original) return
    setDrafts((current) => {
      const existing = current[ticker] ?? { quantity: original.quantity, buyPrice: original.buyPrice }
      return { ...current, [ticker]: { ...existing, [field]: value } }
    })
  }

  const toggleSort = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction: current?.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  return (
    <div className="app-shell" data-theme={theme}>
      <header className="app-bar">
        <div className="brand">
          <div className="brand-icon"><span /><span /><span /></div>
          <div><strong>AutoQuant</strong><small>AI Portfolio Optimizer</small></div>
        </div>
        <div className="app-actions">
          <button className="icon-button" title="Search" aria-label="Search"><Search size={18} /></button>
          <button className="icon-button" title="Notifications" aria-label="Notifications"><Bell size={18} /></button>
          <button
            className="icon-button"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            aria-pressed={theme === 'dark'}
            onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="profile-button"><span>JD</span><strong>John Doe</strong><ChevronDown size={15} /></button>
        </div>
      </header>

      <nav className="tab-bar" aria-label="Primary navigation">
        {TABS.map((tab) => (
          <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>{tab}</button>
        ))}
      </nav>

      {activeTab === 'Paper Trading' ? <PaperTradingTab /> : activeTab === 'AI Prediction' ? <PredictionTab /> : activeTab !== 'Portfolio' ? (
        <main className="empty-module">
          <Settings size={26} />
          <h1>{activeTab}</h1>
          <p>This workspace remains available in the Streamlit application.</p>
        </main>
      ) : (
        <main className="dashboard">
          <section className="page-heading">
            <div><h1>Portfolio Management</h1><p>Track, analyze, and optimize your investment positions.</p></div>
            <div className="page-tools">
              <span className="market-badge"><i /> Market Open</span>
              <button className="weather-button"><CloudSun size={19} /><span>22°C<br /><small>New York</small></span><ChevronDown size={14} /></button>
            </div>
          </section>

          <section className="summary-strip">
            <div><span>Total Portfolio Value</span><strong>{money(totalValue)}</strong></div>
            <div><span>Total P/L</span><strong className={totalPnl >= 0 ? 'gain' : 'loss'}>{totalPnl >= 0 ? '+' : ''}{money(totalPnl)}</strong></div>
            <div><span>Total P/L %</span><strong className={totalPnlPercent >= 0 ? 'gain' : 'loss'}>{totalPnlPercent >= 0 ? '+' : ''}{totalPnlPercent.toFixed(2)}%</strong></div>
          </section>

          <section className="portfolio-workspace">
            <div className="positions-card">
              <div className="card-heading">
                <div><h2>Your Positions</h2><p>Click a row to analyze the ticker below. Edit quantity and buy price inline.</p></div>
                <div className="position-heading-actions">
                  <span>{positions.length} assets</span>
                  <button
                    className="sync-button"
                    onClick={() => webullSyncMutation.mutate()}
                    disabled={webullSyncMutation.isPending}
                  >
                    <CloudDownload size={15} />
                    {webullSyncMutation.isPending ? 'Syncing...' : 'Sync Webull'}
                  </button>
                </div>
              </div>
              <div className="table-scroll">
                <table className="positions-table">
                  <thead>
                    <tr>
                      {POSITION_COLUMNS.map((column) => {
                        const active = sort?.key === column.key
                        const nextDirection = active && sort.direction === 'asc' ? 'descending' : 'ascending'
                        return (
                          <th key={column.key} scope="col" aria-sort={active ? `${sort.direction}ending` : 'none'}>
                            <button
                              className={`sort-button${active ? ' active' : ''}`}
                              onClick={() => toggleSort(column.key)}
                              aria-label={`Sort by ${column.label} ${nextDirection}`}
                            >
                              <span>{column.label}</span>
                              {active
                                ? sort.direction === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                                : <ArrowUpDown size={12} />}
                            </button>
                          </th>
                        )
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {portfolioQuery.isLoading && <tr><td colSpan={7} className="table-state">Loading portfolio...</td></tr>}
                    {portfolioQuery.isError && <tr><td colSpan={7} className="table-state error-text">Unable to load portfolio.</td></tr>}
                    {sortedPositions.map((position) => {
                      const marketValue = position.quantity * position.currentPrice
                      const pnl = marketValue - position.quantity * position.buyPrice
                      const pnlPercent = position.buyPrice ? ((position.currentPrice - position.buyPrice) / position.buyPrice) * 100 : 0
                      return (
                        <tr key={position.ticker} className={position.ticker === activeTicker ? 'selected' : ''} onClick={() => setSelectedTicker(position.ticker)}>
                          <td><span className="ticker-mark">{position.ticker.slice(0, 1)}</span><span><strong>{position.ticker}</strong><small>{COMPANY_NAMES[position.ticker] ?? 'Listed security'}</small></span></td>
                          <td><input aria-label={`${position.ticker} quantity`} type="number" min="0.01" step="0.01" value={position.quantity} onClick={(event) => event.stopPropagation()} onChange={(event) => updateDraft(position.ticker, 'quantity', Number(event.target.value))} /></td>
                          <td><input aria-label={`${position.ticker} buy price`} type="number" min="0.01" step="0.01" value={position.buyPrice} onClick={(event) => event.stopPropagation()} onChange={(event) => updateDraft(position.ticker, 'buyPrice', Number(event.target.value))} /></td>
                          <td>{money(position.currentPrice)}</td><td>{money(marketValue)}</td>
                          <td className={pnl >= 0 ? 'gain' : 'loss'}>{pnl >= 0 ? '+' : ''}{money(pnl)}</td>
                          <td><span className={`performance-pill ${pnlPercent >= 0 ? 'gain' : 'loss'}`}>{pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%</span></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="table-actions">
                <span>
                  {webullSyncMutation.isError
                    ? <span className="sync-error">{webullSyncMutation.error.message}</span>
                    : webullSyncMutation.isSuccess
                      ? `Webull synced ${webullSyncMutation.data.synced} positions from ${webullSyncMutation.data.accounts} account(s)`
                      : `Data refreshed ${lastUpdatedSeconds}s ago`}
                </span>
                <div>
                  {saveMutation.isSuccess && !Object.keys(drafts).length && <span className="saved-state"><Check size={14} /> Saved</span>}
                  <button className="secondary-button" onClick={() => setDrafts({})} disabled={!Object.keys(drafts).length}>Reset</button>
                  <button className="primary-button" onClick={() => saveMutation.mutate()} disabled={!Object.keys(drafts).length || saveMutation.isPending}><Save size={16} />{saveMutation.isPending ? 'Saving...' : 'Save Changes'}</button>
                </div>
              </div>
            </div>

            <aside className="allocation-card">
              <div className="card-heading"><div><h2>Portfolio Allocation</h2><p>By current market value</p></div></div>
              <div className="donut-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={allocation} dataKey="value" nameKey="name" innerRadius="65%" outerRadius="88%" paddingAngle={2} onClick={(_, index) => setSelectedTicker(allocation[index].ticker)}>
                      {allocation.map((entry) => <Cell key={entry.ticker} fill={entry.color} stroke="none" opacity={entry.ticker === activeTicker ? 1 : 0.78} />)}
                    </Pie>
                    <Tooltip formatter={(value) => money(Number(value))} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-total"><span>Total Value</span><strong>{money(totalValue)}</strong></div>
              </div>
              <div className="allocation-legend">
                {allocation.map((position) => (
                  <button key={position.ticker} className={position.ticker === activeTicker ? 'active' : ''} onClick={() => setSelectedTicker(position.ticker)}>
                    <i style={{ backgroundColor: position.color }} /><span><strong>{position.ticker}</strong><small>{totalValue ? ((position.value / totalValue) * 100).toFixed(1) : '0.0'}%</small></span><em>{money(position.value)}</em>
                  </button>
                ))}
              </div>
            </aside>
          </section>

          <section className="analysis-section">
            <div className="analysis-heading">
              <div><h2>Market Analysis</h2><p>Select any portfolio row or allocation segment to update this workspace.</p></div>
              <div className="live-status"><i /> Live market data</div>
            </div>
            <div className="security-selector" aria-label="Security selector">
              {positions.map((position) => <button key={position.ticker} className={position.ticker === activeTicker ? 'active' : ''} onClick={() => setSelectedTicker(position.ticker)}>{position.ticker}</button>)}
            </div>
            <div className="market-card">
              <div className="market-toolbar">
                <div className="quote-block"><span>{activeTicker}</span><strong>{money(marketQuery.data?.candles.at(-1)?.close ?? positions.find((item) => item.ticker === activeTicker)?.currentPrice ?? 0)}</strong><small>{COMPANY_NAMES[activeTicker] ?? 'Market security'}</small></div>
                <div className="timeframe-control">{TIMEFRAMES.map((item) => <button key={item.label} className={timeframe.label === item.label ? 'active' : ''} onClick={() => { setTimeframe(item); setInterval(item.interval) }}>{item.label}</button>)}</div>
                <label className="interval-control">Interval<select value={interval} onChange={(event) => setInterval(event.target.value)}>{INTERVALS.map((value) => <option key={value}>{value}</option>)}</select></label>
                <button className="icon-button" onClick={() => marketQuery.refetch()} title="Refresh market data" aria-label="Refresh market data"><RefreshCw size={17} className={marketQuery.isFetching ? 'spinning' : ''} /></button>
              </div>
              {marketQuery.isLoading && <div className="chart-state">Loading market data...</div>}
              {marketQuery.isError && <div className="chart-state error-text">{marketQuery.error.message}</div>}
              {marketQuery.data && <MarketCharts data={marketQuery.data} theme={theme} />}
            </div>
          </section>
        </main>
      )}
    </div>
  )
}

export default App