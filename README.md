# 🔥 Natural Gas Price Model & Dashboard

Estimate natural gas purchase prices for any date — past or up to a year into the future — using a trend + seasonality regression model fit on historical month-end prices.

**[→ View the live dashboard](https://yourusername.github.io/your-repo-name/)**

---

## Overview

Natural gas prices follow two consistent patterns: a long-term upward trend, and a seasonal cycle tied to heating demand — prices climb heading into winter and ease through the summer. This project models both effects and uses the fitted model to answer one question for any given date:

> **What was (or will) the natural gas price be?**

The repo contains two things:

| File | What it does |
|---|---|
| [`gas_price_model.py`](./gas_price_model.py) | Fits the pricing model and exposes a function to estimate the price for any date |
| [`index.html`](./index.html) | An interactive dashboard visualizing the historical data, forecast, and seasonal cycle |

---

## 📊 Dashboard

The dashboard surfaces the model's output visually:

- **Price history & forward curve** — observed prices vs. the one-year forecast
- **Seasonal demand cycle** — average deviation from trend by calendar month, showing the winter peak / summer trough
- **Spot-check estimator** — enter any date and get an instant price estimate
- **Year-over-year change** — month-by-month % change vs. the prior year

→ **[Open the live dashboard](https://yourusername.github.io/your-repo-name/)**

---

## 🧠 Methodology

The data covers 48 month-end purchase prices from **31 Oct 2020 to 30 Sep 2024**.

Prices are modeled as a linear trend plus a two-harmonic seasonal (Fourier) component, fit by ordinary least squares:

```
price(t) = a + b·t
         + c₁·sin(2π·t / 365.25) + c₂·cos(2π·t / 365.25)
         + c₃·sin(4π·t / 365.25) + c₄·cos(4π·t / 365.25)
```

where `t` is the number of days since the first observation.

- **`a + b·t`** — the long-term linear trend
- **First harmonic** — the dominant annual heating-demand cycle
- **Second harmonic** — lets the seasonal curve bend beyond a pure sine wave (sharper winter peak, flatter summer trough)

**How a date is estimated depends on where it falls:**

| Date range | Method |
|---|---|
| Within the historical window (Oct 2020 – Sep 2024) | Linear interpolation between the two nearest real observations |
| Up to 1 year beyond the last observation (through Sep 2025) | Extrapolated using the fitted trend + seasonal model |
| Outside that window | Not supported — raises an error rather than guessing |

---

## 🚀 Usage

```python
from gas_price_model import estimate_price

estimate_price("2022-06-15")   # interpolated, in-sample
estimate_price("2025-03-31")   # extrapolated, future estimate
```

```bash
pip install pandas numpy
```

> **Note:** Update `CSV_PATH` in `gas_price_model.py` to point to wherever `Nat_Gas.csv` lives on your machine.

---

## 📁 Data

`Nat_Gas.csv` contains month-end natural gas purchase prices from **31 Oct 2020** to **30 Sep 2024**.

---

## ⚠️ Disclaimer

This model is built for estimation and educational purposes only. It is not financial advice and should not be used as the sole basis for purchasing or trading decisions.
