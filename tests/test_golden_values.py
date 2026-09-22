"""Known-answer tests: pin SDS and centile for fixed cases across every reference.

These catch drift when rcpchgrowth is upgraded (reference data, LMS lookup,
gestation correction). Expected values were recorded from rcpchgrowth 4.6.4
through /calculate. If one fails after an upgrade, check the library's
changelog and confirm the new value is intended before updating it here.
"""
import pytest

# (payload, {measurement: (sds, centile)}) — SDS to 2 dp, centile to 1 dp.
CASES = {
    "uk-who boy 3y": (
        {"sex": "male", "birth_date": "2020-06-15", "measurement_date": "2023-06-15",
         "reference": "uk-who", "weight": 14.5, "height": 96.0, "ofc": 50.0},
        {"weight": (0.09, 53.7), "height": (-0.02, 49.3), "ofc": (0.38, 64.8), "bmi": (0.08, 53.2)},
    ),
    "uk-who girl 10y": (
        {"sex": "female", "birth_date": "2014-01-10", "measurement_date": "2024-07-10",
         "reference": "uk-who", "weight": 32.0, "height": 140.0},
        {"weight": (-0.35, 36.2), "height": (-0.19, 42.5), "bmi": (-0.43, 33.4)},
    ),
    "uk-who infant 3 months": (
        {"sex": "female", "birth_date": "2024-01-01", "measurement_date": "2024-04-01",
         "reference": "uk-who", "weight": 5.8, "height": 60.0, "ofc": 39.5},
        {"weight": (-0.05, 47.9), "height": (0.11, 54.2), "ofc": (-0.02, 49.3), "bmi": (-0.17, 43.3)},
    ),
    "uk-who preterm 30 weeks, corrected": (
        {"sex": "male", "birth_date": "2024-01-01", "measurement_date": "2024-05-01",
         "reference": "uk-who", "weight": 5.0, "height": 57.0, "ofc": 39.0,
         "gestation_weeks": 30, "gestation_days": 0},
        {"weight": (-0.38, 35.1), "height": (-0.16, 43.6), "ofc": (0.34, 63.5), "bmi": (-0.43, 33.3)},
    ),
    "turner 10y": (
        {"sex": "female", "birth_date": "2014-01-01", "measurement_date": "2024-01-01",
         "reference": "turners-syndrome", "height": 125.0},
        {"height": (0.99, 83.9)},
    ),
    "trisomy 21 5y": (
        {"sex": "male", "birth_date": "2019-01-01", "measurement_date": "2024-01-01",
         "reference": "trisomy-21", "weight": 16.0, "height": 100.0},
        {"weight": (-0.25, 40.3), "height": (0.30, 61.7), "bmi": (-0.57, 28.5)},
    ),
    "cdc girl 12y": (
        {"sex": "female", "birth_date": "2012-01-01", "measurement_date": "2024-01-01",
         "reference": "cdc", "weight": 40.0, "height": 150.0},
        {"weight": (-0.20, 42.0), "height": (-0.16, 43.6), "bmi": (-0.10, 45.8)},
    ),
    "who boy 3y": (
        {"sex": "male", "birth_date": "2021-01-01", "measurement_date": "2024-01-01",
         "reference": "who", "weight": 14.0, "height": 95.0},
        {"weight": (-0.20, 42.2), "height": (-0.29, 38.7), "bmi": (-0.08, 46.8)},
    ),
    "trisomy 21 aap girl 4y": (
        {"sex": "female", "birth_date": "2020-01-01", "measurement_date": "2024-01-01",
         "reference": "trisomy-21-aap", "weight": 14.0, "height": 92.0},
        {"weight": (-0.02, 49.3), "height": (-0.02, 49.2), "bmi": (-0.25, 40.1)},
    ),
}


@pytest.mark.parametrize("payload, expected", CASES.values(), ids=CASES.keys())
def test_known_sds_and_centile(client, payload, expected):
    response = client.post("/calculate", json=payload)
    assert response.status_code == 200, response.get_json()
    results = response.get_json()["results"]
    actual = {
        m: (round(results[m]["sds"], 2), round(results[m]["centile"], 1))
        for m in expected
    }
    assert actual == expected


def test_extreme_height_sds_pinned_and_flagged(client):
    payload = {"sex": "male", "birth_date": "2016-01-01", "measurement_date": "2024-01-01",
               "reference": "uk-who", "height": 100.0}
    results = client.post("/calculate", json=payload).get_json()["results"]
    assert round(results["height"]["sds"], 2) == -5.08
    assert any("-5.1 SDS" in msg for msg in results["validation_messages"])
