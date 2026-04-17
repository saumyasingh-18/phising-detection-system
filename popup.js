const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");
const domainText = document.getElementById("domainText");
const meterFill = document.getElementById("meterFill");
const scoreText = document.getElementById("scoreText");
const metaText = document.getElementById("metaText");
const scanBtn = document.getElementById("scanNow");

function normalizeConfidence(value) {
	const confidence = Number.isFinite(value) ? value : 0;
	return Math.max(0, Math.min(100, Math.round(confidence * 100)));
}

function toDomain(url) {
	try {
		return new URL(url).hostname;
	} catch {
		return "Unknown domain";
	}
}

function setStatus({ label, color, domain, risk, meta }) {
	statusLabel.textContent = label;
	statusDot.style.background = color;
	domainText.textContent = domain;
	meterFill.style.width = `${Math.max(0, Math.min(100, risk))}%`;
	scoreText.textContent = `Risk score: ${risk}%`;
	metaText.textContent = meta;
}

function buildWarningUrl(targetUrl, confidence, explanation) {
	const risk = Math.max(0, Math.min(100, Math.round(confidence * 100)));
	const compactExplanation = explanation
		.filter(item => typeof item === "string")
		.slice(0, 5)
		.map(item => item.slice(0, 180));

	return chrome.runtime.getURL(
		`warning/warning.html?url=${encodeURIComponent(targetUrl)}&risk=${encodeURIComponent(String(risk))}&exp=${encodeURIComponent(JSON.stringify(compactExplanation))}`
	);
}

function isScannableUrl(url) {
	return /^https?:\/\//i.test(url || "");
}

async function getActiveTab() {
	const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
	return tabs[0];
}

async function readLastScan() {
	const data = await chrome.storage.local.get(["lastScan"]);
	return data.lastScan || null;
}

async function renderInitialState() {
	const activeTab = await getActiveTab();
	if (!activeTab || !isScannableUrl(activeTab.url)) {
		setStatus({
			label: "Unsupported",
			color: "#7a848d",
			domain: "Open any HTTP or HTTPS page",
			risk: 0,
			meta: "Chrome and extension pages cannot be scanned"
		});
		scanBtn.disabled = true;
		return;
	}

	scanBtn.disabled = false;
	const fallbackDomain = toDomain(activeTab.url);
	const lastScan = await readLastScan();

	if (!lastScan || lastScan.url !== activeTab.url) {
		setStatus({
			label: "Ready",
			color: "#4a7a9f",
			domain: fallbackDomain,
			risk: 0,
			meta: "Tap scan to analyze this tab now"
		});
		return;
	}

	const risk = normalizeConfidence(lastScan.confidence);

	if (lastScan.status === "phishing") {
		setStatus({
			label: "Danger",
			color: "#d84c3f",
			domain: fallbackDomain,
			risk,
			meta: "High-risk signals detected"
		});
		return;
	}

	if (lastScan.status === "safe") {
		setStatus({
			label: "Safe",
			color: "#14a36a",
			domain: fallbackDomain,
			risk,
			meta: "No major indicators found"
		});
		return;
	}

	if (lastScan.status === "checking") {
		setStatus({
			label: "Checking",
			color: "#e09a2e",
			domain: fallbackDomain,
			risk,
			meta: "Model scan in progress"
		});
		return;
	}

	setStatus({
		label: "Error",
		color: "#ba5849",
		domain: fallbackDomain,
		risk: 0,
		meta: "Backend unavailable. Verify API service."
	});
}

async function scanCurrentTab() {
	const activeTab = await getActiveTab();
	if (!activeTab || !isScannableUrl(activeTab.url)) return;

	scanBtn.disabled = true;
	scanBtn.textContent = "Scanning...";

	try {
		const response = await fetch("http://127.0.0.1:8000/predict", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ url: activeTab.url })
		});

		if (!response.ok) {
			throw new Error(`Prediction API failed with status ${response.status}`);
		}

		const data = await response.json();
		const confidence = Number.isFinite(data.confidence) ? data.confidence : 0;
		const risk = normalizeConfidence(confidence);

		await chrome.storage.local.set({
			lastScan: {
				timestamp: Date.now(),
				url: activeTab.url,
				status: data.prediction === 1 ? "phishing" : "safe",
				confidence,
				prediction: data.prediction,
				explanation: Array.isArray(data.explanation) ? data.explanation : []
			}
		});

		if (data.prediction === 1) {
			const explanation = Array.isArray(data.explanation) ? data.explanation : [];
			const warningPage = buildWarningUrl(activeTab.url, confidence, explanation);
			await chrome.tabs.update(activeTab.id, { url: warningPage });
			window.close();
			return;
		}

		const safeScore = Math.max(0, Math.min(100, (1 - confidence) * 100));
		const safePage = chrome.runtime.getURL(
			`safe/safe.html?url=${encodeURIComponent(activeTab.url)}&safeScore=${safeScore}&seconds=3`
		);
		await chrome.tabs.update(activeTab.id, { url: safePage });
		window.close();
		return;
	} catch (error) {
		setStatus({
			label: "Error",
			color: "#ba5849",
			domain: toDomain(activeTab.url),
			risk: 0,
			meta: "Scan failed. Start backend and try again."
		});

		await chrome.storage.local.set({
			lastScan: {
				timestamp: Date.now(),
				url: activeTab.url,
				status: "error",
				error: String(error)
			}
		});
	} finally {
		scanBtn.disabled = false;
		scanBtn.textContent = "Scan This Tab";
	}
}

scanBtn.addEventListener("click", () => {
	scanCurrentTab();
});

renderInitialState().catch(() => {
	setStatus({
		label: "Error",
		color: "#ba5849",
		domain: "Unable to load tab state",
		risk: 0,
		meta: "Please reopen popup"
	});
});
