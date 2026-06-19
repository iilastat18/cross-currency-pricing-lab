from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean, pstdev

from .model import CrossCurrencyModel, SimulationResult


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def lognormal_call_price(
    *,
    initial_value: float,
    strike: float,
    volatility: float,
    maturity: float,
    drift: float,
    discount_factor: float,
    payoff_scale: float = 1.0,
) -> float:
    if maturity <= 0.0 or volatility <= 0.0:
        forward_mean = initial_value * math.exp(drift * maturity)
        return discount_factor * payoff_scale * max(forward_mean - strike, 0.0)

    total_volatility = volatility * math.sqrt(maturity)
    d1 = (math.log(initial_value / strike) + (drift + 0.5 * volatility * volatility) * maturity) / total_volatility
    d2 = d1 - total_volatility
    return discount_factor * payoff_scale * (
        initial_value * math.exp(drift * maturity) * normal_cdf(d1) - strike * normal_cdf(d2)
    )


@dataclass(frozen=True)
class MonteCarloEstimate:
    price: float
    standard_error: float


class CrossCurrencyProduct:
    name: str

    def price_from_simulation(self, simulation: SimulationResult, model: CrossCurrencyModel) -> MonteCarloEstimate:
        raise NotImplementedError

    def analytic_price(self, model: CrossCurrencyModel) -> float | None:
        return None


@dataclass(frozen=True)
class DomesticCaplet(CrossCurrencyProduct):
    strike: float
    name: str = "Domestic Caplet"

    def price_from_simulation(self, simulation: SimulationResult, model: CrossCurrencyModel) -> MonteCarloEstimate:
        payoffs = [
            model.domestic_zero_bond * model.period_length * max(level - self.strike, 0.0)
            for level in simulation.domestic_forward_t1
        ]
        return _estimate(payoffs)

    def analytic_price(self, model: CrossCurrencyModel) -> float:
        return lognormal_call_price(
            initial_value=model.initial_domestic_forward_rate,
            strike=self.strike,
            volatility=model.volatility_domestic,
            maturity=model.period_start,
            drift=0.0,
            discount_factor=model.domestic_zero_bond,
            payoff_scale=model.period_length,
        )


@dataclass(frozen=True)
class QuantoForeignCaplet(CrossCurrencyProduct):
    strike: float
    name: str = "Quanto Foreign Caplet"

    def price_from_simulation(self, simulation: SimulationResult, model: CrossCurrencyModel) -> MonteCarloEstimate:
        payoffs = [
            model.domestic_zero_bond * model.period_length * max(level - self.strike, 0.0)
            for level in simulation.foreign_forward_t1
        ]
        return _estimate(payoffs)

    def analytic_price(self, model: CrossCurrencyModel) -> float:
        return lognormal_call_price(
            initial_value=model.initial_foreign_forward_rate,
            strike=self.strike,
            volatility=model.volatility_foreign,
            maturity=model.period_start,
            drift=model.foreign_drift,
            discount_factor=model.domestic_zero_bond,
            payoff_scale=model.period_length,
        )


@dataclass(frozen=True)
class ForeignCapletWithFXConversion(CrossCurrencyProduct):
    strike: float
    name: str = "Foreign Caplet With FX Conversion"

    def price_from_simulation(self, simulation: SimulationResult, model: CrossCurrencyModel) -> MonteCarloEstimate:
        payoffs = [
            model.domestic_zero_bond * model.period_length * max(rate - self.strike, 0.0) * fx_rate
            for rate, fx_rate in zip(simulation.foreign_forward_t1, simulation.fx_t2)
        ]
        return _estimate(payoffs)


@dataclass(frozen=True)
class FXCall(CrossCurrencyProduct):
    strike: float
    name: str = "FX Call On Terminal Spot"

    def price_from_simulation(self, simulation: SimulationResult, model: CrossCurrencyModel) -> MonteCarloEstimate:
        payoffs = [
            model.domestic_zero_bond * max(fx_rate - self.strike, 0.0)
            for fx_rate in simulation.fx_t2
        ]
        return _estimate(payoffs)

    def analytic_price(self, model: CrossCurrencyModel) -> float:
        return lognormal_call_price(
            initial_value=model.initial_ffx,
            strike=self.strike,
            volatility=model.volatility_ffx,
            maturity=model.period_end,
            drift=0.0,
            discount_factor=model.domestic_zero_bond,
        )


def _estimate(payoffs: list[float]) -> MonteCarloEstimate:
    if not payoffs:
        return MonteCarloEstimate(price=0.0, standard_error=0.0)
    price = fmean(payoffs)
    std_dev = pstdev(payoffs)
    standard_error = std_dev / math.sqrt(len(payoffs))
    return MonteCarloEstimate(price=price, standard_error=standard_error)
