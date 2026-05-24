# Punokawan V2 — Autonomous XAUUSD Trading System

Sistem trading otonom berbasis MCP (Model Context Protocol) untuk scalping XAUUSD.
4 server khusus + AI orchestrator dengan 8-dimensi confluence scoring.

## Arsitektur

```
orchestrator (decision maker)
    │
    ├── mcp-market-analysis (:8082)   → Indikator, SMC, candlestick, backtest
    ├── mcp-risk-guardrail  (:8084)   → 11 validasi risiko deterministik
    ├── mcp-learning-self   (:8083)   → Trade journal + avoidance database
    └── mcp-metatrader-ext  (:8081)   → Lot sizing + terminal status
            │
            └── MT5 Terminal (harus running)
```

## Quick Start

### 1. Prasyarat

- Python 3.10+ terinstall
- MetaTrader 5 terminal terinstall & login
- Git (opsional, untuk clone)

### 2. Install dependencies

```powershell
pip install mcp mplfinance backtesting chromadb sentence-transformers optuna beautifulsoup4 requests Pillow MetaTrader5 pandas
```

> Note: `pandas-ta` tidak diperlukan — semua indikator diimplementasikan pure numpy.

### 3. Konfigurasi .env

```powershell
copy .env.example .env
notepad .env
```

Isi minimal:
```ini
# Lot sizing — atur sesuai keinginan
LOT_MODE=FIXED
FIXED_LOT_SIZE=0.05

# Symbol auto-detect (biarkan AUTO)
SYMBOL=XAUUSD
ACCOUNT_TYPE=AUTO
```

**Mode Lot:**
| Mode | Keterangan |
|------|-----------|
| `FIXED` | Pakai `FIXED_LOT_SIZE` langsung (default 0.05) |
| `RISK_PCT` | Hitung lot dari `RISK_PER_TRADE_PCT`% equity + jarak SL |
| `KELLY` | Kelly Criterion — perlu win rate historis |

**Symbol Auto-Detect:**
- `ACCOUNT_TYPE=AUTO` → deteksi otomatis: cent akun pakai `XAUUSDc`, USD pakai `XAUUSD`
- `ACCOUNT_TYPE=MANUAL` → pakai symbol dari `SYMBOL=` apa adanya

### 4. Jalankan MCP Servers

```powershell
# Terminal 1: metatrader-ext
cd "D:\Punokawan V2\mcp-metatrader-ext"
$env:PYTHONPATH = "D:\Punokawan V2\mcp-metatrader-ext\src"
python -m metatrader_mcp_ext.server --port 8081

# Terminal 2: market-analysis
cd "D:\Punokawan V2\mcp-market-analysis"
$env:PYTHONPATH = "D:\Punokawan V2\mcp-market-analysis\src"
python -m market_analysis_server.server --port 8082

# Terminal 3: learning-self
cd "D:\Punokawan V2\mcp-learning-self"
$env:PYTHONPATH = "D:\Punokawan V2\mcp-learning-self\src"
python -m learning_server.server --port 8083

# Terminal 4: risk-guardrail
cd "D:\Punokawan V2\mcp-risk-guardrail"
$env:PYTHONPATH = "D:\Punokawan V2\mcp-risk-guardrail\src"
python -m risk_guardrail_server.server --port 8084
```

Atau pakai satu command:
```powershell
D:\Punokawan V2\start_all.bat
```

### 5. Jalankan Orchestrator

```powershell
cd "D:\Punokawan V2"
$env:PYTHONPATH = "D:\Punokawan V2"

# Single cycle (test):
python -m orchestrator --force

# Autonomous loop (live trading):
python -m orchestrator --loop 300

# Loop dengan AI consultation (DeepSeek):
$env:DEEPSEEK_API_KEY = "sk-xxx"
python -m orchestrator --loop 300 --ai
```

**Flag:**
| Flag | Keterangan |
|------|-----------|
| `--loop N` | Loop setiap N detik (default: single run) |
| `--force` | Skip weekend/off-hours check (testing) |
| `--ai` | Konsultasi DeepSeek sebelum eksekusi |
| `--symbol XAUUSD` | Override symbol |

## Alur Trading Cycle

```
[1/5] Market Analysis
      ├─ Multi-TF indicators (M15, H1, H4, D1)
      ├─ SMC: Order Blocks, FVG, Swing Points, Sweeps
      ├─ Candlestick patterns (8 pola)
      └─ Account info + symbol detect

[2/5] Scoring (0-10)
      ├─ BOS Confirmation        +2
      ├─ Order Block Reaction    +2
      ├─ Multi-TF Alignment      +2
      ├─ Clean R:R Ratio         +2
      ├─ Candlestick Patterns    +1
      ├─ Divergence Detection    +1
      ├─ FVG Magnet              +1
      └─ Sweep Confirmation      +1

[3/5] Risk Validation (11 checks)
      ├─ Lot size, SL distance, risk %, margin
      ├─ Daily drawdown limit
      ├─ Spread + latency check
      └─ News blackout

[4/5] Avoidance Database
      └─ ChromaDB vector similarity >80% → BLOCK

[5/5] Decision
      ├─ Score >= 6 + Risk OK + No avoidance → EXECUTE
      │   └─ Write ai_directive.json → MT5 bridge executes
      └─ Otherwise → SKIP / BLOCKED
```

## MT5 Execution Bridge

Sistem menulis `ai_directive.json` ke `C:\Users\Riri\Documents\`.
Bridge `xauusd_mt5_bridge.py` di folder Documents membaca file ini dan eksekusi ke MT5.

Jalankan bridge secara terpisah:
```powershell
python C:\Users\Riri\Documents\xauusd_mt5_bridge.py --cron
```

## Output & Monitoring

**Trade Journal:** SQLite di `D:\Punokawan V2\data\trading_journal.db`
**Avoidance DB:** ChromaDB di `D:\Punokawan V2\data\chromadb\`
**Chart Images:** `D:\Punokawan V2\charts\`
**Logs:** `D:\Punokawan V2\logs\`

**Kill Switch:** Jika daily loss limit tercapai, file `kill_switch.flag` dibuat.
Hapus file untuk reset.

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError` | Set `$env:PYTHONPATH` ke folder `src` masing-masing server |
| Server tidak konek | Cek `curl http://127.0.0.1:8082/sse` — harus respon |
| MT5 tidak terdeteksi | Pastikan Terminal MT5 running & login |
| Score selalu 3.0 | Weekend market — tunggu Senin, atau signal memang lemah |
| Lot fix error | Cek `LOT_MODE=FIXED` dan `FIXED_LOT_SIZE` di `.env` |
| Spread BLOCKED | Spread >3 pips — normal saat news/opening |
