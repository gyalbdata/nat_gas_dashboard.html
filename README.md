# 🔥 Natural Gas Price Model & Storage Contract Valuation

A two-part quantitative finance project completed as part of the **JPMorgan Chase & Co. Quantitative Research Virtual Experience**. The project models natural gas prices and uses that model to price a gas storage trading contract — the same type of analysis a commodities trading desk uses to evaluate "buy low, store, sell high" deals.

**[→ Price Model Dashboard](https://gyalbdata.github.io/index.html/)**
**[→ Storage Contract Dashboard](https://gyalbdata.github.io/storage_contract_dashboard.html/)**

---

## 📌 Project Overview

This simulation is broken into two connected tasks:

| Task | What it solves |
|---|---|
| **1. Price Estimation Model** | Given historical natural gas prices, estimate the price on any date — past or up to a year in the future |
| **2. Storage Contract Pricing Model** | Given that price model, calculate the value of a gas storage trading contract — what a trading desk should be willing to pay a client to enter the deal |

The second task builds directly on the first: you can't value a storage contract without first knowing what the gas is worth on the dates the contract specifies.

---

## 1️⃣ Natural Gas Price Estimation

### The problem
Natural gas prices follow two consistent patterns: a long-term upward trend, and a seasonal cycle tied to winter heating demand. The goal is to model both, so that the price on **any date** can be estimated — not just the dates we have data for.

### The approach
Prices are modeled as a linear trend combined with a two-harmonic seasonal (Fourier) component, fit by ordinary least squares on 48 month-end observations (31 Oct 2020 – 30 Sep 2024):

```
price(t) = a + b·t
         + c₁·sin(2π·t / 365.25) + c₂·cos(2π·t / 365.25)
         + c₃·sin(4π·t / 365.25) + c₄·cos(4π·t / 365.25)
```

| Date falls... | Method used |
|---|---|
| Within the historical window | Linear interpolation between the two nearest real observations |
| Up to 1 year beyond the last observation | Extrapolated using the fitted trend + seasonal model |
| Outside that window | Not supported — raises an error rather than guessing |

📊 **[View the dashboard](https://gyalbdata.github.io/index.html/)** — price history, forward curve, seasonal demand cycle, and a live date-based estimator.

📄 Code: [`gas_price_model.py`](./gas_price_model.py)

```python
from gas_price_model import estimate_price

estimate_price("2022-06-15")   # interpolated
estimate_price("2025-03-31")   # extrapolated
```

---

## 2️⃣ Storage Contract Valuation

### The problem
A client wants to inject gas into storage on certain dates (buying it cheap) and withdraw it on other dates (selling it once prices rise) — but every step has real costs and physical limits. The contract's value isn't just "sell price minus buy price" — it has to account for everything involved in actually executing the trade.

### Cash flows considered

```
Contract value =  (revenue from withdrawals)
                 − (cost of injections)
                 − (storage cost × months held)
                 − (injection/withdrawal handling fees)
                 − (other transaction costs, e.g. transport)
```

### Inputs to the model
1. Injection dates
2. Withdrawal dates
3. Purchase/sale price on each date
4. Maximum injection/withdrawal rate (the "speed limit" — how fast gas can physically move in or out)
5. Maximum storage volume (the facility's total capacity)
6. Storage costs

### Why the rate and volume limits matter
These two inputs aren't part of the cash-flow math — they're a **feasibility check**. The pricing formula can return a profitable number, but if the deal would require moving more gas per day than the facility's pumps allow, or storing more than the tank can hold, that deal is **not physically possible** — and the model rejects it rather than silently returning a number for a trade that could never actually be executed.

📊 **[View the dashboard](https://gyalbdata.github.io/storage_contract_dashboard.html/)** — editable injection/withdrawal schedule, live contract value, storage volume over time, and cumulative cash flow.

📄 Code: [`storage_contract_pricer.py`](./storage_contract_pricer.py)

```python
from storage_contract_pricer import price_storage_contract

result = price_storage_contract(
    injection_dates=["2023-06-30"],
    withdrawal_dates=["2023-12-31"],
    injection_prices=[10.90],
    withdrawal_prices=[12.80],
    injection_volumes=[1_000_000],
    withdrawal_volumes=[1_000_000],
    max_injection_withdrawal_rate=1_000_000,
    max_storage_volume=1_000_000,
    storage_cost_per_month=80_000,
    injection_withdrawal_cost_per_unit=0.01,
    other_transaction_cost=50_000,
)
print(result.summary())
```

---

## 🧪 Validation approach

Every output in this project was checked against an independently calculated expected value before being trusted — not just assumed correct because the code ran:

- **Hand-calculated sanity checks** — e.g. buying and selling at the same price with zero costs must return exactly $0
- **Edge-case tests** — injecting beyond capacity, withdrawing beyond rate limits, or selling gas never injected all correctly raise errors instead of returning a number
- **Cross-checking the dashboard's JavaScript logic against the Python model's output**, to confirm both implementations agree

---

## 📁 Repository contents

| File | Description |
|---|---|
| [`gas_price_model.py`](./gas_price_model.py) | Price estimation model (Task 1) |
| [`storage_contract_pricer.py`](./storage_contract_pricer.py) | Storage contract valuation model (Task 2) |
| [`index.html`](./index.html) | Interactive price model dashboard |
| [`storage_contract_dashboard.html`](./storage_contract_dashboard.html) | Interactive storage contract dashboard |
| `Nat_Gas.csv` | Historical month-end natural gas prices (31 Oct 2020 – 30 Sep 2024) |

---

## ⚙️ Usage

```bash
pip install pandas numpy
```

> Update `CSV_PATH` in `gas_price_model.py` to point to wherever `Nat_Gas.csv` is on your machine.

---

## ⚠️ Disclaimer

This project was built as part of a training/educational simulation (JPMorgan Chase & Co. Quantitative Research Virtual Experience). It is a prototype for learning purposes only — not financial advice, and not validated for production trading use.
