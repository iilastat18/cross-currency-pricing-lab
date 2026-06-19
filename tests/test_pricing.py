import unittest

from cross_currency_pricing_lab.experiments import DEFAULT_MODEL
from cross_currency_pricing_lab.model import CrossCurrencyModel
from cross_currency_pricing_lab.products import DomesticCaplet, FXCall, QuantoForeignCaplet


class PricingTests(unittest.TestCase):
    def test_initial_ffx_relation(self) -> None:
        expected = DEFAULT_MODEL.initial_fx * DEFAULT_MODEL.foreign_zero_bond / DEFAULT_MODEL.domestic_zero_bond
        self.assertAlmostEqual(DEFAULT_MODEL.initial_ffx, expected, places=12)

    def test_domestic_caplet_mc_matches_analytic(self) -> None:
        product = DomesticCaplet(strike=0.0400)
        simulation = DEFAULT_MODEL.simulate_terminal_values(number_of_paths=40_000, seed=11)
        estimate = product.price_from_simulation(simulation, DEFAULT_MODEL)
        analytic = product.analytic_price(DEFAULT_MODEL)

        self.assertIsNotNone(analytic)
        self.assertLess(abs(estimate.price - analytic), 0.006)

    def test_fx_call_mc_matches_analytic(self) -> None:
        product = FXCall(strike=DEFAULT_MODEL.initial_ffx)
        simulation = DEFAULT_MODEL.simulate_terminal_values(number_of_paths=40_000, seed=21)
        estimate = product.price_from_simulation(simulation, DEFAULT_MODEL)
        analytic = product.analytic_price(DEFAULT_MODEL)

        self.assertIsNotNone(analytic)
        self.assertLess(abs(estimate.price - analytic), 0.01)

    def test_positive_fx_foreign_correlation_reduces_quanto_price(self) -> None:
        low_corr = CrossCurrencyModel(
            **{**DEFAULT_MODEL.__dict__, "correlation_fx_foreign": -0.60}
        )
        high_corr = CrossCurrencyModel(
            **{**DEFAULT_MODEL.__dict__, "correlation_fx_foreign": 0.60}
        )

        product = QuantoForeignCaplet(strike=0.0300)
        self.assertGreater(product.analytic_price(low_corr), product.analytic_price(high_corr))


if __name__ == "__main__":
    unittest.main()
