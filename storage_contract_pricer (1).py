 """
Gas Storage Contract Pricing Model
===================================

PURPOSE
-------
Prototype pricing model for natural gas storage contracts. Given a schedule of injection dates (buying gas, putting it into storage) and  withdrawal dates (taking gas out, selling it), this model computes the total value of the contract — i.e. what the trading desk should be willing to pay or charge a client to enter into it.

This generalizes the single buy/sell example: a client may inject gas on several different dates and withdraw it on several different dates, in different volumes, subject to storage capacity and injection/withdrawal rate limits.

VALUE LOGIC
-----------
Contract value = (cash inflows from selling gas at withdrawal)
                - (cash outflows from buying gas at injection)
                - (storage costs)
                - (injection/withdrawal handling costs)
                - (any other transaction costs, e.g. transport)

Assumptions (per task scope 
- No transport delay.
- Interest rates are zero (no discounting of cash flows over time).
- Weekends/holidays are not accounted for separately — every input
  date is treated as a valid trading day.
- Gas is injected and withdrawn in full instantaneously on the given
  date (subject to the rate limit check below).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Union

DateLike = Union[str, date, datetime]


def _to_date(d: DateLike) -> date:
    """Normalize a string or date/datetime input into a plain date."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


@dataclass
class CashflowEvent:
    """A single dated cash flow / volume event, for the audit trail."""
    event_date: date
    event_type: str   # "injection" or "withdrawal"
    volume: float
    price: float
    cash_flow: float  # negative = cash out, positive = cash in
    note: str = ""


@dataclass
class ContractResult:
    """Full breakdown of a priced contract."""
    contract_value: float
    total_purchase_cost: float
    total_sale_revenue: float
    total_storage_cost: float
    total_injection_withdrawal_cost: float
    events: List[CashflowEvent] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{'Date':<12}{'Action':<12}{'Volume':>10}{'Price':>9}{'Cash Flow':>14}  Note",
            "-" * 70,
        ]
        for e in self.events:
            lines.append(
                f"{e.event_date.isoformat():<12}{e.event_type:<12}"
                f"{e.volume:>10,.0f}{e.price:>9.2f}{e.cash_flow:>14,.2f}  {e.note}"
            )
        lines.append("-" * 70)
        lines.append(f"Total purchase cost:            ${self.total_purchase_cost:,.2f}")
        lines.append(f"Total sale revenue:              ${self.total_sale_revenue:,.2f}")
        lines.append(f"Total storage cost:              ${self.total_storage_cost:,.2f}")
        lines.append(f"Total injection/withdrawal cost: ${self.total_injection_withdrawal_cost:,.2f}")
        lines.append("-" * 70)
        lines.append(f"CONTRACT VALUE:                  ${self.contract_value:,.2f}")
        return "\n".join(lines)


def price_storage_contract(
    injection_dates: List[DateLike],
    withdrawal_dates: List[DateLike],
    injection_prices: List[float],
    withdrawal_prices: List[float],
    injection_volumes: List[float],
    withdrawal_volumes: List[float],
    max_injection_withdrawal_rate: float,
    max_storage_volume: float,
    storage_cost_per_month: float,
    injection_withdrawal_cost_per_unit: float = 0.0,
    other_transaction_cost: float = 0.0,
) -> ContractResult:
    """
    Price a gas storage contract with multiple injection/withdrawal dates.

    Parameters
    ----------
    injection_dates : list of date-like
        Dates on which gas is purchased and injected into storage.
    withdrawal_dates : list of date-like
        Dates on which gas is withdrawn from storage and sold.
    injection_prices : list of float
        Purchase price ($/unit) on each corresponding injection date.
    withdrawal_prices : list of float
        Sale price ($/unit) on each corresponding withdrawal date.
    injection_volumes : list of float
        Volume injected on each corresponding injection date.
    withdrawal_volumes : list of float
        Volume withdrawn on each corresponding withdrawal date.
    max_injection_withdrawal_rate : float
        Maximum volume that can be injected OR withdrawn on any single
        date (a physical pumping-rate constraint).
    max_storage_volume : float
        Maximum volume the facility can hold at any point in time.
    storage_cost_per_month : float
        Fixed fee charged per calendar month (or part thereof) that
        gas is held in storage, independent of volume.
    injection_withdrawal_cost_per_unit : float, default 0.0
        Variable handling fee charged per unit of gas, applied on both
        injection and withdrawal.
    other_transaction_cost : float, default 0.0
        Any additional flat cost applied once per injection or
        withdrawal event (e.g. a fixed transport fee per trip).

    Returns
    -------
    ContractResult
        Object containing the total contract value and a full
        itemized breakdown of all cash flows and costs.

    Raises
    ------
    ValueError
        If input lists are mismatched in length, if any single
        injection/withdrawal exceeds the rate limit, if storage
        capacity is exceeded at any point, or if a withdrawal is
        attempted without sufficient gas in storage.
    """
    # ---- Validate input shapes -------------------------------------
    if not (len(injection_dates) == len(injection_prices) == len(injection_volumes)):
        raise ValueError("injection_dates, injection_prices, and injection_volumes must be the same length.")
    if not (len(withdrawal_dates) == len(withdrawal_prices) == len(withdrawal_volumes)):
        raise ValueError("withdrawal_dates, withdrawal_prices, and withdrawal_volumes must be the same length.")

    # ---- Build a unified, chronologically sorted event list --------
    # Each event records: date, type, volume, price.
    events_raw = []
    for d, p, v in zip(injection_dates, injection_prices, injection_volumes):
        events_raw.append((_to_date(d), "injection", v, p))
    for d, p, v in zip(withdrawal_dates, withdrawal_prices, withdrawal_volumes):
        events_raw.append((_to_date(d), "withdrawal", v, p))

    # Sort chronologically. On ties, process injections before
    # withdrawals (gas must be in storage before it can be taken out).
    events_raw.sort(key=lambda e: (e[0], 0 if e[1] == "injection" else 1))

    if not events_raw:
        raise ValueError("At least one injection or withdrawal event is required.")

    # ---- Walk through events, tracking storage level over time -----
    events: List[CashflowEvent] = []
    current_volume = 0.0
    total_purchase_cost = 0.0
    total_sale_revenue = 0.0
    total_injection_withdrawal_cost = 0.0
    total_other_cost = 0.0

    for event_date, event_type, volume, price in events_raw:
        # Rate constraint: can't move more than the max rate in one event.
        if volume > max_injection_withdrawal_rate:
            raise ValueError(
                f"{event_type.capitalize()} of {volume} on {event_date} exceeds the "
                f"maximum injection/withdrawal rate of {max_injection_withdrawal_rate}."
            )

        if event_type == "injection":
            new_volume = current_volume + volume
            if new_volume > max_storage_volume:
                raise ValueError(
                    f"Injection of {volume} on {event_date} would bring storage to "
                    f"{new_volume}, exceeding capacity of {max_storage_volume}."
                )
            cash_flow = -volume * price
            total_purchase_cost += volume * price
            note = f"Buy {volume:,.0f} units @ ${price:.2f}"
            current_volume = new_volume

        else:  # withdrawal
            new_volume = current_volume - volume
            if new_volume < 0:
                raise ValueError(
                    f"Withdrawal of {volume} on {event_date} exceeds available "
                    f"storage volume of {current_volume}."
                )
            cash_flow = volume * price
            total_sale_revenue += volume * price
            note = f"Sell {volume:,.0f} units @ ${price:.2f}"
            current_volume = new_volume

        # Variable injection/withdrawal handling fee (applies both ways).
        handling_fee = volume * injection_withdrawal_cost_per_unit
        total_injection_withdrawal_cost += handling_fee
        cash_flow -= handling_fee

        # Flat per-event cost (e.g. transport).
        cash_flow -= other_transaction_cost
        total_other_cost += other_transaction_cost

        events.append(CashflowEvent(event_date, event_type, volume, price, cash_flow, note))

    # ---- Storage cost: charged per calendar month gas is held -------
    # Months are counted from the first injection date through the
    # last withdrawal date (inclusive), since that's the full window
    # the facility is in use for this contract.
    first_date = events_raw[0][0]
    last_date = events_raw[-1][0]
    months_held = (
        (last_date.year - first_date.year) * 12
        + (last_date.month - first_date.month)
        + 1  # count the starting month itself
    )
    months_held = max(months_held, 1)
    total_storage_cost = months_held * storage_cost_per_month

    # ---- Final contract value ---------------------------------------
    contract_value = (
        total_sale_revenue
        - total_purchase_cost
        - total_storage_cost
        - total_injection_withdrawal_cost
        - total_other_cost
    )

    return ContractResult(
        contract_value=contract_value,
        total_purchase_cost=total_purchase_cost,
        total_sale_revenue=total_sale_revenue,
        total_storage_cost=total_storage_cost,
        total_injection_withdrawal_cost=total_injection_withdrawal_cost + total_other_cost,
        events=events,
    )


# -----------------------------------------------------------------
# Sample test cases
# -----------------------------------------------------------------
if __name__ == "__main__":

    print("TEST 1: Simple single buy/sell (matches the worked example)\n")
    result = price_storage_contract(
        injection_dates=["2023-06-30"],
        withdrawal_dates=["2023-10-31"],
        injection_prices=[2.0],
        withdrawal_prices=[3.0],
        injection_volumes=[1_000_000],
        withdrawal_volumes=[1_000_000],
        max_injection_withdrawal_rate=1_000_000,
        max_storage_volume=1_000_000,
        storage_cost_per_month=100_000,
        injection_withdrawal_cost_per_unit=0.01,   # $10K per 1M units = $0.01/unit
        other_transaction_cost=50_000,
    )
    print(result.summary())
    print()

    print("TEST 2: Multiple injections and withdrawals across a year\n")
    result2 = price_storage_contract(
        injection_dates=["2023-06-30", "2023-07-31"],
        withdrawal_dates=["2023-11-30", "2023-12-31"],
        injection_prices=[2.00, 2.10],
        withdrawal_prices=[3.20, 3.50],
        injection_volumes=[500_000, 500_000],
        withdrawal_volumes=[500_000, 500_000],
        max_injection_withdrawal_rate=500_000,
        max_storage_volume=1_000_000,
        storage_cost_per_month=50_000,
        injection_withdrawal_cost_per_unit=0.01,
        other_transaction_cost=25_000,
    )
    print(result2.summary())
    print()

    print("TEST 3: Edge case - storage capacity exceeded (should raise an error)\n")
    try:
        price_storage_contract(
            injection_dates=["2023-06-30", "2023-07-31"],
            withdrawal_dates=["2023-12-31"],
            injection_prices=[2.0, 2.0],
            withdrawal_prices=[3.0],
            injection_volumes=[700_000, 700_000],   # exceeds max_storage_volume together
            withdrawal_volumes=[1_400_000],
            max_injection_withdrawal_rate=1_000_000,
            max_storage_volume=1_000_000,
            storage_cost_per_month=50_000,
        )
    except ValueError as e:
        print(f"Correctly raised: {e}")
    print()

    print("TEST 4: Edge case - withdrawal exceeds rate limit (should raise an error)\n")
    try:
        price_storage_contract(
            injection_dates=["2023-06-30"],
            withdrawal_dates=["2023-10-31"],
            injection_prices=[2.0],
            withdrawal_prices=[3.0],
            injection_volumes=[1_000_000],
            withdrawal_volumes=[1_000_000],
            max_injection_withdrawal_rate=200_000,  # too low for the withdrawal
            max_storage_volume=1_000_000,
            storage_cost_per_month=50_000,
        )
    except ValueError as e:
        print(f"Correctly raised: {e}")
    print()

    print("TEST 5: Sanity check - zero costs should give a pure price-spread profit\n")
    result5 = price_storage_contract(
        injection_dates=["2023-01-31"],
        withdrawal_dates=["2023-06-30"],
        injection_prices=[2.0],
        withdrawal_prices=[2.0],   # same price in and out -> value should be ~0 minus costs
        injection_volumes=[1_000_000],
        withdrawal_volumes=[1_000_000],
        max_injection_withdrawal_rate=1_000_000,
        max_storage_volume=1_000_000,
        storage_cost_per_month=0,
        injection_withdrawal_cost_per_unit=0,
        other_transaction_cost=0,
    )
    print(result5.summary())
    print(f"\nExpected ~$0 (buy and sell at same price, no costs): got ${result5.contract_value:,.2f}")
