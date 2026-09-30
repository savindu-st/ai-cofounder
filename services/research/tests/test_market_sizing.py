"""Unit tests for Deterministic Market Sizing Engine (TAM, SAM, SOM)."""

from services.research.app.agents.market_research.market_sizing import MarketSizingEngine


def test_invariant_valid_passes():
    is_valid, violations = MarketSizingEngine.validate_invariants(
        tam=10_000_000_000.0,
        sam=1_000_000_000.0,
        som=50_000_000.0
    )
    assert is_valid is True
    assert len(violations) == 0


def test_invariant_violation_sam_gt_tam():
    is_valid, violations = MarketSizingEngine.validate_invariants(
        tam=5_000_000.0,
        sam=10_000_000.0,  # SAM > TAM
        som=500_000.0
    )
    assert is_valid is False
    assert any("SAM violation" in v for v in violations)


def test_invariant_violation_som_gt_sam():
    is_valid, violations = MarketSizingEngine.validate_invariants(
        tam=100_000_000.0,
        sam=10_000_000.0,
        som=25_000_000.0  # SOM > SAM
    )
    assert is_valid is False
    assert any("SOM violation" in v for v in violations)


def test_invariant_zero_and_negative_values():
    is_valid, violations = MarketSizingEngine.validate_invariants(
        tam=-1000.0,
        sam=0.0,
        som=500.0
    )
    assert is_valid is False
    assert len(violations) >= 2


def test_auto_correct_clamps_violations():
    tam, sam, som = MarketSizingEngine.auto_correct(
        tam=50_000_000.0,
        sam=80_000_000.0,   # Exceeds TAM
        som=100_000_000.0   # Exceeds SAM
    )
    is_valid, violations = MarketSizingEngine.validate_invariants(tam, sam, som)
    assert is_valid is True
    assert len(violations) == 0
    assert 0 < som <= sam <= tam


def test_triangulation_dual_methodology():
    # Top-down: $6 Billion
    # Bottom-up: 500,000 customers * $8,000 ACV = $4 Billion
    # Triangulated TAM should be ($6B + $4B) / 2 = $5 Billion
    sizing = MarketSizingEngine.triangulate(
        top_down_tam=6_000_000_000.0,
        estimated_target_customers=500_000,
        annual_contract_value=8_000.0,
        target_geography="North America"
    )

    assert sizing.tam == 5_000_000_000.0
    assert "triangulated" in sizing.methodology
    assert 0 < sizing.som <= sizing.sam <= sizing.tam


def test_triangulation_top_down_only():
    sizing = MarketSizingEngine.triangulate(
        top_down_tam=3_000_000_000.0,
        target_geography="Global"
    )
    assert sizing.tam == 3_000_000_000.0
    assert 0 < sizing.som <= sizing.sam <= sizing.tam
