document.addEventListener("DOMContentLoaded", async () => {

  const params = new URLSearchParams(window.location.search);
  const url = params.get("url");
  const fromUrl = params.get("from");
  const riskParam = params.get("risk");
  const explanationParam = params.get("exp");

  const riskValueEl = document.getElementById("riskValue");
  const confidenceText = document.getElementById("confidenceText");
  const domainText = document.getElementById("domainText");
  const explanationList = document.getElementById("explanation");
  const goBackBtn = document.getElementById("goBack");
  const continueBtn = document.getElementById("continue");
  
  let hasNavigated = false;
  let currentUrl = url;

  const formatPercent = value => {
    const normalized = Math.max(0, Math.min(100, value));
    return Number.isInteger(normalized) ? String(normalized) : normalized.toFixed(1);
  };

  const isSupportedUrl = value => /^https?:\/\//i.test(value || "");

  // Parse domain for display
  let parsedDomain = "Unknown site";
  try {
    parsedDomain = new URL(url).hostname;
  } catch {
    parsedDomain = "Unknown site";
  }
  domainText.textContent = parsedDomain;

  // Send allowOnce message to background script
  const sendAllowOnce = (callback) => {
    chrome.tabs.getCurrent(tab => {
      const message = {
        type: "allowOnce",
        url: currentUrl
      };

      if (tab && Number.isInteger(tab.id)) {
        message.tabId = tab.id;
      }

      chrome.runtime.sendMessage(message, () => {
        if (callback) callback();
      });
    });
  };

  // Convert confidence to risk band label
  const toRiskBand = (confidence) => {
    if (confidence >= 85) return "Critical";
    if (confidence >= 65) return "High";
    if (confidence >= 40) return "Medium";
    return "Elevated";
  };

  // Update UI with risk data
  const renderRisk = (confidence, explanationItems) => {
    const clamped = Math.max(0, Math.min(100, confidence));
    
    riskValueEl.textContent = formatPercent(clamped);
    confidenceText.textContent = `Risk Level: ${formatPercent(clamped)}%`;

    explanationList.innerHTML = "";
    if (explanationItems && Array.isArray(explanationItems) && explanationItems.length > 0) {
      explanationItems.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        explanationList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "Suspicious page behavior detected by model.";
      explanationList.appendChild(li);
    }
  };

  // Parse explanation parameter
  const parseExplanationParam = (raw) => {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(item => typeof item === "string" && item.trim().length > 0);
    } catch {
      return [];
    }
  };

  const paramRisk = Number.parseFloat(riskParam || "");
  const paramExplanation = parseExplanationParam(explanationParam);
  const hasParamRisk = Number.isFinite(paramRisk);

  // Use params if available, otherwise fetch from backend
  if (hasParamRisk) {
    renderRisk(paramRisk, paramExplanation);
  } else if (url) {
    try {
      const res = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      if (!res.ok) {
        throw new Error(`Prediction API failed with status ${res.status}`);
      }

      const data = await res.json();

      const numericConfidence = Number.isFinite(data.confidence) ? data.confidence : 0;
      const confidence = Math.max(0, Math.min(100, numericConfidence * 100));
      const explanationItems = Array.isArray(data.explanation)
        ? data.explanation
        : ["Suspicious page behavior detected by model."];

      renderRisk(confidence, explanationItems);
    } catch (err) {
      console.error("Prediction error:", err);
      renderRisk(72, ["Could not contact detection API. Treat this page as high risk unless verified."]);
    }
  }

  // Go Back button - return to previous page
  goBackBtn.addEventListener("click", () => {
    if (isSupportedUrl(fromUrl) && fromUrl !== url) {
      window.location.replace(fromUrl);
      return;
    }

    if (history.length > 2) {
      history.go(-2);
      return;
    }

    history.back();
  });

  // Continue Anyway button - bypass warning and navigate
  continueBtn.addEventListener("click", () => {
    if (hasNavigated || !currentUrl) return;
    hasNavigated = true;

    let navigationTimeout = null;

    const navigate = () => {
      if (navigationTimeout !== null) {
        clearTimeout(navigationTimeout);
      }
      window.location.href = currentUrl;
    };

    // Set timeout as fallback in case background script doesn't respond
    navigationTimeout = setTimeout(navigate, 150);
    
    // Send allowOnce message to background, then navigate
    sendAllowOnce(navigate);
  });
});
