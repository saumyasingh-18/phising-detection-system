# 🔐 Real-Time Phishing Detection System using AI/ML

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--learn%20%7C%20XGBoost%20%7C%20LightGBM-FF6F00.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Detect. Analyze. Protect.** — A robust, real-time phishing defense mechanism powered by a Hybrid Super Learner Ensemble Model.

---

## 📌 Overview

The **Real-Time AI/ML-Based Phishing Detection and Prevention System** is designed to proactively identify and block malicious websites during active browsing. By leveraging a Hybrid Super Learner Ensemble Model, the system achieves exceptional accuracy with minimal false positives. 

The architecture seamlessly integrates a **FastAPI backend** for rapid predictions with a lightweight **Chrome Extension**, ensuring seamless, real-time protection for the end-user.

---

## 🎥 Demo & Screenshots

*(Placeholder: Add a GIF showing the Chrome extension blocking a phishing site in real-time)*
![Demo GIF](https://via.placeholder.com/800x400?text=Insert+Demo+GIF+Here)

**Extension Interface & Warning Screen:**
*(Placeholder: Add screenshots of the extension popup and the red warning page)*
<p align="center">
  <img src="https://via.placeholder.com/400x250?text=Popup+Screenshot" width="45%" />
  <img src="https://via.placeholder.com/400x250?text=Warning+Page+Screenshot" width="45%" />
</p>

---

## 🚀 Key Features

* **🔍 Real-Time Monitoring:** Scans active URLs and page contents instantly via the Chrome Extension.
* **🤖 Hybrid AI/ML Engine:** Combines the strengths of **Random Forest**, **XGBoost**, and **LightGBM** into a Stacking Ensemble.
* **⚡ High-Speed API:** Built on FastAPI for ultra-low latency inference.
* **🧠 Advanced Feature Engineering:** Uses highly optimized, domain-specific attributes (e.g., URL length, HTTPS usage, special character density) for superior predictive power.

---

## 🧠 Model Architecture

To ensure high accuracy and resilience against novel phishing techniques, the system utilizes a **Hybrid Super Learner Ensemble**:

1.  **Random Forest:** Handles noisy datasets effectively and minimizes the risk of overfitting.
2.  **XGBoost:** Excellently captures complex, non-linear patterns within the URL structures.
3.  **LightGBM:** Provides lightning-fast gradient boosting, crucial for real-time inference.
4.  **Stacking Ensemble:** Intelligently combines the predictions of the base models to produce a highly confident final classification.

---

## ⚙️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python, JavaScript |
| **Machine Learning** | Scikit-learn, XGBoost, LightGBM, Pandas, NumPy |
| **Backend API** | FastAPI, Uvicorn |
| **Frontend/Extension**| HTML, CSS, JavaScript, Chrome Extension API (MV3) |

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/phishing-detection-system.git](https://github.com/your-username/phishing-detection-system.git)
cd phishing-detection-system
```

### 2. Set Up the Python Environment
Create and activate a virtual environment to manage dependencies:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirement.txt
```

### 4. Run the Backend API
Start the FastAPI server:
```bash
cd backend
uvicorn main:app --reload
```
*The API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)*

---

## 🌐 Chrome Extension Setup

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** on (top right corner).
3. Click **Load unpacked**.
4. Select the `extension/` folder from this repository.
5. The extension is now active! Navigate to any website to see the model in action.

---

## 🔄 System Workflow

```text
[ User Browses Website ] 
       │
       ▼
[ Chrome Extension Extracts Features ]
       │
       ▼
[ Sends Data to FastAPI Backend ]
       │
       ▼
[ Hybrid ML Model Evaluates Data ]
       │
       ▼
[ Returns Prediction (Safe / Phishing) ]
       │
       ▼
[ Extension Allows Access OR Blocks & Shows Warning ]
```

---

## 📊 Dataset & Performance

The model is trained on a robust, combined dataset sourced from multiple phishing URL repositories:
* **Raw Data:** `Phishing URLs.csv` and `URL dataset.csv`
* **Processed Data:** `training_data.csv` and `training_data_clean.csv`
* **Configuration:** `threshold_config.json` and `threshold_report.json`

**Key Performance Focus:**
While Accuracy and Precision are high, the model is heavily optimized for **Recall** to ensure malicious sites are strictly identified, minimizing false negatives in phishing detection.

---

## 📁 Project Structure

```text
phishing-detection-system/
├── backend/                          # FastAPI server and ML pipeline
│   ├── main.py                       # API endpoints
│   ├── model_loader.py               # Loads the trained model
│   ├── feature_extractor.py          # Parses URLs into ML features
│   └── schemas.py                    # Pydantic schemas for request/response
├── extension/                        # Chrome Extension files (MV3)
│   ├── manifest.json                 # Extension manifest
│   ├── background.js                 # Service worker
│   ├── content.js                    # Content script for page interaction
│   ├── popup/                        # Popup UI
│   │   ├── popup.html
│   │   └── popup.js
│   ├── warning/                      # Phishing warning page
│   │   ├── warning.html
│   │   ├── warning.js
│   │   └── style.css
│   └── safe/                         # Safe page notification
│       ├── safe.html
│       ├── safe.js
│       └── style.css
├── ml/                               # Machine Learning scripts
│   ├── prepare_data.py               # Data preprocessing and feature engineering
│   ├── train_model.py                # Model training (Random Forest, XGBoost, LightGBM)
│   ├── evaluate_model.py             # Model evaluation and metrics
│   ├── utils.py                      # Utility functions for ML pipeline
│   └── hybrid_model.pkl              # Trained ensemble model (Random Forest + XGBoost + LightGBM)
├── data/                             # Datasets
│   ├── raw/                          # Raw dataset files
│   │   ├── Phishing URLs.csv
│   │   └── URL dataset.csv
│   └── processed/                    # Processed and cleaned data
│       ├── training_data.csv
│       ├── training_data_clean.csv
│       ├── threshold_config.json     # Model threshold configuration
│       └── threshold_report.json     # Threshold evaluation report
├── notebooks/                        # Jupyter notebooks for analysis
│   └── analysis.ipynb
├── tests/                            # Unit and integration tests
│   ├── test_api.py
│   └── test_models.py
├── phish_venv/                       # Python virtual environment
├── requirement.txt                   # Python dependencies
└── README.md                         # Project documentation
```

---

## 🔮 Future Enhancements

* **Deep Learning Integration:** Implement LSTM or BERT models for sequence-based URL analysis.
* **Visual Similarity Detection:** Compare website UI/logos against known legitimate brands.
* **Mobile Browser Support:** Extend support to Firefox and mobile-compatible browsers.
* **Threat Intelligence Feed:** Integrate with live APIs (e.g., PhishTank, VirusTotal) for real-time updates.

---

## 👨‍💻 Author

**Ritiz Shukla** *B.Tech in Artificial Intelligence & Machine Learning | Maharana Institute of Professional Studies* * **GitHub:** [@ritizshukla](https://github.com/ritizshukla)
* **Kaggle:** [rititizshukla](https://www.kaggle.com/ritizshukla)
* **LinkedIn:** [ritizshukla](https://www.linkedin.com/in/ritiz-shukla/)

---

## ⭐ Support

If you found this project helpful or learned something new, please consider giving it a ⭐ on GitHub!
```
