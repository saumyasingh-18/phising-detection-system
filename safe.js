document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const targetUrl = params.get("url") || "https://www.google.com";

  const safeScoreValue = Number.parseFloat(params.get("safeScore") || "0");
  const safeScore = Number.isFinite(safeScoreValue)
    ? Math.max(0, Math.min(100, safeScoreValue))
    : 0;

  const secondsValue = Number.parseInt(params.get("seconds") || "3", 10);
  let seconds = Number.isFinite(secondsValue)
    ? Math.max(1, Math.min(10, secondsValue))
    : 3;

  const safeScoreEl = document.getElementById("safeScore");
  const statusSummaryEl = document.getElementById("statusSummary");
  const domainTextEl = document.getElementById("domainText");
  const countdownEl = document.getElementById("countdownText");
  const countdownFill = document.getElementById("countdownFill");
  const openBtn = document.getElementById("openSite");
  const totalSeconds = seconds;
  const totalMs = totalSeconds * 1000;
  const startedAt = Date.now();

  const formatPercent = value => {
    const normalized = Math.max(0, Math.min(100, value));
    return Number.isInteger(normalized) ? String(normalized) : normalized.toFixed(1);
  };

  const parsedDomain = (() => {
    try {
      return new URL(targetUrl).hostname;
    } catch {
      return "Unknown site";
    }
  })();

  safeScoreEl.textContent = `${formatPercent(safeScore)}%`;
  statusSummaryEl.textContent =
    safeScore >= 75
      ? "No major phishing indicators detected."
      : "Low to moderate risk signals were found, but this page was classified safe.";
  domainTextEl.textContent = parsedDomain;

  let hasNavigated = false;

  const sendAllowOnce = callback => {
    chrome.tabs.getCurrent(tab => {
      const message = {
        type: "allowOnce",
        url: targetUrl
      };

      if (tab && Number.isInteger(tab.id)) {
        message.tabId = tab.id;
      }

      chrome.runtime.sendMessage(message, callback);
    });
  };

  const navigateToTarget = () => {
    if (hasNavigated) return;
    hasNavigated = true;

    countdownFill.style.width = "100%";
    countdownEl.textContent = "Opening...";

    let fallbackTimer = null;
    const go = () => {
      if (fallbackTimer !== null) {
        clearTimeout(fallbackTimer);
      }
      window.location.replace(targetUrl);
    };

    fallbackTimer = setTimeout(go, 120);
    sendAllowOnce(go);
  };

  const updateCountdown = () => {
    const elapsedMs = Math.min(Date.now() - startedAt, totalMs);
    const remainingMs = Math.max(totalMs - elapsedMs, 0);
    seconds = Math.ceil(remainingMs / 1000);

    countdownEl.textContent = seconds > 0 ? `Opening in ${seconds}s` : "Opening...";
    const progress = (elapsedMs / totalMs) * 100;
    countdownFill.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  };

  updateCountdown();

  const timer = setInterval(() => {
    updateCountdown();
    if (seconds <= 0) {
      clearInterval(timer);
      navigateToTarget();
      return;
    }
  }, 120);

  openBtn.addEventListener("click", () => {
    clearInterval(timer);
    navigateToTarget();
  });
});
