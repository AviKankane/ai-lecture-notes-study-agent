from app.graph.workflow import route_after_validation, route_by_size


def test_route_by_size_short():
    assert route_by_size({"word_count": 499}) == "short"


def test_route_by_size_long():
    assert route_by_size({"word_count": 500}) == "long"


def test_route_after_validation_valid():
    assert route_after_validation({"error": None, "retry_count": 0}) == "valid"


def test_route_after_validation_repair():
    assert route_after_validation({"error": "bad json", "retry_count": 1}) == "repair"


def test_route_after_validation_failed():
    assert route_after_validation({"error": "bad json", "retry_count": 2}) == "failed"
