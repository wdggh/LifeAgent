"""Fast end-to-end canary for the v2 validator (V2.0.1-04)."""

from tests.evaluation.dataset import validate_v2


def test_v2_validator_passes_on_real_dataset() -> None:
    assert validate_v2.main("synthetic-personal-kb-v2") == 0
