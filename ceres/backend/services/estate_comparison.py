"""Factual pair comparison; an attribute difference is not an investment ranking."""
from backend.api.schemas.analysis import EstatePairMetric
from backend.services.valuation_metrics import valuation_metrics


def comparison_metrics(a: dict, b: dict) -> list[EstatePairMetric]:
    def values(estate):
        estimate = estate.get('estimated_price')
        gap = valuation_metrics(estate.get('asking_price'), estimate, None)['difference_percent'] if estimate and estimate > 0 else None
        return {
            'price': estate.get('asking_price'), 'price_per_m2': estate.get('price_per_m2'),
            'suggested_price': estimate, 'price_deviation': gap,
            'area_m2': estate.get('area_m2'), 'bedrooms': estate.get('rooms'),
            'bathrooms': estate.get('bathrooms'), 'parking_spaces': estate.get('parking_spaces'),
            'property_age': estate.get('age_years'), 'days_on_market': estate.get('days_on_market'),
            'liquidity_score': estate.get('liquidity_score'), 'market_heat': estate.get('market_heat'),
        }

    av, bv = values(a), values(b)
    units = {'price': 'BRL', 'price_per_m2': 'BRL/m²', 'suggested_price': 'BRL',
             'price_deviation': 'percentage_points', 'area_m2': 'm²',
             'property_age': 'years', 'days_on_market': 'days', 'liquidity_score': 'score_0_100',
             'market_heat': 'score_0_100'}
    return [EstatePairMetric(key=key, a_value=value, b_value=bv[key], unit=units.get(key, 'count'),
                            difference=float(bv[key]) - float(value) if value is not None and bv[key] is not None else None)
            for key, value in av.items()]
