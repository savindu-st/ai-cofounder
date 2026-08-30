from app.validation.invariants import verify_tam_sam_som

def test_tam_sam_som():
    assert verify_tam_sam_som(1000000, 500000, 50000) is True
    assert verify_tam_sam_som(50000, 100000, 500000) is False
