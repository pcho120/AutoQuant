import { useState } from 'react'
import { CircleHelp, X } from 'lucide-react'

type Language = 'ko' | 'en'
type GuideSection = { title: string; body?: string; items?: Array<{ term: string; description: string }> }
type Guide = { eyebrow: string; title: string; summary: string; sections: GuideSection[]; notice: string }

const predictionGuide: Record<Language, Guide> = {
  ko: {
    eyebrow: 'AI Prediction 안내',
    title: '이 화면은 무엇을 분석하나요?',
    summary: '개별 종목의 5거래일 후 방향과 수익률을 서로 다른 머신러닝 모델로 추정합니다. 브라우저에서는 학습하지 않으며, 과거 데이터로 검증된 최신 결과를 Supabase에서 읽습니다.',
    sections: [
      {
        title: '백그라운드와 분석 로직',
        body: '일봉 가격과 거래량으로 RSI, MACD, ATR, ADX, 볼린저 밴드 폭, 모멘텀을 만들고 SPY, QQQ, VIX, 섹터 ETF 환경을 결합합니다. 상승 여부는 분류 모델, 수익률 크기는 회귀 모델이 담당합니다. 시간 순서 기반 walk-forward 검증과 5거래일 purge 구간으로 미래 데이터 누수를 줄입니다.',
      },
      {
        title: '상단 결과 박스',
        items: [
          { term: 'Current price', description: '예측 기준시점의 종가입니다. 실시간 체결가가 아닐 수 있습니다.' },
          { term: 'Predicted price', description: '현재가 × (1 + Expected Return)으로 계산한 5거래일 후 추정 가격입니다.' },
          { term: 'Expected return', description: '회귀 모델이 예상한 5거래일 수익률입니다. +0.5%는 평균적으로 0.5% 상승을 추정한다는 뜻입니다.' },
          { term: 'Probability Up', description: '5거래일 뒤 수익률이 양수일 보정 확률입니다. Expected Return과 다른 모델의 결과라 서로 엇갈릴 수 있습니다.' },
          { term: 'Model reliability', description: '확률 모델의 외부검증 Brier skill입니다. 개별 거래의 성공확률이 아니며, 0%는 단순 기준보다 개선을 입증하지 못했다는 뜻입니다.' },
          { term: 'Downside risk', description: '과거 외부검증 잔차의 하위 10%를 반영한 불리한 손실 폭 추정치입니다.' },
          { term: 'Risk / reward', description: 'Expected Return ÷ Downside Risk입니다. 높을수록 기대수익 대비 추정 하방 위험이 작습니다.' },
          { term: 'Signal', description: '상승확률 > 50%와 양의 예상수익률이 함께 나오면 BUY, 둘 다 반대면 SELL, 불일치하면 HOLD입니다.' },
        ],
      },
      {
        title: '분석 패널과 표',
        items: [
          { term: 'Observed bullish factors', description: '현재 특성 중 상승 방향으로 해석된 조건입니다.' },
          { term: 'Observed risk factors', description: '과매수, 음의 모멘텀, 높은 변동성 등 관찰된 위험 조건입니다.' },
          { term: 'Technical snapshot', description: '해당 종목의 RSI, MACD, ATR, 상대 거래량 등 최신 입력값입니다.' },
          { term: 'Market regime', description: 'SPY·QQQ 추세, VIX, 섹터 상대수익률로 본 시장 환경입니다.' },
          { term: 'Recent analyzed news', description: '예측시점 이전의 참고 뉴스입니다. 현재 ML 학습·예측 입력에는 포함되지 않습니다.' },
          { term: 'Market Screener', description: '저장된 최신 예측을 Expected Return 또는 Probability Up 순으로 비교합니다. 이 표를 열어도 모델 재학습은 실행되지 않습니다.' },
        ],
      },
      {
        title: '운영 방식',
        body: '시장 데이터 수집 → 특성 생성 → 모델 평가·학습 → 예측 저장 → API 조회 순서의 오프라인 배치 구조입니다. Stale 표시는 예측이 4일 이상 갱신되지 않았음을 뜻합니다.',
      },
    ],
    notice: '이 결과는 검증 가능한 연구·의사결정 보조 신호이며 투자 자문이나 주문 지시가 아닙니다. 특히 Model Reliability가 낮으면 기술지표 요약 이상의 예측력을 입증하지 못한 상태로 해석해야 합니다.',
  },
  en: {
    eyebrow: 'AI Prediction guide',
    title: 'What does this page analyze?',
    summary: 'It estimates an individual stock’s direction and return over the next five trading days with separate machine-learning models. Training never runs in the browser; the page reads the latest validated result stored in Supabase.',
    sections: [
      {
        title: 'Background and model logic',
        body: 'Daily price and volume produce RSI, MACD, ATR, ADX, Bollinger width, and momentum features, combined with SPY, QQQ, VIX, and sector ETF context. A classifier estimates direction while a regressor estimates return magnitude. Time-ordered walk-forward evaluation and a five-day purge reduce look-ahead leakage.',
      },
      {
        title: 'Top result boxes',
        items: [
          { term: 'Current price', description: 'The closing price at the prediction timestamp, which may not be a live tradable quote.' },
          { term: 'Predicted price', description: 'The five-day estimate calculated as current price × (1 + Expected Return).' },
          { term: 'Expected return', description: 'The regression model’s estimated five-day return. +0.5% means an average estimated gain of 0.5%.' },
          { term: 'Probability Up', description: 'The calibrated probability that the five-day return is positive. It can disagree with Expected Return because it comes from a different model.' },
          { term: 'Model reliability', description: 'Out-of-sample Brier skill versus a prevalence baseline. It is not the success probability of this trade; 0% means no demonstrated improvement over the baseline.' },
          { term: 'Downside risk', description: 'An adverse loss estimate based on the lower 10th percentile of out-of-sample regression residuals.' },
          { term: 'Risk / reward', description: 'Expected Return divided by Downside Risk. Higher values indicate more expected return per unit of estimated downside.' },
          { term: 'Signal', description: 'BUY requires Probability Up > 50% and positive Expected Return. SELL requires both to be negative; disagreement produces HOLD.' },
        ],
      },
      {
        title: 'Analysis panels and table',
        items: [
          { term: 'Observed bullish factors', description: 'Current feature conditions interpreted as supportive of upside.' },
          { term: 'Observed risk factors', description: 'Observed risks such as overbought levels, negative momentum, or elevated volatility.' },
          { term: 'Technical snapshot', description: 'Latest RSI, MACD, ATR, relative volume, and related model inputs for the stock.' },
          { term: 'Market regime', description: 'Broader context from SPY and QQQ trends, VIX, and sector-relative returns.' },
          { term: 'Recent analyzed news', description: 'Reference news published before the prediction timestamp. News is not currently an ML training or inference feature.' },
          { term: 'Market Screener', description: 'Compares stored predictions by Expected Return or Probability Up. Opening it does not retrain a model.' },
        ],
      },
      {
        title: 'Operating model',
        body: 'The offline pipeline runs market collection → feature generation → model evaluation and training → prediction storage → API serving. Stale means the prediction has not been refreshed for more than four days.',
      },
    ],
    notice: 'This is a research and decision-support signal, not investment advice or an order instruction. Low Model Reliability means predictive value beyond a technical-feature summary has not been demonstrated.',
  },
}

const leverageGuide: Record<Language, Guide> = {
  ko: {
    eyebrow: 'Leverage Engine 안내',
    title: '트라이팟 전략은 어떻게 움직이나요?',
    summary: '시계열 모멘텀(Time-series Momentum)과 추세추종(Trend Following)의 핵심 원리를 개량해 모방한 규칙 기반 자산배분 전략입니다. 개별 종목 가격을 예측하지 않고, NASDAQ-100의 자기 과거 추세와 변동성·낙폭을 이용해 3배, 1.5배, 현금 노출을 전환합니다.',
    sections: [
      {
        title: '백그라운드와 상태 판정',
        body: 'NASDAQ-100 또는 QQQ가 SMA250보다 1% 초과 높으면 BULL, 5% 초과 낮으면 BEAR입니다. 그 사이 완충 구간에서는 직전 상태를 유지해 잦은 왕복매매를 줄입니다. VIX MA10은 단기 공포 수준, 52-week drawdown은 최근 250거래일 고점 대비 낙폭을 측정합니다.',
      },
      {
        title: '현재 시그널 영역',
        items: [
          { term: 'Current regime', description: '장기 추세로 판정한 BULL 또는 BEAR 상태입니다.' },
          { term: 'Target allocation', description: '오늘 종가 데이터로 계산해 다음 거래일에 맞출 목표 자산배분입니다.' },
          { term: 'QQQ / QLD / TQQQ / CASH', description: '각 자산의 목표 비중입니다. QQQ 50% + QLD 50%는 이론적으로 약 1.5배 노출입니다.' },
          { term: 'Benchmark close', description: '상태 판정에 사용한 QQQ 또는 NASDAQ-100 지수 종가입니다.' },
          { term: 'SMA 250', description: '약 1년 장기 이동평균으로, 추세추종의 기준선입니다.' },
          { term: 'VIX MA 10', description: 'VIX의 10거래일 평균으로, 일시적인 변동을 완화한 시장 공포 지표입니다.' },
          { term: '52-week drawdown', description: '최근 250거래일 최고점 대비 현재 하락률입니다.' },
        ],
      },
      {
        title: '트라이팟 배분 규칙',
        items: [
          { term: '강한 상승장', description: 'BULL, VIX MA10 < 28, 낙폭 9% 미만이면 TQQQ 100%입니다.' },
          { term: '상승장 속 위험', description: 'BULL이지만 VIX MA10 ≥ 28 또는 낙폭 9% 이상이면 QQQ 50% + QLD 50%입니다.' },
          { term: '하락장 속 공포 완화', description: 'BEAR이고 VIX MA10 < 18이면 QQQ 50% + QLD 50%입니다.' },
          { term: '하락장 속 공포 심화', description: 'BEAR이고 VIX MA10 ≥ 18이면 CASH 100%입니다.' },
        ],
      },
      {
        title: 'Backtest Console과 결과',
        items: [
          { term: 'Benchmark', description: 'QQQ는 실제 ETF에 가깝고, ^NDX는 더 긴 가격지수 프록시 이력을 제공합니다.' },
          { term: 'T+1 execution', description: 'T일 종가로 신호를 계산하고 T+1 시가 또는 종가에 체결해 미래참조 편향을 방지합니다.' },
          { term: 'Commission / Slippage', description: '수수료와 예상 체결가격 불리함을 각각 백테스트에 반영합니다.' },
          { term: 'CAGR / Total return', description: '연복리수익률과 전체 누적수익률입니다.' },
          { term: 'Maximum drawdown', description: '과거 고점에서 경험한 최대 손실폭입니다.' },
          { term: 'Sharpe / Sortino', description: '전체 변동성 및 하방 변동성 대비 수익 효율입니다.' },
          { term: 'Ulcer index', description: '낙폭의 깊이와 지속기간을 함께 반영하며 낮을수록 좋습니다.' },
          { term: 'Rebalances', description: '목표 배분이 바뀌어 실제 매매가 발생한 횟수입니다.' },
          { term: 'Strategy Equity / Recent Rebalances', description: '자산가치 변화와 신호일·익일 체결일·회전율·비용을 보여줍니다.' },
        ],
      },
    ],
    notice: 'QLD와 TQQQ의 상장 이전 구간은 일간 레버리지와 운용보수를 적용한 합성 데이터입니다. ^NDX 장기 결과는 배당 없는 가격지수 프록시이며 실제 ETF 총수익률과 다릅니다. 현재 엔진은 목표 비중을 제시할 뿐 주문을 자동 제출하지 않습니다.',
  },
  en: {
    eyebrow: 'Leverage Engine guide',
    title: 'How does the Tripod strategy work?',
    summary: 'This is a rule-based allocation strategy adapted to emulate the core ideas of time-series momentum and trend following. Rather than forecasting individual stocks, it switches among 3x, 1.5x, and cash exposure using the NASDAQ-100’s own trend, volatility, and drawdown.',
    sections: [
      {
        title: 'Background and regime detection',
        body: 'The regime becomes BULL above 101% of SMA-250 and BEAR below 95% of SMA-250. Between those thresholds, it retains the previous state to reduce whipsaw trading. VIX MA-10 measures smoothed short-term fear, while 52-week drawdown measures the decline from the trailing 250-day high.',
      },
      {
        title: 'Current signal area',
        items: [
          { term: 'Current regime', description: 'The BULL or BEAR state determined by the long-term trend.' },
          { term: 'Target allocation', description: 'The target portfolio calculated from today’s close and intended for the next trading day.' },
          { term: 'QQQ / QLD / TQQQ / CASH', description: 'Target asset weights. A 50% QQQ and 50% QLD mix has approximately 1.5x theoretical exposure.' },
          { term: 'Benchmark close', description: 'The QQQ or NASDAQ-100 close used for regime detection.' },
          { term: 'SMA 250', description: 'The roughly one-year moving average used as the trend-following baseline.' },
          { term: 'VIX MA 10', description: 'The ten-day VIX average, smoothing one-day volatility shocks.' },
          { term: '52-week drawdown', description: 'The current decline from the highest close in the previous 250 trading days.' },
        ],
      },
      {
        title: 'Tripod allocation rules',
        items: [
          { term: 'Strong bull', description: 'BULL, VIX MA-10 < 28, and drawdown below 9% selects 100% TQQQ.' },
          { term: 'Risky bull', description: 'BULL with VIX MA-10 ≥ 28 or drawdown ≥ 9% selects 50% QQQ + 50% QLD.' },
          { term: 'Calmer bear', description: 'BEAR with VIX MA-10 < 18 selects 50% QQQ + 50% QLD.' },
          { term: 'Fearful bear', description: 'BEAR with VIX MA-10 ≥ 18 selects 100% CASH.' },
        ],
      },
      {
        title: 'Backtest console and results',
        items: [
          { term: 'Benchmark', description: 'QQQ is closer to the tradable ETF; ^NDX provides a longer price-index proxy history.' },
          { term: 'T+1 execution', description: 'A signal from the T close executes at the T+1 open or close to prevent look-ahead bias.' },
          { term: 'Commission / Slippage', description: 'Models explicit fees and adverse execution-price movement.' },
          { term: 'CAGR / Total return', description: 'Annualized compound growth and cumulative return.' },
          { term: 'Maximum drawdown', description: 'The largest historical loss from a prior equity peak.' },
          { term: 'Sharpe / Sortino', description: 'Return efficiency relative to total volatility and downside volatility.' },
          { term: 'Ulcer index', description: 'Combines drawdown depth and duration; lower is better.' },
          { term: 'Rebalances', description: 'The number of allocation changes that generated trades.' },
          { term: 'Strategy Equity / Recent Rebalances', description: 'Shows portfolio value and each signal date, next-day execution, turnover, and modeled cost.' },
        ],
      },
    ],
    notice: 'Pre-inception QLD and TQQQ history is synthetic, using daily leverage and fund expenses. Long ^NDX results use a price-index proxy without dividends and are not investable ETF total returns. The engine provides target weights and does not submit orders automatically.',
  },
}

function AnalysisHelp({ guide, label }: { guide: Record<Language, Guide>; label: string }) {
  const [open, setOpen] = useState(false)
  const [language, setLanguage] = useState<Language>('ko')
  const content = guide[language]

  return <>
    <button className="analysis-help-button" title={label} aria-label={label} onClick={() => setOpen(true)}><CircleHelp size={19} /></button>
    {open && <div className="analysis-help-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
      <section className="analysis-help-dialog" role="dialog" aria-modal="true" aria-labelledby="analysis-help-title" onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false) }}>
        <header>
          <div><span>{content.eyebrow}</span><h2 id="analysis-help-title">{content.title}</h2></div>
          <div className="analysis-help-actions">
            <div className="language-switch" aria-label="Guide language">
              <button className={language === 'ko' ? 'active' : ''} onClick={() => setLanguage('ko')}>한국어</button>
              <button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>English</button>
            </div>
            <button className="analysis-help-close" aria-label="Close guide" autoFocus onClick={() => setOpen(false)}><X size={19} /></button>
          </div>
        </header>
        <div className="analysis-help-content">
          <p className="analysis-help-summary">{content.summary}</p>
          {content.sections.map((section) => <section key={section.title}>
            <h3>{section.title}</h3>
            {section.body && <p>{section.body}</p>}
            {section.items && <dl>{section.items.map((item) => <div key={item.term}><dt>{item.term}</dt><dd>{item.description}</dd></div>)}</dl>}
          </section>)}
          <aside>{content.notice}</aside>
        </div>
      </section>
    </div>}
  </>
}

export function PredictionHelp() {
  return <AnalysisHelp guide={predictionGuide} label="Open AI Prediction guide" />
}

export function LeverageHelp() {
  return <AnalysisHelp guide={leverageGuide} label="Open Leverage Engine guide" />
}