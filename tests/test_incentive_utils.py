from car_workshop.incentive_utils import calculate_incentive


def test_calculate_percentage():
    config = {"incentive_type": "Percentage", "rate": 10}
    assert calculate_incentive(200, config) == 20


def test_calculate_fixed():
    config = {"incentive_type": "Fixed", "rate": 50}
    assert calculate_incentive(200, config) == 50


def test_calculate_tiered():
    tiers = [
        {"threshold": 0, "rate": 5},
        {"threshold": 100, "rate": 10},
        {"threshold": 200, "rate": 15},
    ]
    config = {"incentive_type": "Tiered", "tiers": tiers}
    assert calculate_incentive(150, config) == 15


def test_calculate_team_based():
    config = {"incentive_type": "Team-Based", "rate": 10}
    result = calculate_incentive(100, config, team_members=["E1", "E2"])
    assert result == {"E1": 5.0, "E2": 5.0}
