from __future__ import annotations

from pathlib import Path

from .experiments import DEFAULT_MODEL, write_results_bundle


def main() -> None:
    output_root = Path(__file__).resolve().parents[2] / "results"
    pricing_records, sensitivity_records = write_results_bundle(output_root=output_root, model=DEFAULT_MODEL)

    print("Generated pricing summary:")
    for record in pricing_records:
        analytic_text = "n/a" if record.analytic_price is None else f"{record.analytic_price:.6f}"
        error_text = "n/a" if record.absolute_error is None else f"{record.absolute_error:.6f}"
        print(
            f"  {record.product}: mc={record.monte_carlo_price:.6f}, "
            f"se={record.standard_error:.6f}, analytic={analytic_text}, abs_error={error_text}"
        )

    print("\nGenerated quanto sensitivity grid:")
    for record in sensitivity_records:
        print(
            f"  corr={record.correlation_fx_foreign:+.2f}, drift={record.foreign_drift:.6f}, "
            f"analytic={record.analytic_price:.6f}, mc={record.monte_carlo_price:.6f}, se={record.standard_error:.6f}"
        )

    print(f"\nResults written to: {output_root}")


if __name__ == "__main__":
    main()
