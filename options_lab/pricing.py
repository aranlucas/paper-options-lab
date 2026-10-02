"""QuantLib BlackCalculator, using explicit inputs and no global evaluation date."""
import math

import QuantLib as ql


def analytical(kind, spot, strike, years, iv, rate, dividend_yield):
    if years <= 0:
        raise ValueError("Greeks require positive time to expiration")
    forward = spot * math.exp((rate - dividend_yield) * years)
    calculator = ql.BlackCalculator(
        ql.PlainVanillaPayoff(ql.Option.Call if kind == "call" else ql.Option.Put, strike),
        forward, iv * math.sqrt(years), math.exp(-rate * years),
    )
    return {
        "price": calculator.value(),
        "delta": calculator.delta(spot),
        "gamma": calculator.gamma(spot),
        "theta": calculator.thetaPerDay(spot, years),
        "vega": calculator.vega(years) / 100,  # per 1 percentage point IV
    }


def intrinsic(kind, spot, strike):
    return max(0.0, spot - strike if kind == "call" else strike - spot)
