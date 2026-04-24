"""Integration tests for chart data workflows."""
import json


class TestChartDataWorkflows:
    def test_chart_data_all_methods(self, client):
        """All four measurement methods return valid chart data."""
        for method in ["height", "weight", "bmi", "ofc"]:
            payload = {"reference": "uk-who", "measurement_method": method, "sex": "male"}
            response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
            assert response.status_code == 200, f"Failed for {method}"
            data = response.get_json()
            assert data["success"] is True
            assert len(data["centiles"]) == 9

    def test_chart_data_all_references(self, client):
        """All references return chart data for their supported methods."""
        cases = [
            ("uk-who", "height", "male"),
            ("uk-who", "weight", "female"),
            ("turners-syndrome", "height", "female"),
            ("trisomy-21", "height", "male"),
            ("cdc", "weight", "male"),
        ]
        for ref, method, sex in cases:
            payload = {"reference": ref, "measurement_method": method, "sex": sex}
            response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
            assert response.status_code == 200, f"Failed for {ref}/{method}/{sex}"

    def test_chart_data_consistency_with_calculate(self, client):
        """Chart data age range covers the child's age from /calculate."""
        calc_payload = {
            "sex": "male",
            "birth_date": "2020-06-15",
            "measurement_date": "2023-06-15",
            "height": 96.0,
        }
        calc_resp = client.post("/calculate", data=json.dumps(calc_payload), content_type="application/json")
        calc_data = calc_resp.get_json()
        child_age = calc_data["results"]["age_years"]

        chart_payload = {"reference": "uk-who", "measurement_method": "height", "sex": "male"}
        chart_resp = client.post("/chart-data", data=json.dumps(chart_payload), content_type="application/json")
        chart_data = chart_resp.get_json()

        median = [c for c in chart_data["centiles"] if c["centile"] == 50][0]
        x_values = [p["x"] for p in median["data"]]
        assert min(x_values) < child_age
        assert max(x_values) > child_age

    def test_chart_data_centile_values(self, client):
        """Verify the 9 cole-nine-centile values."""
        payload = {"reference": "uk-who", "measurement_method": "height", "sex": "female"}
        response = client.post("/chart-data", data=json.dumps(payload), content_type="application/json")
        data = response.get_json()
        centile_values = sorted([c["centile"] for c in data["centiles"]])
        expected = [0.4, 2, 9, 25, 50, 75, 91, 98, 99.6]
        assert centile_values == expected
