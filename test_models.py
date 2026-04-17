import unittest

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from backend.feature_extractor import extract_features
from backend.model_loader import predict_url_probability
from ml.utils import load_training_dataset


class ModelSupportTests(unittest.TestCase):
    def test_predictor_supports_text_pipeline_models(self):
        model = Pipeline(
            steps=[
                ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4))),
                ("clf", LogisticRegression(max_iter=500)),
            ]
        )
        samples = ["https://example.com", "http://secure-login-paypal.com"]
        labels = [0, 1]
        model.fit(samples, labels)

        score = predict_url_probability(model, "http://secure-login-paypal.com")

        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_feature_extractor_matches_feature_model_vector_size(self):
        classifier = RandomForestClassifier(n_estimators=5, random_state=42)
        training_rows = [
            extract_features("https://example.com"),
            extract_features("http://secure-login-paypal.com"),
        ]
        classifier.fit(training_rows, [0, 1])

        features = extract_features("https://login.example.com/account")

        self.assertEqual(len(features), classifier.n_features_in_)

    def test_new_url_signals_are_detected(self):
        shortener_features = extract_features("http://bit.ly/3abc?redirect=https://evil.com")
        punycode_features = extract_features("https://xn--pple-43d.com/login")

        self.assertEqual(shortener_features[15], 1)
        self.assertEqual(shortener_features[16], 1)
        self.assertGreaterEqual(shortener_features[13], 0)
        self.assertGreater(shortener_features[14], 0)
        self.assertEqual(punycode_features[17], 1)

    def test_dataset_loader_normalizes_excel_column_names(self):
        df = load_training_dataset()

        self.assertIn("url", df.columns)
        self.assertIn("label", df.columns)
        self.assertGreater(len(df), 0)


if __name__ == "__main__":
    unittest.main()
