# 🏍️ Two-Wheeler Sales Intelligence App

> **AI-powered dispatch planning & analytics platform for Indian two-wheeler dealerships**

---

## 📊 Features

| Module | Capability |
|--------|-----------|
| **Sales Analytics** | YoY/MoM comparison, SKU performance, colour analysis, seasonal patterns |
| **Festival Intelligence** | Panchang-based festival calendar (Diwali, Navratri, Onam…), marriage seasons, demand uplift forecasts |
| **Predictive Forecasting** | 60-day SKU-level demand forecasting with confidence intervals and festival adjustment |
| **Dispatch Planner** | Risk-scored dispatch recommendations, working capital simulation, what-if analysis |
| **Smart Alerts** | Real-time alerts for festival proximity, slow-moving stock, marriage season, year-end clearance |
| **AI Copilot** | Natural language interface to answer business questions about sales and inventory |
| **Market Intelligence** | EV trends, competitor news, fuel price impact, policy updates |

---

## 🗂️ Project Structure

```
shubham-data-analytic-app/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # App entry point & router registration
│   ├── config.py             # Settings (env-driven)
│   ├── database.py           # SQLAlchemy engine & session
│   ├── models.py             # ORM models
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── routes/               # API route handlers
│   │   ├── sales.py          # /api/sales/*
│   │   ├── forecast.py       # /api/forecast/*
│   │   ├── dispatch.py       # /api/dispatch/*
│   │   ├── festivals.py      # /api/festivals/*
│   │   ├── alerts.py         # /api/alerts/*
│   │   ├── copilot.py        # /api/copilot/*
│   │   └── market.py         # /api/market/*
│   ├── services/             # Business logic
│   │   ├── sales_analytics.py
│   │   ├── forecasting.py    # Seasonal-trend + festival adjustment
│   │   ├── festival_calendar.py  # Panchang-based calendar
│   │   ├── dispatch_planner.py   # Risk scoring & WC simulation
│   │   └── ai_copilot.py    # NL query handler
│   ├── scripts/
│   │   └── generate_sample_data.py  # 4-year realistic seed data
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React + Tailwind + Recharts
│   ├── src/
│   │   ├── App.jsx           # Router & sidebar layout
│   │   ├── components/       # Page components
│   │   └── services/api.js   # Axios API client
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── start.sh                  # One-command local dev start
└── README.md
```

---

## 🚀 Quick Start

### Option 1 – One Command (local)

```bash
bash start.sh
```

Opens:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs

### Option 2 – Docker Compose

```bash
docker-compose up --build
```

### Option 3 – Manual

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                    │
│  Dashboard │ Sales Analytics │ Forecast │ Dispatch  │
│  Festival Calendar │ Alerts │ AI Copilot │ Market   │
└──────────────────┬──────────────────────────────────┘
                   │ REST API (Axios)
┌──────────────────▼──────────────────────────────────┐
│              FastAPI Backend                        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Sales   │  │Forecast  │  │Dispatch Planner  │  │
│  │Analytics │  │Engine    │  │+ Risk Scorer     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │Festival Calendar │  │  AI Copilot              │ │
│  │(Panchang-based)  │  │(Rule-based + LLM option) │ │
│  └──────────────────┘  └──────────────────────────┘ │
│                                                     │
│              SQLite / PostgreSQL                    │
└─────────────────────────────────────────────────────┘
```

---

## 📈 Forecasting Logic

The forecasting engine uses **Seasonal Trend Decomposition**:

```
forecast(t) = base_daily_avg
            × seasonal_factor(month)    # empirical Indian market index
            × festival_multiplier(t)    # festival proximity boost
            × yoy_trend_factor          # linear YoY growth extrapolation

CI(t) = forecast(t) ± (20% + horizon_fraction × 15%)
```

**Festival multipliers**: Diwali +60%, Dhanteras +50%, Navratri +25%, Akshaya Tritiya +25%...

---

## ⚠️ Risk Scoring Formula

```
risk_score = 0.40 × (stockout_prob - overstock_prob)
           + 0.30 × stockout_prob
           + 0.20 × overstock_prob
           + 0.10 × festival_proximity_risk

risk_type:
  stockout_prob > 0.30 → "understock" 🔴
  overstock_prob > 0.35 → "overstock" 🟡
  else → "neutral" 🟢
```

---

## 🗓️ Indian Festival Calendar

| Festival | Typical Period | Demand Boost |
|----------|---------------|-------------|
| Diwali | Oct–Nov (shifts yearly) | +60% |
| Dhanteras | 2 days before Diwali | +50% |
| Navratri | Sep–Oct (9 days) | +25% |
| Dussehra | End of Navratri | +30% |
| Akshaya Tritiya | Apr–May | +25% |
| Onam | Aug–Sep (Kerala) | +35% |
| Pongal | Jan 14 (South India) | +30% |

**Marriage Seasons**: Nov–Dec (Winter) +25% | Feb–May (Spring) +20%

---

## 🔧 Configuration

Create `.env` in `backend/`:

```env
DATABASE_URL=sqlite:///./hero_sales.db
APP_NAME=Two-Wheeler Sales Intelligence
APP_ENV=development

# Optional AI integrations
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
NEWS_API_KEY=your_key

# Forecasting tuning
FORECAST_HORIZON_DAYS=60
BUFFER_STOCK_PERCENT=0.15
DEFAULT_LEAD_TIME_DAYS=21
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ML/Analytics | Pandas, NumPy, SciPy, XGBoost |
| Frontend | React 18, Vite, Tailwind CSS |
| Charts | Recharts |
| Deployment | Docker, Docker Compose |

---

## 🎯 Business Outcomes

- **Reduce dead stock** by 15–20% through risk-scored dispatch planning
- **Improve festive accuracy** by 25% with festival-adjusted forecasting
- **60-day planning horizon** with confidence intervals
- **Working capital optimisation** through simulation
- **Instant insights** via AI Copilot natural language queries
