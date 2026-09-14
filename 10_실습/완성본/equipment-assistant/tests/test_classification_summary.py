import pytest
from backend.detect.rules import classification_summary


def test_same_holdout_and_feature_order():
    result = classification_summary([0, 0, 1, 1], [0, 1, 1, 1], [303, 302], [.25, .75])
    assert result["metrics"]["recall"] == 1
    assert result["baseline"]["metrics"] == {"tp":0,"tn":2,"fp":0,"fn":2,"n":4,"accuracy":.5,"precision":None,"recall":0}
    assert result["feature_importances"] == [{"column_id":303,"importance":.25},{"column_id":302,"importance":.75}]


def test_no_positive_is_undefined_not_perfect():
    result = classification_summary([0, 0], [0, 0], [302], [0.])
    assert result["baseline"]["metrics"]["recall"] is None
    assert result["metrics"]["recall"] is None


@pytest.mark.parametrize("ids,weights", [([302,303],[1.]),([302,302],[.5,.5]),([302],[float('nan')]),([302],[-.1])])
def test_invalid_importance_is_not_silently_zipped(ids, weights):
    with pytest.raises(ValueError):
        classification_summary([0,1],[0,1],ids,weights)
