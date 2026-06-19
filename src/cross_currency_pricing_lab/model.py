from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class SimulationResult:
    domestic_forward_t1: list[float]
    foreign_forward_t1: list[float]
    ffx_t1: list[float]
    ffx_t2: list[float]
    fx_t1: list[float]
    fx_t2: list[float]
    numeraire_t1: list[float]

    @property
    def number_of_paths(self) -> int:
        return len(self.domestic_forward_t1)


@dataclass(frozen=True)
class CrossCurrencyModel:
    initial_domestic_forward_rate: float
    initial_foreign_forward_rate: float
    initial_fx: float
    volatility_domestic: float
    volatility_foreign: float
    volatility_ffx: float
    correlation_domestic_foreign: float
    correlation_fx_domestic: float
    correlation_fx_foreign: float
    period_start: float
    period_end: float
    domestic_zero_bond: float
    foreign_zero_bond: float

    @property
    def period_length(self) -> float:
        return self.period_end - self.period_start

    @property
    def initial_ffx(self) -> float:
        return self.initial_fx * self.foreign_zero_bond / self.domestic_zero_bond

    @property
    def factor_loadings(self) -> tuple[tuple[float, float, float], ...]:
        corr_df = self.correlation_domestic_foreign
        corr_xd = self.correlation_fx_domestic
        corr_xf = self.correlation_fx_foreign

        if abs(corr_df) >= 1.0:
            raise ValueError("Domestic/foreign correlation must be strictly between -1 and 1.")

        l00 = 1.0
        l10 = corr_df
        l11 = math.sqrt(max(1.0 - corr_df * corr_df, 0.0))
        l20 = corr_xd
        if l11 < 1.0e-12:
            raise ValueError("Correlation matrix is degenerate.")
        l21 = (corr_xf - corr_xd * corr_df) / l11
        l22_square = 1.0 - l20 * l20 - l21 * l21
        if l22_square < -1.0e-10:
            raise ValueError("Correlation matrix is not positive semi-definite.")
        l22 = math.sqrt(max(l22_square, 0.0))

        return (
            (
                self.volatility_domestic * l00,
                0.0,
                0.0,
            ),
            (
                self.volatility_foreign * l10,
                self.volatility_foreign * l11,
                0.0,
            ),
            (
                self.volatility_ffx * l20,
                self.volatility_ffx * l21,
                self.volatility_ffx * l22,
            ),
        )

    @property
    def foreign_drift(self) -> float:
        domestic, foreign, ffx = self.factor_loadings
        return -sum(foreign[index] * ffx[index] for index in range(3))

    def simulate_terminal_values(self, number_of_paths: int, seed: int) -> SimulationResult:
        rng = random.Random(seed)
        lambda_domestic, lambda_foreign, lambda_ffx = self.factor_loadings

        domestic_forward_t1: list[float] = []
        foreign_forward_t1: list[float] = []
        ffx_t1: list[float] = []
        ffx_t2: list[float] = []
        fx_t1: list[float] = []
        fx_t2: list[float] = []
        numeraire_t1: list[float] = []

        for _ in range(number_of_paths):
            factor_t1 = [rng.gauss(0.0, math.sqrt(self.period_start)) for _ in range(3)]
            factor_t2 = [
                factor_t1[index] + rng.gauss(0.0, math.sqrt(self.period_end - self.period_start))
                for index in range(3)
            ]

            domestic_level = self._lognormal_terminal(
                initial_value=self.initial_domestic_forward_rate,
                drift=0.0,
                factor_loadings=lambda_domestic,
                factors=factor_t1,
                time_horizon=self.period_start,
            )
            foreign_level = self._lognormal_terminal(
                initial_value=self.initial_foreign_forward_rate,
                drift=self.foreign_drift,
                factor_loadings=lambda_foreign,
                factors=factor_t1,
                time_horizon=self.period_start,
            )
            ffx_level_t1 = self._lognormal_terminal(
                initial_value=self.initial_ffx,
                drift=0.0,
                factor_loadings=lambda_ffx,
                factors=factor_t1,
                time_horizon=self.period_start,
            )
            ffx_level_t2 = self._lognormal_terminal(
                initial_value=self.initial_ffx,
                drift=0.0,
                factor_loadings=lambda_ffx,
                factors=factor_t2,
                time_horizon=self.period_end,
            )

            numeraire_at_t1 = 1.0 / (1.0 + domestic_level * self.period_length)
            foreign_bond_t1 = 1.0 / (1.0 + foreign_level * self.period_length)
            fx_level_t1 = ffx_level_t1 * numeraire_at_t1 / foreign_bond_t1

            domestic_forward_t1.append(domestic_level)
            foreign_forward_t1.append(foreign_level)
            ffx_t1.append(ffx_level_t1)
            ffx_t2.append(ffx_level_t2)
            fx_t1.append(fx_level_t1)
            fx_t2.append(ffx_level_t2)
            numeraire_t1.append(numeraire_at_t1)

        return SimulationResult(
            domestic_forward_t1=domestic_forward_t1,
            foreign_forward_t1=foreign_forward_t1,
            ffx_t1=ffx_t1,
            ffx_t2=ffx_t2,
            fx_t1=fx_t1,
            fx_t2=fx_t2,
            numeraire_t1=numeraire_t1,
        )

    @staticmethod
    def _lognormal_terminal(
        *,
        initial_value: float,
        drift: float,
        factor_loadings: tuple[float, float, float],
        factors: list[float],
        time_horizon: float,
    ) -> float:
        variance = sum(loading * loading for loading in factor_loadings)
        diffusion = sum(factor_loadings[index] * factors[index] for index in range(3))
        return initial_value * math.exp((drift - 0.5 * variance) * time_horizon + diffusion)
