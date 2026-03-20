# AutoQuant 리팩토링 Phase 1-6 완벽 가이드

> **중요:** 각 Phase는 독립적으로 완료 가능하며, 언제든지 중단/재개할 수 있습니다.  
> 연속 2-3주 작업이 **아니라**, 총 작업 시간이 70시간 정도 소요됩니다.  
> 원하는 시간에 조금씩 진행하세요. Git 커밋이 체크포인트 역할을 합니다.

---

## 전체 타임라인 요약

| Phase | 설명 | 예상 시간 | 누적 시간 | 중단 가능? |
|-------|------|----------|----------|-----------|
| **Phase 1** | Domain models 생성 | 1시간 | 1h | ✅ 파일 단위 |
| **Phase 2** | Adapters 생성 (병렬 API) | 6시간 | 7h | ✅ 파일 단위 |
| **Phase 3** | Services 추출 | 15시간 | 22h | ✅ 파일 단위 |
| **Phase 4** | UI 재구성 | 12시간 | 34h | ✅ 탭 단위 |
| **Phase 5** | AI 예측 기능 | 30시간 | 64h | ✅ 하위 단계별 |
| **Phase 6** | Legacy 제거 + 테스트 | 6시간 | **70h** | ✅ 테스트별 |

**총 예상 시간: 70시간 (실제 달력으로는 2-8주, 당신의 스케줄에 따라)**

---

## Phase 1: Domain Models 추출 (Quick - 1시간)

### 목표
비즈니스 개념을 순수 Python 클래스로 정의 (Streamlit 의존성 제거)

### 작업 내용

#### 1-1. domain/ticker.py 생성
```python
from enum import Enum
from dataclasses import dataclass

class Sector(Enum):
    TECH = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    CONSUMER = "consumer"
    INDUSTRIAL = "industrial"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class Ticker:
    symbol: str
    sector: Sector
    risk_level: RiskLevel
    
    def __str__(self):
        return f"{self.symbol} ({self.sector.value}, {self.risk_level.value})"
```

#### 1-2. domain/position.py 생성
```python
from dataclasses import dataclass
from typing import List
from datetime import datetime
from domain.ticker import Ticker

@dataclass
class Position:
    ticker: str
    quantity: int
    buy_price: float
    current_price: float
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def pnl_dollars(self) -> float:
        return (self.current_price - self.buy_price) * self.quantity
    
    @property
    def pnl_percent(self) -> float:
        return ((self.current_price - self.buy_price) / self.buy_price) * 100

@dataclass
class Portfolio:
    positions: List[Position]
    cash: float
    
    @property
    def total_value(self) -> float:
        return sum(p.market_value for p in self.positions) + self.cash
    
    @property
    def invested_value(self) -> float:
        return sum(p.quantity * p.buy_price for p in self.positions)
    
    def to_dataframe(self):
        """Streamlit data_editor용 DataFrame 변환"""
        import pandas as pd
        return pd.DataFrame([{
            "Ticker": p.ticker,
            "Quantity": p.quantity,
            "Buy Price": p.buy_price,
            "Current Price": p.current_price,
            "Mkt Value": p.market_value,
            "P/L ($)": p.pnl_dollars,
            "P/L (%)": p.pnl_percent
        } for p in self.positions])

@dataclass
class Order:
    ticker: str
    action: str  # "BUY" or "SELL"
    quantity: int
    price: float
    timestamp: datetime
    fee: float = 0.0
    
    @property
    def total_cost(self) -> float:
        """수수료 포함 총 비용"""
        return (self.price * self.quantity) + self.fee
```

#### 1-3. domain/prediction.py 생성
```python
from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class PredictionRequest:
    ticker: str
    horizon: str  # "1 day", "1 week", "1 month"
    include_news: bool = True
    include_indicators: bool = True

@dataclass
class PredictionResult:
    ticker: str
    current_price: float
    predicted_price: float
    confidence: float  # 0-100
    reasoning: str
    chart_data: Optional[pd.DataFrame] = None
    
    @property
    def change_dollars(self) -> float:
        return self.predicted_price - self.current_price
    
    @property
    def change_percent(self) -> float:
        return (self.change_dollars / self.current_price) * 100
```

### 완료 조건
- [ ] `domain/__init__.py` 생성 (빈 파일)
- [ ] `domain/ticker.py` 생성 완료
- [ ] `domain/position.py` 생성 완료
- [ ] `domain/prediction.py` 생성 완료
- [ ] 모든 클래스에 `import streamlit` 없음 확인
- [ ] 커밋: `feat(domain): add core domain models`

### 중단/재개 시나리오
```
시작: "Phase 1 시작해줘"
중단 (파일 1개 완료): "ticker.py까지만 커밋해줘"
재개: "Phase 1 이어서 해줘" → position.py부터 시작
```

### 예상 시간
- ticker.py: 10분
- position.py: 20분
- prediction.py: 15분
- 테스트/검토: 15분
- **총: 1시간**

---

## Phase 2: Adapters 추출 (Short - 6시간)

### 목표
외부 서비스(yfinance, Supabase, News API) 호출을 래핑하고 병렬 처리 구현

### 작업 내용

#### 2-1. adapters/market_data.py 생성
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
import pandas as pd
from typing import List, Dict

class MarketDataAdapter:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
    
    def fetch_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """여러 티커의 현재 가격을 병렬로 가져옴"""
        def _fetch_single(ticker: str) -> tuple:
            try:
                data = yf.Ticker(ticker).history(period="1d")
                if data.empty:
                    return (ticker, None)
                return (ticker, data["Close"].iloc[-1])
            except Exception as e:
                print(f"Warning: Failed to fetch {ticker}: {e}")
                return (ticker, None)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_fetch_single, t): t for t in tickers}
            results = {}
            for future in as_completed(futures):
                ticker, price = future.result()
                if price is not None:
                    results[ticker] = price
        
        return results
    
    def fetch_historical_data(self, ticker: str, period: str = "1mo", 
                             interval: str = "1d") -> pd.DataFrame:
        """단일 티커의 과거 데이터 가져옴"""
        try:
            return yf.Ticker(ticker).history(period=period, interval=interval)
        except Exception as e:
            print(f"Error fetching history for {ticker}: {e}")
            return pd.DataFrame()
    
    def fetch_ticker_info(self, ticker: str) -> dict:
        """티커 정보 (섹터, 산업 등) 가져옴"""
        try:
            info = yf.Ticker(ticker).info
            return {
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "marketCap": info.get("marketCap", 0)
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {"sector": "Unknown", "industry": "Unknown", "marketCap": 0}
```

#### 2-2. adapters/db_client.py 생성
```python
from supabase import create_client, Client
from typing import List, Optional
from domain.position import Position, Order
import pandas as pd

class DBClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    def fetch_positions(self, user_id: str = "default") -> List[Position]:
        """사용자의 포지션 가져옴"""
        try:
            response = self.client.table("holdings").select("*").eq("user_id", user_id).execute()
            return [Position(
                ticker=row["ticker"],
                quantity=row["quantity"],
                buy_price=row["buy_price"],
                current_price=0.0  # 현재가는 market_data에서 조회
            ) for row in response.data]
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def save_positions(self, user_id: str, positions: List[Position]) -> bool:
        """포지션 저장 (기존 삭제 후 재생성)"""
        try:
            # 기존 데이터 삭제
            self.client.table("holdings").delete().eq("user_id", user_id).execute()
            
            # 새 데이터 삽입
            data = [{
                "user_id": user_id,
                "ticker": p.ticker,
                "quantity": p.quantity,
                "buy_price": p.buy_price
            } for p in positions]
            
            self.client.table("holdings").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving positions: {e}")
            return False
    
    def fetch_orders(self, user_id: str = "default") -> List[Order]:
        """주문 히스토리 가져옴"""
        try:
            response = self.client.table("orders").select("*").eq("user_id", user_id).execute()
            return [Order(
                ticker=row["ticker"],
                action=row["action"],
                quantity=row["quantity"],
                price=row["price"],
                timestamp=row["timestamp"],
                fee=row.get("fee", 0.0)
            ) for row in response.data]
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def save_order(self, user_id: str, order: Order) -> bool:
        """주문 저장"""
        try:
            data = {
                "user_id": user_id,
                "ticker": order.ticker,
                "action": order.action,
                "quantity": order.quantity,
                "price": order.price,
                "timestamp": order.timestamp.isoformat(),
                "fee": order.fee
            }
            self.client.table("orders").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving order: {e}")
            return False
```

#### 2-3. adapters/news_provider.py 생성
```python
from typing import List, Dict
from datetime import datetime, timedelta
import requests

class NewsProvider:
    """뉴스 API 래퍼 (미래 AI 예측용)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        # NewsAPI, Alpha Vantage, 또는 무료 RSS 선택
    
    def fetch_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """티커 관련 뉴스 가져옴 (최근 N일)"""
        # 임시 구현: Phase 5에서 실제 API 연동
        return []
    
    def get_sentiment(self, article: Dict) -> float:
        """뉴스 감정 분석 (-1: 부정, 0: 중립, 1: 긍정)"""
        # 임시 구현: Phase 5에서 FinBERT 또는 키워드 기반 구현
        return 0.0
```

### 완료 조건
- [ ] `adapters/__init__.py` 생성
- [ ] `adapters/market_data.py` 생성 (병렬 API 구현 포함)
- [ ] `adapters/db_client.py` 생성
- [ ] `adapters/news_provider.py` 생성 (스텁)
- [ ] 병렬 가격 조회 테스트 (5개 티커 0.5초 이내)
- [ ] 커밋: `feat(adapters): add external service adapters with parallel fetching`

### 중단/재개 시나리오
```
시작: "Phase 2 시작해줘"
중단 (파일 1개 완료): "market_data.py까지만 커밋해줘"
중단 (병렬 구현 전): "ThreadPoolExecutor는 나중에. 일단 순차 버전 커밋해줘"
재개: "Phase 2 이어서 해줘" → db_client.py부터 또는 병렬 구현 추가
```

### 예상 시간
- market_data.py (순차): 1시간
- market_data.py (병렬 추가): 2시간
- db_client.py: 2시간
- news_provider.py (스텁): 30분
- 테스트: 30분
- **총: 6시간**

---

## Phase 3: Services 추출 (Medium - 15시간)

### 목표
비즈니스 로직을 Streamlit에서 완전히 분리 (가장 중요한 단계!)

### 작업 내용

#### 3-1. services/portfolio_service.py 생성
```python
import streamlit as st
import pandas as pd
from typing import List, Dict
from domain.position import Position, Portfolio
from domain.ticker import Ticker, RiskLevel, Sector
from adapters.db_client import DBClient
from adapters.market_data import MarketDataAdapter

class PortfolioService:
    def __init__(self, db: DBClient, market: MarketDataAdapter):
        self.db = db
        self.market = market
    
    @st.cache_data(ttl=300)  # 5분 캐시
    def get_portfolio(_self, user_id: str = "default") -> Portfolio:
        """사용자의 전체 포트폴리오 조회 (현재가 포함)"""
        # DB에서 포지션 가져오기
        positions = _self.db.fetch_positions(user_id)
        
        if not positions:
            return Portfolio(positions=[], cash=10000.0)
        
        # 현재가 조회 (병렬)
        tickers = [p.ticker for p in positions]
        current_prices = _self.market.fetch_current_prices(tickers)
        
        # 포지션 업데이트
        for position in positions:
            position.current_price = current_prices.get(position.ticker, position.buy_price)
        
        return Portfolio(positions=positions, cash=0.0)  # cash는 DB에서 조회
    
    def update_positions(self, user_id: str, edited_df: pd.DataFrame) -> bool:
        """편집된 DataFrame을 DB에 저장"""
        positions = [Position(
            ticker=row["Ticker"],
            quantity=int(row["Quantity"]),
            buy_price=float(row["Buy Price"]),
            current_price=float(row["Current Price"])
        ) for _, row in edited_df.iterrows()]
        
        return self.db.save_positions(user_id, positions)
    
    def label_risk(self, ticker: Ticker) -> RiskLevel:
        """티커의 위험도 계산 (섹터 기반)"""
        high_risk_sectors = [Sector.TECH, Sector.ENERGY]
        low_risk_sectors = [Sector.UTILITIES, Sector.CONSUMER]
        
        if ticker.sector in high_risk_sectors:
            return RiskLevel.HIGH
        elif ticker.sector in low_risk_sectors:
            return RiskLevel.LOW
        else:
            return RiskLevel.MEDIUM
    
    def calculate_allocation(self, portfolio: Portfolio) -> Dict[str, float]:
        """섹터별/티커별 비중 계산"""
        total = portfolio.total_value
        
        ticker_allocation = {
            p.ticker: (p.market_value / total) * 100
            for p in portfolio.positions
        }
        
        return ticker_allocation
```

#### 3-2. services/trading_service.py 생성
```python
import streamlit as st
from datetime import datetime
from typing import Dict
from domain.position import Order, Position
from adapters.db_client import DBClient
from adapters.market_data import MarketDataAdapter

class TradingService:
    def __init__(self, db: DBClient, market: MarketDataAdapter):
        self.db = db
        self.market = market
        self.fee_rate = 0.001  # 0.1% 수수료
    
    def execute_order(self, user_id: str, order: Order, cash_balance: float) -> Dict:
        """주문 실행 (페이퍼 트레이딩)"""
        # 수수료 계산
        order.fee = order.price * order.quantity * self.fee_rate
        
        # 매수 검증
        if order.action == "BUY":
            if cash_balance < order.total_cost:
                return {
                    "status": "FAILED",
                    "reason": "Insufficient cash",
                    "required": order.total_cost,
                    "available": cash_balance
                }
        
        # 매도 검증
        elif order.action == "SELL":
            positions = self.db.fetch_positions(user_id)
            position = next((p for p in positions if p.ticker == order.ticker), None)
            
            if not position or position.quantity < order.quantity:
                return {
                    "status": "FAILED",
                    "reason": "Insufficient shares",
                    "required": order.quantity,
                    "available": position.quantity if position else 0
                }
        
        # 주문 저장
        self.db.save_order(user_id, order)
        
        return {
            "status": "SUCCESS",
            "order": order,
            "remaining_cash": cash_balance - order.total_cost if order.action == "BUY" else cash_balance + (order.price * order.quantity - order.fee)
        }
    
    def calculate_pnl(self, positions: List[Position]) -> Dict:
        """총 P/L 계산"""
        total_pnl = sum(p.pnl_dollars for p in positions)
        total_invested = sum(p.quantity * p.buy_price for p in positions)
        total_market_value = sum(p.market_value for p in positions)
        
        return {
            "total": total_pnl,
            "total_percent": (total_pnl / total_invested * 100) if total_invested > 0 else 0,
            "invested": total_invested,
            "market_value": total_market_value,
            "by_ticker": {p.ticker: p.pnl_dollars for p in positions}
        }
```

#### 3-3. services/prediction_service.py 생성 (스텁)
```python
from domain.prediction import PredictionRequest, PredictionResult
from adapters.market_data import MarketDataAdapter
from adapters.news_provider import NewsProvider

class PredictionService:
    """AI 가격 예측 서비스 (Phase 5에서 완전 구현)"""
    
    def __init__(self, market: MarketDataAdapter, news: NewsProvider):
        self.market = market
        self.news = news
    
    def predict_price(self, request: PredictionRequest) -> PredictionResult:
        """가격 예측 (현재는 스텁)"""
        # 임시: 현재가 ±5% 랜덤 예측
        current_price = self.market.fetch_current_prices([request.ticker])[request.ticker]
        
        return PredictionResult(
            ticker=request.ticker,
            current_price=current_price,
            predicted_price=current_price * 1.05,  # 임시: +5%
            confidence=50.0,
            reasoning="Placeholder prediction (Phase 5 will implement real AI)"
        )
```

### 완료 조건
- [ ] `services/__init__.py` 생성
- [ ] `services/portfolio_service.py` 생성 (캐싱 포함)
- [ ] `services/trading_service.py` 생성
- [ ] `services/prediction_service.py` 생성 (스텁)
- [ ] 모든 서비스에 `import streamlit as st` 없음 (캐싱 제외)
- [ ] `portfolio.py`의 모든 비즈니스 로직이 service로 이동 확인
- [ ] 커밋: `feat(services): extract business logic from UI`

### 중단/재개 시나리오
```
시작: "Phase 3 시작해줘"
중단 (파일 1개 완료): "portfolio_service.py까지만 커밋해줘"
중단 (함수 일부 완료): "get_portfolio()까지만 구현하고 커밋해줘"
재개: "Phase 3 이어서 해줘" → update_positions()부터 또는 trading_service.py부터
```

### 예상 시간
- portfolio_service.py: 5시간
- trading_service.py: 6시간
- prediction_service.py (스텁): 1시간
- 캐싱 적용 및 테스트: 3시간
- **총: 15시간**

---

## Phase 4: UI Layer 재구성 (Medium - 12시간)

### 목표
Streamlit 코드를 "입력 수집 + 결과 렌더링"만 하도록 단순화

### 작업 내용

#### 4-1. ui/portfolio_tab.py 생성
```python
import streamlit as st
import plotly.express as px
from services.portfolio_service import PortfolioService

def render_portfolio_tab(portfolio_service: PortfolioService):
    """Portfolio Tracking 탭 렌더링"""
    st.header("📊 Portfolio Tracking")
    
    # 새로고침 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Prices"):
            st.cache_data.clear()
            st.rerun()
    
    # 포트폴리오 조회
    portfolio = portfolio_service.get_portfolio(user_id="default")
    
    if not portfolio.positions:
        st.info("No positions yet. Add your first position below.")
        return
    
    # 포트폴리오 편집 (조건부 refresh)
    st.subheader("Your Holdings")
    
    edited_df = st.data_editor(
        portfolio.to_dataframe(),
        key="portfolio_editor",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0),
            "Buy Price": st.column_config.NumberColumn("Buy Price", format="$%.2f"),
            "Current Price": st.column_config.NumberColumn("Current Price", format="$%.2f", disabled=True),
            "Mkt Value": st.column_config.NumberColumn("Mkt Value", format="$%.2f", disabled=True),
            "P/L ($)": st.column_config.NumberColumn("P/L ($)", format="$%.2f", disabled=True),
            "P/L (%)": st.column_config.NumberColumn("P/L (%)", format="%.2f%%", disabled=True)
        }
    )
    
    # 저장 버튼 (명시적 저장만 rerun)
    if st.button("💾 Save Changes"):
        if portfolio_service.update_positions("default", edited_df):
            st.success("Portfolio saved!")
            st.rerun()
        else:
            st.error("Failed to save portfolio")
    
    # 요약 정보
    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Value", f"${portfolio.total_value:,.2f}")
    
    with col2:
        total_pnl = sum(p.pnl_dollars for p in portfolio.positions)
        st.metric("Total P/L", f"${total_pnl:,.2f}", 
                  delta=f"{(total_pnl/portfolio.invested_value)*100:.2f}%")
    
    with col3:
        st.metric("Positions", len(portfolio.positions))
    
    # 할당 차트
    st.subheader("Allocation")
    allocation = portfolio_service.calculate_allocation(portfolio)
    
    fig = px.pie(
        names=list(allocation.keys()),
        values=list(allocation.values()),
        title="Portfolio Allocation"
    )
    st.plotly_chart(fig, use_container_width=True)
```

#### 4-2. ui/paper_trading_tab.py 생성
```python
import streamlit as st
from datetime import datetime
from domain.position import Order
from services.trading_service import TradingService

def render_trading_tab(trading_service: TradingService):
    """Paper Trading 탭 렌더링"""
    st.header("📈 Paper Trading")
    
    # 세션 상태 초기화
    if "cash" not in st.session_state:
        st.session_state.cash = 10000.0
    
    # 주문 입력 폼
    st.subheader("Place Order")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.text_input("Ticker", value="AAPL").upper()
        action = st.radio("Action", ["BUY", "SELL"], horizontal=True)
    
    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1)
        price = st.number_input("Price", min_value=0.01, value=150.0, format="%.2f")
    
    # 주문 실행
    if st.button("Execute Order"):
        order = Order(
            ticker=ticker,
            action=action,
            quantity=quantity,
            price=price,
            timestamp=datetime.now()
        )
        
        result = trading_service.execute_order("default", order, st.session_state.cash)
        
        if result["status"] == "SUCCESS":
            st.success(f"✅ {action} {quantity} {ticker} @ ${price:.2f}")
            st.session_state.cash = result["remaining_cash"]
        else:
            st.error(f"❌ Order failed: {result['reason']}")
    
    # 현재 잔고
    st.subheader("Account Balance")
    st.metric("Cash", f"${st.session_state.cash:,.2f}")
    
    # P/L 표시 (portfolio와 통합 가능)
    # ... (기존 paper_trading.py 코드 참고)
```

#### 4-3. ui/prediction_tab.py 생성
```python
import streamlit as st
from domain.prediction import PredictionRequest
from services.prediction_service import PredictionService

def render_prediction_tab(prediction_service: PredictionService):
    """AI Price Prediction 탭 렌더링"""
    st.header("🔮 AI Price Prediction")
    
    st.info("This feature will be fully implemented in Phase 5. Current version shows placeholder predictions.")
    
    # 입력 폼
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.text_input("Ticker", value="AAPL").upper()
    
    with col2:
        horizon = st.selectbox("Prediction Horizon", ["1 day", "1 week", "1 month"])
    
    # 예측 실행
    if st.button("🚀 Predict Price"):
        with st.spinner("Analyzing news and indicators..."):
            request = PredictionRequest(
                ticker=ticker,
                horizon=horizon,
                include_news=True,
                include_indicators=True
            )
            
            result = prediction_service.predict_price(request)
        
        # 결과 표시
        st.subheader("Prediction Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Price", f"${result.current_price:.2f}")
        
        with col2:
            st.metric(
                "Predicted Price", 
                f"${result.predicted_price:.2f}",
                delta=f"{result.change_percent:+.2f}%"
            )
        
        with col3:
            st.metric("Confidence", f"{result.confidence:.0f}%")
        
        st.write(f"**Reasoning:** {result.reasoning}")
```

### 완료 조건
- [ ] `ui/__init__.py` 생성
- [ ] `ui/portfolio_tab.py` 생성
- [ ] `ui/paper_trading_tab.py` 생성
- [ ] `ui/prediction_tab.py` 생성
- [ ] 조건부 refresh 적용 (edit state loss 해결)
- [ ] 모든 UI 파일이 service만 호출, 비즈니스 로직 없음
- [ ] 커밋: `feat(ui): separate UI layer from business logic`

### 중단/재개 시나리오
```
시작: "Phase 4 시작해줘"
중단 (탭 1개 완료): "portfolio_tab.py까지만 커밋해줘"
재개: "Phase 4 이어서 해줘" → paper_trading_tab.py부터
```

### 예상 시간
- portfolio_tab.py: 4시간
- paper_trading_tab.py: 4시간
- prediction_tab.py: 2시간
- 조건부 refresh 적용: 2시간
- **총: 12시간**

---

## Phase 5: AI 예측 기능 구현 (Large - 30시간)

### 목표
Feature 3 (AI Price Prediction) 완전 구현

### 5-1. 뉴스 API 통합 (6시간)

#### adapters/news_provider.py 완성
```python
import requests
from typing import List, Dict
from datetime import datetime, timedelta

class NewsProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"  # 또는 Alpha Vantage
    
    def fetch_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """티커 관련 뉴스 가져옴"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "q": ticker,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "relevancy"
        }
        
        response = requests.get(f"{self.base_url}/everything", params=params)
        
        if response.status_code == 200:
            return response.json()["articles"]
        else:
            return []
    
    def get_sentiment(self, article: Dict) -> float:
        """뉴스 감정 분석"""
        # 옵션 A: 키워드 기반 (빠름)
        positive_keywords = ["profit", "growth", "bullish", "upgrade", "beat"]
        negative_keywords = ["loss", "decline", "bearish", "downgrade", "miss"]
        
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        return (pos_count - neg_count) / (pos_count + neg_count)
        
        # 옵션 B: FinBERT (더 정확, 느림)
        # from transformers import pipeline
        # sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        # result = sentiment_pipeline(text)[0]
        # return result["score"] if result["label"] == "positive" else -result["score"]
```

### 5-2. 기술적 지표 계산 (8시간)

#### services/prediction_service.py 확장 - 지표 추가
```python
import pandas as pd
import pandas_ta as ta
from typing import Dict

class PredictionService:
    # ... (기존 코드)
    
    def calculate_indicators(self, ticker: str) -> Dict[str, float]:
        """기술적 지표 계산"""
        # 과거 데이터 가져오기 (90일)
        df = self.market.fetch_historical_data(ticker, period="3mo", interval="1d")
        
        if df.empty:
            return {}
        
        # RSI 계산
        df.ta.rsi(length=14, append=True)
        rsi = df["RSI_14"].iloc[-1]
        
        # MACD 계산
        df.ta.macd(append=True)
        macd = df["MACD_12_26_9"].iloc[-1]
        macd_signal = df["MACDs_12_26_9"].iloc[-1]
        
        # Bollinger Bands
        df.ta.bbands(length=20, append=True)
        bb_upper = df["BBU_20_2.0"].iloc[-1]
        bb_lower = df["BBL_20_2.0"].iloc[-1]
        current_price = df["Close"].iloc[-1]
        
        # 이동평균
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        sma_50 = df["SMA_50"].iloc[-1]
        sma_200 = df["SMA_200"].iloc[-1]
        
        return {
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "current_price": current_price,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "volume": df["Volume"].iloc[-1],
            "avg_volume": df["Volume"].mean()
        }
    
    def generate_signals(self, indicators: Dict) -> Dict[str, str]:
        """지표 기반 매매 신호 생성"""
        signals = {}
        
        # RSI 신호
        if indicators["rsi"] > 70:
            signals["rsi"] = "OVERBOUGHT"
        elif indicators["rsi"] < 30:
            signals["rsi"] = "OVERSOLD"
        else:
            signals["rsi"] = "NEUTRAL"
        
        # MACD 신호
        if indicators["macd"] > indicators["macd_signal"]:
            signals["macd"] = "BULLISH"
        else:
            signals["macd"] = "BEARISH"
        
        # 볼린저 밴드
        price = indicators["current_price"]
        if price > indicators["bb_upper"]:
            signals["bb"] = "OVERBOUGHT"
        elif price < indicators["bb_lower"]:
            signals["bb"] = "OVERSOLD"
        else:
            signals["bb"] = "NEUTRAL"
        
        # 이동평균 크로스
        if indicators["sma_50"] > indicators["sma_200"]:
            signals["ma_cross"] = "GOLDEN_CROSS"
        else:
            signals["ma_cross"] = "DEATH_CROSS"
        
        return signals
```

### 5-3. AI 모델 구현 (12시간)

#### 옵션 A: 규칙 기반 (가장 빠름, 4시간)
```python
def predict_price(self, request: PredictionRequest) -> PredictionResult:
    """규칙 기반 예측"""
    # 1. 현재가 조회
    current_price = self.market.fetch_current_prices([request.ticker])[request.ticker]
    
    # 2. 뉴스 감정 분석
    news_sentiment = 0.0
    if request.include_news:
        articles = self.news.fetch_news(request.ticker, days=30)
        if articles:
            sentiments = [self.news.get_sentiment(a) for a in articles[:10]]
            news_sentiment = sum(sentiments) / len(sentiments)
    
    # 3. 기술적 지표
    indicators = {}
    signals = {}
    if request.include_indicators:
        indicators = self.calculate_indicators(request.ticker)
        signals = self.generate_signals(indicators)
    
    # 4. 점수 계산
    score = 0.0
    
    # 뉴스 감정 (30% 가중치)
    score += news_sentiment * 0.3
    
    # RSI (20%)
    if signals.get("rsi") == "OVERSOLD":
        score += 0.2
    elif signals.get("rsi") == "OVERBOUGHT":
        score -= 0.2
    
    # MACD (30%)
    if signals.get("macd") == "BULLISH":
        score += 0.3
    elif signals.get("macd") == "BEARISH":
        score -= 0.3
    
    # 이동평균 (20%)
    if signals.get("ma_cross") == "GOLDEN_CROSS":
        score += 0.2
    elif signals.get("ma_cross") == "DEATH_CROSS":
        score -= 0.2
    
    # 5. 가격 예측
    horizon_multiplier = {"1 day": 0.01, "1 week": 0.05, "1 month": 0.15}
    max_change = horizon_multiplier.get(request.horizon, 0.05)
    
    predicted_price = current_price * (1 + (score * max_change))
    
    # 6. 신뢰도 계산
    confidence = min(abs(score) * 100, 85)  # 최대 85%
    
    # 7. 근거 생성
    reasoning = f"""
    **News Sentiment:** {news_sentiment:.2f} ({len(articles)} articles analyzed)
    **Technical Signals:**
    - RSI: {signals.get('rsi', 'N/A')}
    - MACD: {signals.get('macd', 'N/A')}
    - MA Cross: {signals.get('ma_cross', 'N/A')}
    
    **Overall Score:** {score:.2f} (range: -1 to 1)
    """
    
    return PredictionResult(
        ticker=request.ticker,
        current_price=current_price,
        predicted_price=predicted_price,
        confidence=confidence,
        reasoning=reasoning.strip()
    )
```

#### 옵션 B: 회귀 모델 (중간, 8시간)
```python
from sklearn.linear_model import LinearRegression
import numpy as np

class PredictionService:
    def __init__(self, ...):
        # ...
        self.model = LinearRegression()
        self._train_model()
    
    def _train_model(self):
        """과거 데이터로 모델 훈련"""
        # TODO: 과거 뉴스 + 지표 → 실제 가격 변화 데이터셋 준비
        # X = [news_sentiment, rsi, macd, ...]
        # y = [price_change_percent]
        # self.model.fit(X, y)
        pass
    
    def predict_price(self, request: PredictionRequest) -> PredictionResult:
        # 특성 추출
        features = self._extract_features(request.ticker)
        
        # 예측
        predicted_change = self.model.predict([features])[0]
        
        # ...
```

#### 옵션 C: 외부 API (가장 정확, 4시간 통합)
```python
def predict_price(self, request: PredictionRequest) -> PredictionResult:
    """OpenAI GPT 또는 Alpha Vantage AI 사용"""
    # OpenAI 예시
    import openai
    
    prompt = f"""
    Based on the following data, predict the price of {request.ticker} for {request.horizon}:
    
    Current Price: ${current_price}
    News Sentiment: {news_sentiment}
    Technical Indicators: {indicators}
    
    Provide:
    1. Predicted price
    2. Confidence (0-100)
    3. Reasoning
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # 파싱 및 반환
    # ...
```

### 5-4. UI 개선 (4시간)

#### ui/prediction_tab.py 완성
```python
def render_prediction_tab(prediction_service: PredictionService):
    st.header("🔮 AI Price Prediction")
    
    # 입력 폼
    ticker = st.text_input("Ticker", value="AAPL").upper()
    horizon = st.selectbox("Horizon", ["1 day", "1 week", "1 month"])
    
    col1, col2 = st.columns(2)
    with col1:
        include_news = st.checkbox("Include News Analysis", value=True)
    with col2:
        include_indicators = st.checkbox("Include Technical Indicators", value=True)
    
    # 예측 실행
    if st.button("🚀 Predict Price"):
        request = PredictionRequest(
            ticker=ticker,
            horizon=horizon,
            include_news=include_news,
            include_indicators=include_indicators
        )
        
        with st.spinner("Analyzing..."):
            result = prediction_service.predict_price(request)
        
        # 결과 표시
        st.subheader("📊 Prediction Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Price", f"${result.current_price:.2f}")
        
        with col2:
            st.metric(
                "Predicted Price",
                f"${result.predicted_price:.2f}",
                delta=f"{result.change_percent:+.2f}%"
            )
        
        with col3:
            confidence_color = "🟢" if result.confidence > 70 else "🟡" if result.confidence > 50 else "🔴"
            st.metric("Confidence", f"{confidence_color} {result.confidence:.0f}%")
        
        # 근거 표시
        st.subheader("💡 Analysis")
        st.markdown(result.reasoning)
        
        # 차트 (선택)
        if result.chart_data is not None:
            st.plotly_chart(result.chart_data, use_container_width=True)
        
        # 예측 히스토리 (선택)
        if "prediction_history" not in st.session_state:
            st.session_state.prediction_history = []
        
        st.session_state.prediction_history.append({
            "timestamp": datetime.now(),
            "ticker": ticker,
            "predicted": result.predicted_price,
            "actual": None  # 나중에 업데이트
        })
        
        # 히스토리 표시
        if st.session_state.prediction_history:
            st.subheader("📜 Prediction History")
            st.dataframe(pd.DataFrame(st.session_state.prediction_history))
```

### 완료 조건
- [ ] 뉴스 API 연동 완료 (NewsAPI, Alpha Vantage, 또는 RSS)
- [ ] 기술적 지표 계산 완료 (RSI, MACD, Bollinger, MA)
- [ ] AI 모델 구현 (규칙/회귀/외부 API 중 택1)
- [ ] UI 완성 (예측 결과 시각화)
- [ ] 예측 정확도 최소 50% (백테스트 또는 실시간 검증)
- [ ] 커밋 3개:
  - `feat(news): integrate news API and sentiment analysis`
  - `feat(indicators): add technical indicators calculation`
  - `feat(prediction): complete AI price prediction feature`

### 중단/재개 시나리오
```
시작: "Phase 5 시작해줘"
중단 (5-1 완료): "뉴스 API 통합까지만 커밋해줘"
중단 (5-2 중간): "RSI, MACD까지만 구현하고 커밋해줘"
재개: "Phase 5 이어서 해줘" → Bollinger Bands부터 또는 5-3부터
```

### 예상 시간
- 5-1 뉴스 API: 6시간
- 5-2 기술적 지표: 8시간
- 5-3 AI 모델: 12시간 (규칙 기반 4h / 회귀 8h / 외부 API 4h)
- 5-4 UI 개선: 4시간
- **총: 30시간**

---

## Phase 6: Legacy 코드 제거 및 테스트 (Quick - 6시간)

### 목표
구 코드 정리, 새 구조로 전환, 품질 검증

### 작업 내용

#### 6-1. Legacy 코드 이동 (30분)
```bash
mkdir legacy/
git mv portfolio.py legacy/
git mv chart.py legacy/
git mv paper_trading.py legacy/
git commit -m "refactor: move legacy code to legacy/ folder"
```

#### 6-2. app.py 업데이트 (2시간)
```python
# app.py (최종 버전)
import streamlit as st
from ui.portfolio_tab import render_portfolio_tab
from ui.paper_trading_tab import render_trading_tab
from ui.prediction_tab import render_prediction_tab
from services.portfolio_service import PortfolioService
from services.trading_service import TradingService
from services.prediction_service import PredictionService
from adapters.db_client import DBClient
from adapters.market_data import MarketDataAdapter
from adapters.news_provider import NewsProvider

st.set_page_config(
    page_title="AutoQuant",
    page_icon="📊",
    layout="wide"
)

# 의존성 주입
@st.cache_resource
def get_services():
    """서비스 싱글톤 생성"""
    # Adapters
    db = DBClient(
        supabase_url=st.secrets["supabase"]["url"],
        supabase_key=st.secrets["supabase"]["key"]
    )
    market = MarketDataAdapter(max_workers=10)
    news = NewsProvider(api_key=st.secrets.get("newsapi", {}).get("key"))
    
    # Services
    return {
        "portfolio": PortfolioService(db, market),
        "trading": TradingService(db, market),
        "prediction": PredictionService(market, news)
    }

services = get_services()

# 헤더
st.title("📊 AutoQuant: AI Portfolio Optimizer")

# 탭 렌더링
tab1, tab2, tab3 = st.tabs([
    "📊 Portfolio",
    "📈 Paper Trading",
    "🔮 AI Prediction"
])

with tab1:
    render_portfolio_tab(services["portfolio"])

with tab2:
    render_trading_tab(services["trading"])

with tab3:
    render_prediction_tab(services["prediction"])
```

#### 6-3. 기본 테스트 작성 (3시간)
```python
# tests/test_portfolio_service.py
import pytest
from domain.position import Position, Portfolio
from services.portfolio_service import PortfolioService

class MockDB:
    def fetch_positions(self, user_id):
        return [Position("AAPL", 10, 150, 0)]

class MockMarket:
    def fetch_current_prices(self, tickers):
        return {"AAPL": 160.0}

def test_get_portfolio():
    service = PortfolioService(MockDB(), MockMarket())
    portfolio = service.get_portfolio("test_user")
    
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].current_price == 160.0
    assert portfolio.positions[0].pnl_dollars == 100.0  # (160-150)*10

def test_calculate_allocation():
    positions = [
        Position("AAPL", 10, 150, 160),  # $1600
        Position("GOOGL", 5, 100, 120)   # $600
    ]
    portfolio = Portfolio(positions, cash=800)
    
    service = PortfolioService(MockDB(), MockMarket())
    allocation = service.calculate_allocation(portfolio)
    
    assert allocation["AAPL"] == pytest.approx(53.33, rel=0.01)  # 1600/3000
    assert allocation["GOOGL"] == pytest.approx(20.0, rel=0.01)  # 600/3000

# tests/test_trading_service.py
from services.trading_service import TradingService
from domain.position import Order
from datetime import datetime

def test_execute_buy_order_success():
    service = TradingService(MockDB(), MockMarket())
    
    order = Order(
        ticker="AAPL",
        action="BUY",
        quantity=10,
        price=150.0,
        timestamp=datetime.now()
    )
    
    result = service.execute_order("test_user", order, cash_balance=2000.0)
    
    assert result["status"] == "SUCCESS"
    assert result["remaining_cash"] < 2000  # 수수료 포함

def test_execute_buy_order_insufficient_cash():
    service = TradingService(MockDB(), MockMarket())
    
    order = Order(
        ticker="AAPL",
        action="BUY",
        quantity=100,
        price=150.0,
        timestamp=datetime.now()
    )
    
    result = service.execute_order("test_user", order, cash_balance=1000.0)
    
    assert result["status"] == "FAILED"
    assert "Insufficient cash" in result["reason"]

# tests/test_market_data.py
from adapters.market_data import MarketDataAdapter

def test_fetch_current_prices_parallel():
    adapter = MarketDataAdapter(max_workers=5)
    tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    
    import time
    start = time.time()
    prices = adapter.fetch_current_prices(tickers)
    elapsed = time.time() - start
    
    assert len(prices) == 5
    assert all(p > 0 for p in prices.values())
    assert elapsed < 2.0  # 병렬 처리로 2초 이내
```

#### 6-4. 통합 테스트 (30분)
```bash
# 모든 기능 수동 테스트
streamlit run app.py

# 체크리스트:
# [ ] Portfolio 탭 정상 동작
# [ ] 포지션 편집 → 저장 → 새로고침 시 유지
# [ ] Paper Trading 주문 실행
# [ ] AI Prediction 예측 결과 표시
# [ ] 캐싱 동작 확인 (같은 티커 재조회 시 빠름)
```

### 완료 조건
- [ ] Legacy 코드 `legacy/` 폴더로 이동
- [ ] `app.py` 새 구조로 전환 완료
- [ ] 모든 기능 정상 작동 확인
- [ ] 최소 8개 테스트 작성 및 통과
- [ ] 커밋 2개:
  - `refactor: migrate to new architecture`
  - `test: add comprehensive service tests`

### 예상 시간
- Legacy 이동: 30분
- app.py 업데이트: 2시간
- 테스트 작성: 3시간
- 통합 테스트: 30분
- **총: 6시간**

---

# 전체 완료 후 검증

## 최종 체크리스트

### 아키텍처
- [ ] `domain/` - 순수 Python 클래스, Streamlit 의존성 없음
- [ ] `adapters/` - 외부 API 래핑, 병렬 처리 구현
- [ ] `services/` - 비즈니스 로직, 캐싱 적용
- [ ] `ui/` - Streamlit 코드만, service 호출만
- [ ] `legacy/` - 구 코드 보관

### 성능
- [ ] 5개 티커 가격 조회 < 1초 (병렬)
- [ ] 포트폴리오 조회 캐시 적중 시 < 0.1초
- [ ] Edit state loss 해결 (셀 편집 시 값 유지)

### 기능
- [ ] Portfolio Tracking - 포지션 조회/편집/저장
- [ ] Paper Trading - 주문 실행/P/L 계산
- [ ] AI Prediction - 뉴스+지표 기반 가격 예측

### 테스트
- [ ] 최소 8개 테스트 통과
- [ ] 수동 통합 테스트 완료

---

# 중단/재개 시나리오 총정리

## 시나리오 1: Phase별로 진행
```
Week 1 토요일: Phase 1, 2 (7시간)
→ 커밋: "feat(domain): ..." + "feat(adapters): ..."
→ 컴퓨터 끔

Week 2 토요일: Phase 3 (15시간) - 하루에 다 못 하면 중간에 커밋
→ 오전: portfolio_service (4시간) → 커밋
→ 점심 후 외출
→ 저녁: trading_service (6시간) → 커밋
→ 일요일: prediction_service (5시간) → 커밋

Week 3: 바쁨 (0시간)

Week 4 토요일: Phase 4 (12시간)
→ 오전: portfolio_tab (4시간) → 커밋
→ 오후: paper_trading_tab (4시간) → 커밋
→ 저녁: prediction_tab (4시간) → 커밋

Week 5-6: Phase 5 (30시간) - 여러 번 나눠서
→ 토: 뉴스 API (6시간) → 커밋
→ 일: 기술 지표 (8시간) → 커밋
→ 다음 토: AI 모델 (12시간) → 커밋
→ 다음 일: UI 완성 (4시간) → 커밋

Week 7 토요일: Phase 6 (6시간)
→ 완료!
```

## 시나리오 2: 함수 단위로 중단
```
"Phase 3 시작해줘"
→ portfolio_service.get_portfolio() 구현 중...
→ "급한 전화 왔어. get_portfolio()까지만 커밋해줘"
→ AI: [커밋] "feat(services): add portfolio_service.get_portfolio (partial)"

3일 후
→ "Phase 3 이어서 해줘"
→ AI: [git log 확인] "portfolio_service.get_portfolio() 완료됐네요. update_positions() 구현할게요"
→ 작업 재개
```

## 시나리오 3: 몇 달 후 재개
```
2026년 3월: Phase 1-3 완료
→ 여름에 바빠서 중단

2026년 9월 (6개월 후):
→ "AutoQuant 리팩토링 어디까지 했지?"
→ AI: [git log, .sisyphus/plans/ 확인]
   "Phase 3까지 완료됐네요. Phase 4 (UI 재구성)부터 시작하면 됩니다."
→ "이어서 해줘"
→ ✅ 정확히 이어서 진행
```

---

# AI가 진행 상황 파악하는 방법

## 당신이 "Phase N 어디까지 했지?" 물으면:

### Step 1: Git 히스토리 확인
```bash
git log --oneline -50 --grep="feat\\|refactor"
```

### Step 2: 파일 존재 확인
```bash
ls -la domain/
ls -la adapters/
ls -la services/
ls -la ui/
```

### Step 3: 각 파일 내용 확인
```python
# domain/position.py 열어서
# - Position 클래스 있는지
# - Portfolio 클래스 있는지
# - to_dataframe() 메서드 있는지
```

### Step 4: 요약 제공
```
현재 상태:
✅ Phase 1: 완료 (domain/ 모든 파일 존재)
✅ Phase 2: 완료 (adapters/ 모든 파일 존재, 병렬 구현 확인됨)
⏸️  Phase 3: 60% 진행
   ✅ portfolio_service.py: 완료
   ⏸️  trading_service.py: execute_order()까지 구현됨
   ⏳ prediction_service.py: 미시작

다음 단계: trading_service.calculate_pnl() 구현
이어서 할까요?
```

---

# 성공 기준

## Phase 1-6 전체 완료 시:

### 코드 품질
- [ ] 953줄 → ~1200줄 (구조화로 약간 증가, 하지만 유지보수성 10배 향상)
- [ ] 순환 의존성 0개
- [ ] Service에 `import streamlit` 0개 (캐싱 제외)

### 성능
- [ ] 포트폴리오 로딩 3-5배 빠름 (캐싱)
- [ ] Edit state loss 100% 해결

### 기능
- [ ] Portfolio, Trading 기능 유지 (100%)
- [ ] AI Prediction 신규 추가 (100%)

### 마이그레이션 준비
- [ ] Streamlit 제거해도 services/domain/adapters 동작
- [ ] FastAPI 통합 가능 (services 그대로 사용)

---

**파일 저장 완료!** 
`.sisyphus/drafts/phase-1-6-guide.md`
