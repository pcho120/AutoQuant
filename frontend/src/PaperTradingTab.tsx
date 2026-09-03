import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Save, Trash2, TrendingDown, TrendingUp, WalletCards } from 'lucide-react'
import { fetchJson } from './api'
import { TickerSearch } from './TickerSearch'

type PaperPosition = {
  ticker: string
  quantity: number
  buyPrice: number
  currentPrice: number
}

type OrderAction = 'BUY' | 'SELL'

const PAPER_USER_ID = 'user123'
const INITIAL_CASH = 100_000
const money = (value: number) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export function PaperTradingTab() {
  const queryClient = useQueryClient()
  const [cash, setCash] = useState(() => {
    const storedCash = localStorage.getItem('autoquant-paper-cash')
    if (storedCash === null) return INITIAL_CASH
    const parsedCash = Number(storedCash)
    return Number.isFinite(parsedCash) ? parsedCash : INITIAL_CASH
  })
  const [holdingsDraft, setHoldingsDraft] = useState<PaperPosition[] | null>(null)
  const [ticker, setTicker] = useState('')
  const [action, setAction] = useState<OrderAction>('BUY')
  const [quantity, setQuantity] = useState(1)
  const [price, setPrice] = useState(100)
  const [newTicker, setNewTicker] = useState('')

  const holdingsQuery = useQuery({
    queryKey: ['paper-portfolio', PAPER_USER_ID],
    queryFn: () => fetchJson<{ positions: PaperPosition[] }>(`/api/paper-trading/${PAPER_USER_ID}`),
    refetchInterval: 30_000,
  })

  const holdings = holdingsDraft ?? holdingsQuery.data?.positions ?? []

  useEffect(() => {
    localStorage.setItem('autoquant-paper-cash', String(cash))
  }, [cash])

  const saveMutation = useMutation({
    mutationFn: () => fetchJson(`/api/paper-trading/${PAPER_USER_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ positions: holdings.map(({ ticker: symbol, quantity: shares, buyPrice }) => ({ ticker: symbol, quantity: shares, buyPrice })) }),
    }),
    onSuccess: async () => {
      setHoldingsDraft(null)
      await queryClient.invalidateQueries({ queryKey: ['paper-portfolio', PAPER_USER_ID] })
    },
  })

  const orderMutation = useMutation({
    mutationFn: () => fetchJson<{ status: string; remaining_cash: number; fee: number }>(
      `/api/paper-trading/${PAPER_USER_ID}/orders`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, action, quantity, price, cashBalance: cash }),
      },
    ),
    onSuccess: (result) => setCash(result.remaining_cash),
  })

  const updateHolding = (symbol: string, field: 'quantity' | 'buyPrice', value: number) => {
    setHoldingsDraft((current) => (current ?? holdings).map((position) => position.ticker === symbol ? { ...position, [field]: value } : position))
  }

  const addHolding = () => {
    const symbol = newTicker.trim().toUpperCase()
    if (!symbol || holdings.some((position) => position.ticker === symbol)) return
    setHoldingsDraft((current) => [...(current ?? holdings), { ticker: symbol, quantity: 1, buyPrice: 0, currentPrice: 0 }])
    setNewTicker('')
  }

  const holdingsValue = holdings.reduce((total, position) => total + position.quantity * position.currentPrice, 0)
  const holdingsCost = holdings.reduce((total, position) => total + position.quantity * position.buyPrice, 0)
  const unrealizedPnl = holdingsValue - holdingsCost

  return (
    <main className="feature-page">
      <section className="feature-heading">
        <div><span className="feature-kicker">Simulation workspace</span><h1>Paper Trading</h1><p>Practice orders against live quotes without putting capital at risk.</p></div>
        <div className="balance-chip"><WalletCards size={19} /><span>Available cash<strong>{money(cash)}</strong></span></div>
      </section>

      <section className="metric-row four">
        <div><span>Cash balance</span><strong>{money(cash)}</strong></div>
        <div><span>Holdings value</span><strong>{money(holdingsValue)}</strong></div>
        <div><span>Total account</span><strong>{money(cash + holdingsValue)}</strong></div>
        <div><span>Unrealized P/L</span><strong className={unrealizedPnl >= 0 ? 'gain' : 'loss'}>{unrealizedPnl >= 0 ? '+' : ''}{money(unrealizedPnl)}</strong></div>
      </section>

      <section className="feature-grid trading-grid">
        <div className="feature-card holdings-panel">
          <div className="feature-card-heading"><div><h2>Paper Holdings</h2><p>Edit quantity and average buy price, then save to Supabase.</p></div><button className="primary-button" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}><Save size={15} />{saveMutation.isPending ? 'Saving...' : 'Save Holdings'}</button></div>
          <div className="table-scroll">
            <table className="feature-table">
              <thead><tr><th>Ticker</th><th>Quantity</th><th>Buy Price</th><th>Current Price</th><th>Unrealized P/L</th><th aria-label="Actions" /></tr></thead>
              <tbody>
                {holdingsQuery.isLoading && <tr><td colSpan={6} className="table-state">Loading holdings...</td></tr>}
                {holdingsQuery.isError && <tr><td colSpan={6} className="table-state error-text">Unable to load holdings.</td></tr>}
                {!holdingsQuery.isLoading && !holdings.length && <tr><td colSpan={6} className="table-state">No paper holdings yet.</td></tr>}
                {holdings.map((position) => {
                  const pnl = position.quantity * (position.currentPrice - position.buyPrice)
                  return <tr key={position.ticker}>
                    <td><strong>{position.ticker}</strong></td>
                    <td><input aria-label={`${position.ticker} paper quantity`} type="number" min="0.01" step="0.01" value={position.quantity} onChange={(event) => updateHolding(position.ticker, 'quantity', Number(event.target.value))} /></td>
                    <td><input aria-label={`${position.ticker} paper buy price`} type="number" min="0" step="0.01" value={position.buyPrice} onChange={(event) => updateHolding(position.ticker, 'buyPrice', Number(event.target.value))} /></td>
                    <td>{money(position.currentPrice)}</td>
                    <td className={pnl >= 0 ? 'gain' : 'loss'}>{pnl >= 0 ? '+' : ''}{money(pnl)}</td>
                    <td><button className="row-action" aria-label={`Delete ${position.ticker}`} onClick={() => setHoldingsDraft((current) => (current ?? holdings).filter((item) => item.ticker !== position.ticker))}><Trash2 size={15} /></button></td>
                  </tr>
                })}
              </tbody>
            </table>
          </div>
          <div className="add-holding-row"><TickerSearch label="Add holding" value={newTicker} onChange={setNewTicker} /><button className="secondary-button" disabled={!newTicker.trim()} onClick={addHolding}><Plus size={15} />Add</button></div>
          <div className="feature-feedback">{saveMutation.isError ? <span className="error-text">{saveMutation.error.message}</span> : saveMutation.isSuccess ? <span className="gain">Holdings saved successfully.</span> : 'Paper holdings are isolated from your real portfolio.'}</div>
        </div>

        <aside className="feature-card order-ticket">
          <div className="feature-card-heading"><div><h2>Order Ticket</h2><p>Orders include a 0.1% transaction fee.</p></div></div>
          <div className="ticket-body">
            <TickerSearch label="Security" value={ticker} onChange={setTicker} />
            <div className="segmented-control" aria-label="Order action">
              <button className={action === 'BUY' ? 'active buy' : ''} onClick={() => setAction('BUY')}><TrendingUp size={15} />Buy</button>
              <button className={action === 'SELL' ? 'active sell' : ''} onClick={() => setAction('SELL')}><TrendingDown size={15} />Sell</button>
            </div>
            <div className="field-pair">
              <label><span>Quantity</span><input type="number" min="0.01" step="1" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label>
              <label><span>Price</span><input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(Number(event.target.value))} /></label>
            </div>
            <div className="order-summary"><span>Estimated value<strong>{money(quantity * price)}</strong></span><span>Fee<strong>{money(quantity * price * 0.001)}</strong></span><span className="total">{action === 'BUY' ? 'Estimated total' : 'Estimated proceeds'}<strong>{money(quantity * price * (action === 'BUY' ? 1.001 : 0.999))}</strong></span></div>
            <button className={`execute-button ${action.toLowerCase()}`} disabled={!ticker || quantity <= 0 || price <= 0 || orderMutation.isPending} onClick={() => orderMutation.mutate()}>{orderMutation.isPending ? 'Executing...' : `Execute ${action}`}</button>
            <div className="feature-feedback">{orderMutation.isError ? <span className="error-text">{orderMutation.error.message}</span> : orderMutation.isSuccess ? <span className="gain">Order executed. Fee: {money(orderMutation.data.fee)}</span> : 'Review the estimated value before submitting.'}</div>
          </div>
        </aside>
      </section>
    </main>
  )
}