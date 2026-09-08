import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock3, TrendingDown, TrendingUp, WalletCards } from 'lucide-react'
import { fetchJson } from './api'
import { TickerSearch } from './TickerSearch'

type PaperPosition = {
  ticker: string
  quantity: number
  buyPrice: number
  currentPrice: number
}

type OrderAction = 'BUY' | 'SELL'
type OrderType = 'MARKET' | 'LIMIT'

type PaperOrder = {
  ticker: string
  action: OrderAction
  order_type: OrderType
  requested_quantity: number
  quantity: number
  requested_price: number | null
  filled_price: number
  fee: number
  quote_timestamp: string
  execution_session: 'REGULAR' | 'CLOSED'
  executed_at: string
}

type PaperAccount = {
  positions: PaperPosition[]
  cashBalance: number
  initialCash: number
  orders: PaperOrder[]
}

type TradeQuote = {
  ticker: string
  price: number
  timestamp: string
  marketOpen: boolean
  regularSession: boolean
  afterHoursBuyAllowed: boolean
}

const PAPER_USER_ID = 'user123'
const money = (value: number) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export function PaperTradingTab() {
  const queryClient = useQueryClient()
  const [ticker, setTicker] = useState('')
  const [action, setAction] = useState<OrderAction>('BUY')
  const [orderType, setOrderType] = useState<OrderType>('MARKET')
  const [quantity, setQuantity] = useState(1)
  const [limitPrice, setLimitPrice] = useState('')

  const holdingsQuery = useQuery({
    queryKey: ['paper-portfolio', PAPER_USER_ID],
    queryFn: () => fetchJson<PaperAccount>(`/api/paper-trading/${PAPER_USER_ID}`),
    refetchInterval: 30_000,
  })

  const normalizedTicker = ticker.trim().toUpperCase()
  const quoteQuery = useQuery({
    queryKey: ['paper-quote', normalizedTicker],
    queryFn: () => fetchJson<TradeQuote>(`/api/paper-trading/quotes/${normalizedTicker}`),
    enabled: Boolean(normalizedTicker),
    refetchInterval: 15_000,
  })

  const holdings = holdingsQuery.data?.positions ?? []
  const cash = holdingsQuery.data?.cashBalance ?? 0
  const orders = holdingsQuery.data?.orders ?? []

  const orderMutation = useMutation({
    mutationFn: () => fetchJson<{ status: string; remaining_cash: number; fee: number; filled_price: number; quantity: number; requested_quantity: number; partial_fill: boolean }>(
      `/api/paper-trading/${PAPER_USER_ID}/orders`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: normalizedTicker,
          action,
          quantity,
          orderType,
          limitPrice: orderType === 'LIMIT' ? Number(limitPrice) : null,
        }),
      },
    ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['paper-portfolio', PAPER_USER_ID] })
      await queryClient.invalidateQueries({ queryKey: ['paper-quote', normalizedTicker] })
    },
  })

  const holdingsValue = holdings.reduce((total, position) => total + position.quantity * position.currentPrice, 0)
  const holdingsCost = holdings.reduce((total, position) => total + position.quantity * position.buyPrice, 0)
  const unrealizedPnl = holdingsValue - holdingsCost
  const closedSessionBuy = action === 'BUY' && Boolean(quoteQuery.data?.afterHoursBuyAllowed)
  const orderAvailable = Boolean(quoteQuery.data?.marketOpen) || closedSessionBuy

  return (
    <main className="feature-page">
      <section className="feature-heading">
        <div><span className="feature-kicker">Simulation workspace</span><h1>Paper Trading</h1><p>Server-priced simulated execution with persistent cash and positions.</p></div>
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
          <div className="feature-card-heading"><div><h2>Paper Holdings</h2><p>Positions and weighted average cost update automatically after each fill.</p></div></div>
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
                    <td>{position.quantity.toLocaleString()}</td>
                    <td>{money(position.buyPrice)}</td>
                    <td>{money(position.currentPrice)}</td>
                    <td className={pnl >= 0 ? 'gain' : 'loss'}>{pnl >= 0 ? '+' : ''}{money(pnl)}</td>
                    <td />
                  </tr>
                })}
              </tbody>
            </table>
          </div>
          <div className="feature-feedback">Paper holdings are isolated from your real portfolio and stored in Supabase.</div>
        </div>

        <aside className="feature-card order-ticket">
          <div className="feature-card-heading"><div><h2>Order Ticket</h2><p>Orders include a 0.1% transaction fee.</p></div></div>
          <div className="ticket-body">
            <TickerSearch label="Security" value={ticker} onChange={setTicker} />
            <div className="segmented-control" aria-label="Order action">
              <button className={action === 'BUY' ? 'active buy' : ''} onClick={() => setAction('BUY')}><TrendingUp size={15} />Buy</button>
              <button className={action === 'SELL' ? 'active sell' : ''} onClick={() => setAction('SELL')}><TrendingDown size={15} />Sell</button>
            </div>
            <div className="segmented-control" aria-label="Order type">
              <button className={orderType === 'MARKET' ? 'active' : ''} onClick={() => setOrderType('MARKET')}>Market</button>
              <button className={orderType === 'LIMIT' ? 'active' : ''} onClick={() => setOrderType('LIMIT')}>Limit (immediate)</button>
            </div>
            <div className="field-pair">
              <label><span>Quantity</span><input type="number" min="0.01" step="1" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label>
              {orderType === 'LIMIT' && <label><span>Limit price</span><input type="number" min="0.01" step="0.01" value={limitPrice} onChange={(event) => setLimitPrice(event.target.value)} /></label>}
            </div>
            <div className="order-summary">
              <span>Latest quote<strong>{quoteQuery.data ? money(quoteQuery.data.price) : '—'}</strong></span>
              <span>Market status<strong>{quoteQuery.data?.marketOpen ? 'Open' : closedSessionBuy ? 'Closed · BUY at last close' : 'Closed · SELL unavailable'}</strong></span>
              <span>Estimated value<strong>{quoteQuery.data ? money(quantity * quoteQuery.data.price) : '—'}</strong></span>
              <span>Estimated fee<strong>{quoteQuery.data ? money(quantity * quoteQuery.data.price * 0.001) : '—'}</strong></span>
            </div>
            <button className={`execute-button ${action.toLowerCase()}`} disabled={!normalizedTicker || quantity <= 0 || !orderAvailable || (orderType === 'LIMIT' && Number(limitPrice) <= 0) || orderMutation.isPending} onClick={() => orderMutation.mutate()}>{orderMutation.isPending ? 'Executing...' : closedSessionBuy ? `Buy at ${money(quoteQuery.data?.price ?? 0)} close` : `Execute ${action}`}</button>
            <div className="feature-feedback">{orderMutation.isError ? <span className="error-text">{orderMutation.error.message}</span> : orderMutation.isSuccess ? <span className="gain">{orderMutation.data.partial_fill ? `Partially filled ${orderMutation.data.quantity} of ${orderMutation.data.requested_quantity}` : `Filled ${orderMutation.data.quantity}`} at {money(orderMutation.data.filled_price)}. Fee: {money(orderMutation.data.fee)}</span> : closedSessionBuy ? 'Closed-session BUY uses the last regular close with no slippage; the 0.1% fee still applies.' : 'Market orders include 0.05% simulated slippage and a 0.1% fee.'}</div>
          </div>
        </aside>
      </section>

      <section className="feature-card">
        <div className="feature-card-heading"><div><h2>Recent Fills</h2><p>Completed simulated orders recorded by the server.</p></div><Clock3 size={18} /></div>
        <div className="table-scroll">
          <table className="feature-table">
            <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Type</th><th>Quantity</th><th>Fill</th><th>Fee</th></tr></thead>
            <tbody>
              {!orders.length && <tr><td colSpan={7} className="table-state">No completed orders yet.</td></tr>}
              {orders.map((order) => <tr key={`${order.executed_at}-${order.ticker}`}>
                <td>{new Date(order.executed_at).toLocaleString()}</td><td><strong>{order.ticker}</strong></td>
                <td className={order.action === 'BUY' ? 'gain' : 'loss'}>{order.action}</td><td>{order.order_type}{order.execution_session === 'CLOSED' ? ' · CLOSE' : ''}</td>
                <td>{order.quantity.toLocaleString()}{order.quantity < order.requested_quantity ? ` / ${order.requested_quantity.toLocaleString()}` : ''}</td><td>{money(order.filled_price)}</td><td>{money(order.fee)}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}