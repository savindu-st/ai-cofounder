try:
    from services.finance.app.engine.calculator import calculate_projections
except ImportError:
    from app.engine.calculator import calculate_projections


def test_calculate_projections():
    res = calculate_projections(100, 1500, 0.05, 0.02, 12)
    assert len(res) == 12
    assert res[0]["revenue"] == 150000.0
