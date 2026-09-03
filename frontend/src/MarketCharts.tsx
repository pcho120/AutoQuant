import { memo, useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { MarketPayload, Theme } from './App'

type ChartHostProps = {
  label: string
  height: number
  theme: Theme
  render: (chart: IChartApi) => void
}

function ChartHost({ label, height, theme, render }: ChartHostProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const container = containerRef.current
    const dark = theme === 'dark'
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: dark ? '#151d27' : '#ffffff' },
        textColor: dark ? '#9eacba' : '#708093',
        fontFamily: 'IBM Plex Sans, sans-serif',
      },
      grid: {
        vertLines: { color: dark ? '#263241' : '#edf1f4' },
        horzLines: { color: dark ? '#263241' : '#edf1f4' },
      },
      rightPriceScale: { borderColor: dark ? '#344252' : '#d9dde3' },
      timeScale: { borderColor: dark ? '#344252' : '#d9dde3', timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: '#708090' }, horzLine: { color: '#708090' } },
      height,
      width: container.clientWidth,
    })
    render(chart)
    chart.timeScale().fitContent()

    const observer = new ResizeObserver(([entry]) => chart.applyOptions({ width: entry.contentRect.width }))
    observer.observe(container)
    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [height, render, theme])

  return (
    <section className="chart-panel">
      <div className="chart-label">{label}</div>
      <div ref={containerRef} className="chart-canvas" />
    </section>
  )
}

const timestamp = (value: number) => value as UTCTimestamp

export const MarketCharts = memo(function MarketCharts({ data, theme }: { data: MarketPayload; theme: Theme }) {
  return (
    <div className="chart-stack">
      <ChartHost label="PRICE · CANDLESTICK" height={330} theme={theme} render={(chart) => {
        const series = chart.addSeries(CandlestickSeries, {
          upColor: '#2f7d73', downColor: '#c94f59', borderVisible: false,
          wickUpColor: '#2f7d73', wickDownColor: '#c94f59',
        })
        series.setData(data.candles.map((point) => ({ ...point, time: timestamp(point.time) })))
      }} />
      <ChartHost label="VOLUME" height={120} theme={theme} render={(chart) => {
        const series = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' } })
        series.setData(data.volume.map((point) => ({ ...point, time: timestamp(point.time) })))
      }} />
      <ChartHost label="RSI (14)" height={150} theme={theme} render={(chart) => {
        const series = chart.addSeries(LineSeries, { color: '#235a91', lineWidth: 2 })
        series.setData(data.rsi.map((point) => ({ ...point, time: timestamp(point.time) })))
        series.createPriceLine({ price: 70, color: '#d34b45', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '70' })
        series.createPriceLine({ price: 30, color: '#168a68', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '30' })
      }} />
      <ChartHost label="MACD (12, 26, 9)" height={170} theme={theme} render={(chart) => {
        const histogram = chart.addSeries(HistogramSeries, { priceFormat: { type: 'price' } })
        histogram.setData(data.macd.map((point) => ({
          time: timestamp(point.time), value: point.histogram,
          color: point.histogram >= 0 ? '#8bc7b5' : '#e6aaa7',
        })))
        const macd = chart.addSeries(LineSeries, { color: '#165d8f', lineWidth: 2 })
        macd.setData(data.macd.map((point) => ({ time: timestamp(point.time), value: point.macd })))
        const signal = chart.addSeries(LineSeries, { color: '#d27a29', lineWidth: 2 })
        signal.setData(data.macd.map((point) => ({ time: timestamp(point.time), value: point.signal })))
      }} />
    </div>
  )
})