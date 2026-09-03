import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { fetchJson } from './api'

type TickerResult = { ticker: string; name: string }

type TickerSearchProps = {
  value: string
  onChange: (ticker: string) => void
  label: string
  placeholder?: string
}

export function TickerSearch({ value, onChange, label, placeholder = 'Search ticker or company' }: TickerSearchProps) {
  const [focused, setFocused] = useState(false)
  const query = useQuery({
    queryKey: ['ticker-search', value],
    queryFn: () => fetchJson<{ results: TickerResult[] }>(`/api/tickers?q=${encodeURIComponent(value)}`),
    enabled: focused && value.trim().length > 0,
    staleTime: 60 * 60 * 1_000,
  })

  return (
    <label className="ticker-search-field">
      <span>{label}</span>
      <div className="ticker-search-control">
        <Search size={16} />
        <input
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          onFocus={() => setFocused(true)}
          onBlur={() => window.setTimeout(() => setFocused(false), 120)}
          onChange={(event) => onChange(event.target.value.toUpperCase())}
        />
        {focused && value && (
          <div className="ticker-results">
            {query.isLoading && <span>Searching...</span>}
            {query.isError && <span>Search unavailable. You can still enter a ticker.</span>}
            {query.data?.results.map((result) => (
              <button key={result.ticker} type="button" onMouseDown={() => onChange(result.ticker)}>
                <strong>{result.ticker}</strong><small>{result.name}</small>
              </button>
            ))}
            {query.data && !query.data.results.length && <span>No matching symbols</span>}
          </div>
        )}
      </div>
    </label>
  )
}