import unittest
from unittest.mock import patch

from backend.main import URLRequest, predict, runtime_error_handler


class FakeModel:
    def predict_proba(self, rows):
        return [[0.1, 0.9]]


class PredictApiTests(unittest.TestCase):
    def test_predict_returns_phishing_result(self):
        with patch("backend.main.get_model", return_value=FakeModel()), patch(
            "backend.main.predict_url_probability", return_value=0.9
        ):
            body = predict(URLRequest(url="http://secure-login-paypal.com"))

        self.assertEqual(body["prediction"], 1)
        self.assertGreater(body["confidence"], 0.65)
        self.assertIn("Contains hyphen", body["explanation"])

    def test_runtime_error_handler_returns_503_payload(self):
        response = runtime_error_handler(None, RuntimeError("model missing"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body, b'{"detail":"model missing"}')


if __name__ == "__main__":
    unittest.main()
