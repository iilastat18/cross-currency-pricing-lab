from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path

from .charts import write_dual_line_chart_svg, write_grouped_bar_chart_svg
from .model import CrossCurrencyModel
from .products import (
    CrossCurrencyProduct,
    DomesticCaplet,
    FXCall,
    ForeignCapletWithFXConversion,
    MonteCarloEstimate,
    QuantoForeignCaplet,
)


DEFAULT_MODEL = CrossCurrencyModel(
    initial_domestic_forward_rate=0.0400,
    initial_foreign_forward_rate=0.0300,
    initial_fx=1.2000,
    volatility_domestic=0.25,
    volatility_foreign=0.22,
    volatility_ffx=0.18,
    correlation_domestic_foreign=0.30,
    correlation_fx_domestic=0.15,
    correlation_fx_foreign=0.45,
    period_start=5.0,
    period_end=6.0,
    domestic_zero_bond=0.7866,
    foreign_zero_bond=0.8607,
)


@dataclass(frozen=True)
class PricingRecord:
    product: str
    monte_carlo_price: float
    standard_error: float
    analytic_price: float | None
    absolute_error: float | None


@dataclass(frozen=True)
class SensitivityRecord:
    correlation_fx_foreign: float
    foreign_drift: float
    analytic_price: float
    monte_carlo_price: float
    standard_error: float


def default_products(model: CrossCurrencyModel) -> list[CrossCurrencyProduct]:
    return [
        DomesticCaplet(strike=0.0400),
        QuantoForeignCaplet(strike=0.0300),
        FXCall(strike=model.initial_ffx),
        ForeignCapletWithFXConversion(strike=0.0300),
    ]


def pricing_summary(
    model: CrossCurrencyModel = DEFAULT_MODEL,
    *,
    number_of_paths: int = 50_000,
    seed: int = 42,
) -> list[PricingRecord]:
    simulation = model.simulate_terminal_values(number_of_paths=number_of_paths, seed=seed)
    rows: list[PricingRecord] = []

    for product in default_products(model):
        estimate = product.price_from_simulation(simulation, model)
        analytic = product.analytic_price(model)
        rows.append(
            PricingRecord(
                product=product.name,
                monte_carlo_price=estimate.price,
                standard_error=estimate.standard_error,
                analytic_price=analytic,
                absolute_error=None if analytic is None else abs(estimate.price - analytic),
            )
        )

    return rows


def quanto_correlation_sensitivity(
    model: CrossCurrencyModel = DEFAULT_MODEL,
    *,
    number_of_paths: int = 35_000,
    seed_base: int = 100,
) -> list[SensitivityRecord]:
    correlations = [-0.75, -0.50, -0.25, 0.00, 0.25, 0.50, 0.75]
    records: list[SensitivityRecord] = []

    for index, correlation in enumerate(correlations):
        scenario = CrossCurrencyModel(
            initial_domestic_forward_rate=model.initial_domestic_forward_rate,
            initial_foreign_forward_rate=model.initial_foreign_forward_rate,
            initial_fx=model.initial_fx,
            volatility_domestic=model.volatility_domestic,
            volatility_foreign=model.volatility_foreign,
            volatility_ffx=model.volatility_ffx,
            correlation_domestic_foreign=model.correlation_domestic_foreign,
            correlation_fx_domestic=model.correlation_fx_domestic,
            correlation_fx_foreign=correlation,
            period_start=model.period_start,
            period_end=model.period_end,
            domestic_zero_bond=model.domestic_zero_bond,
            foreign_zero_bond=model.foreign_zero_bond,
        )
        product = QuantoForeignCaplet(strike=0.0300)
        simulation = scenario.simulate_terminal_values(number_of_paths=number_of_paths, seed=seed_base + index)
        estimate = product.price_from_simulation(simulation, scenario)
        records.append(
            SensitivityRecord(
                correlation_fx_foreign=correlation,
                foreign_drift=scenario.foreign_drift,
                analytic_price=product.analytic_price(scenario) or 0.0,
                monte_carlo_price=estimate.price,
                standard_error=estimate.standard_error,
            )
        )

    return records


def write_results_bundle(
    *,
    output_root: Path,
    model: CrossCurrencyModel = DEFAULT_MODEL,
) -> tuple[list[PricingRecord], list[SensitivityRecord]]:
    output_root.mkdir(parents=True, exist_ok=True)

    pricing_records = pricing_summary(model)
    sensitivity_records = quanto_correlation_sensitivity(model)

    _write_csv(
        output_root / "pricing_summary.csv",
        rows=[
            {
                "product": row.product,
                "monte_carlo_price": f"{row.monte_carlo_price:.8f}",
                "standard_error": f"{row.standard_error:.8f}",
                "analytic_price": "" if row.analytic_price is None else f"{row.analytic_price:.8f}",
                "absolute_error": "" if row.absolute_error is None else f"{row.absolute_error:.8f}",
            }
            for row in pricing_records
        ],
    )
    _write_csv(
        output_root / "quanto_correlation_sensitivity.csv",
        rows=[
            {
                "correlation_fx_foreign": f"{row.correlation_fx_foreign:.2f}",
                "foreign_drift": f"{row.foreign_drift:.8f}",
                "analytic_price": f"{row.analytic_price:.8f}",
                "monte_carlo_price": f"{row.monte_carlo_price:.8f}",
                "standard_error": f"{row.standard_error:.8f}",
            }
            for row in sensitivity_records
        ],
    )

    (output_root / "pricing_summary.json").write_text(
        json.dumps([asdict(row) for row in pricing_records], indent=2),
        encoding="utf-8",
    )
    (output_root / "quanto_correlation_sensitivity.json").write_text(
        json.dumps([asdict(row) for row in sensitivity_records], indent=2),
        encoding="utf-8",
    )

    write_grouped_bar_chart_svg(
        title="Cross-Currency Pricing Comparison",
        categories=[row.product.replace(" On Terminal Spot", "") for row in pricing_records],
        left_values=[row.monte_carlo_price for row in pricing_records],
        right_values=[row.analytic_price for row in pricing_records],
        left_label="Monte Carlo",
        right_label="Analytic",
        output_path=output_root / "pricing_comparison.svg",
    )
    write_dual_line_chart_svg(
        title="Quanto Caplet Sensitivity To FX / Foreign Correlation",
        subtitle="Higher positive FX-foreign correlation makes the quanto drift more negative and pushes the price lower.",
        x_values=[row.correlation_fx_foreign for row in sensitivity_records],
        left_values=[row.analytic_price for row in sensitivity_records],
        right_values=[row.monte_carlo_price for row in sensitivity_records],
        output_path=output_root / "quanto_correlation_sensitivity.svg",
    )

    return pricing_records, sensitivity_records


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
