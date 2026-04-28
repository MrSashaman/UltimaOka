console.log("WELCOME TO ULTIMAOKA DASHBOARD");

const apiBaseUrl = window.location.protocol === "file:"
    ? "http://127.0.0.1:8080"
    : "";
const apiUrl = `${apiBaseUrl}/api/stats`;
const devRawUrl = `${apiBaseUrl}/api/devraw`;
const settingsKey = "ultimaoka-dashboard-settings";

const defaultSettings = {
    theme: "light",
    refreshInterval: 5000,
    compactMode: false,
    showDevRaw: true,
    visibleCards: {
        totalUsers: true,
        memberCount: true,
        serverCount: true,
        commandCount: true,
        latency: true,
        eventSubscribers: true,
    },
};

let settings = loadSettings();
let refreshTimer = null;

const refreshButton = document.getElementById("myButton");
const downloadDevRaw = document.getElementById("downloadDevRaw");
const message = document.getElementById("message");
const resetSettingsButton = document.getElementById("resetSettings");
const refreshIntervalSelect = document.getElementById("refreshInterval");
const compactModeInput = document.getElementById("compactMode");
const showDevRawInput = document.getElementById("showDevRaw");

const elements = {
    botName: document.getElementById("botName"),
    botStatus: document.getElementById("botStatus"),
    totalUsers: document.getElementById("totalUsers"),
    memberCount: document.getElementById("memberCount"),
    serverCount: document.getElementById("serverCount"),
    commandCount: document.getElementById("commandCount"),
    latency: document.getElementById("latency"),
    eventSubscribers: document.getElementById("eventSubscribers"),
};

function loadSettings() {
    try {
        const storedSettings = JSON.parse(localStorage.getItem(settingsKey));

        return {
            ...defaultSettings,
            ...storedSettings,
            visibleCards: {
                ...defaultSettings.visibleCards,
                ...(storedSettings ? storedSettings.visibleCards : {}),
            },
        };
    } catch (_error) {
        return { ...defaultSettings, visibleCards: { ...defaultSettings.visibleCards } };
    }
}

function saveSettings() {
    localStorage.setItem(settingsKey, JSON.stringify(settings));
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("ru-RU");
}

function setMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
}

function setActiveSection(sectionName) {
    document.querySelectorAll(".page-section").forEach((section) => {
        section.classList.toggle("active", section.id === `${sectionName}Section`);
    });

    document.querySelectorAll("[data-section-link]").forEach((link) => {
        link.classList.toggle("active", link.dataset.sectionLink === sectionName);
    });
}

function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.body.classList.toggle("compact-mode", settings.compactMode);

    refreshIntervalSelect.value = String(settings.refreshInterval);
    compactModeInput.checked = settings.compactMode;
    showDevRawInput.checked = settings.showDevRaw;
    downloadDevRaw.hidden = !settings.showDevRaw;

    document.querySelectorAll("[data-theme-option]").forEach((button) => {
        button.classList.toggle("active", button.dataset.themeOption === settings.theme);
    });

    document.querySelectorAll("[data-card]").forEach((card) => {
        const cardName = card.dataset.card;
        card.hidden = !settings.visibleCards[cardName];
    });

    document.querySelectorAll("[data-card-toggle]").forEach((input) => {
        input.checked = Boolean(settings.visibleCards[input.dataset.cardToggle]);
    });

    startAutoRefresh();
}

function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }

    if (settings.refreshInterval > 0) {
        refreshTimer = setInterval(updateStats, settings.refreshInterval);
    }
}

function renderStats(stats) {
    elements.botName.textContent = stats.bot_name || "UltimaOka";
    elements.botStatus.textContent = stats.status || "unknown";
    elements.totalUsers.textContent = formatNumber(stats.registered_users);
    elements.memberCount.textContent = formatNumber(stats.members);
    elements.serverCount.textContent = formatNumber(stats.servers);
    elements.commandCount.textContent = formatNumber(stats.commands);
    elements.latency.textContent = `${formatNumber(stats.latency_ms)} ms`;
    elements.eventSubscribers.textContent = formatNumber(stats.event_subscribers);

    const updatedAt = stats.updated_at ? new Date(stats.updated_at) : new Date();
    setMessage(`Updated: ${updatedAt.toLocaleString("ru-RU")}`);
}

async function updateStats() {
    refreshButton.disabled = true;
    setMessage("Loading stats...");

    try {
        const response = await fetch(apiUrl, { cache: "no-store" });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const stats = await response.json();
        renderStats(stats);
    } catch (error) {
        console.error("Dashboard stats error:", error);
        setMessage("Stats unavailable. Start the Python bot and open http://127.0.0.1:8080", true);
    } finally {
        refreshButton.disabled = false;
    }
}

function setupSettingsHandlers() {
    document.querySelectorAll("[data-section-link]").forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            setActiveSection(link.dataset.sectionLink);
            history.replaceState(null, "", `#${link.dataset.sectionLink}`);
        });
    });

    document.querySelectorAll("[data-theme-option]").forEach((button) => {
        button.addEventListener("click", () => {
            settings.theme = button.dataset.themeOption;
            saveSettings();
            applySettings();
        });
    });

    refreshIntervalSelect.addEventListener("change", () => {
        settings.refreshInterval = Number(refreshIntervalSelect.value);
        saveSettings();
        applySettings();
    });

    compactModeInput.addEventListener("change", () => {
        settings.compactMode = compactModeInput.checked;
        saveSettings();
        applySettings();
    });

    showDevRawInput.addEventListener("change", () => {
        settings.showDevRaw = showDevRawInput.checked;
        saveSettings();
        applySettings();
    });

    document.querySelectorAll("[data-card-toggle]").forEach((input) => {
        input.addEventListener("change", () => {
            settings.visibleCards[input.dataset.cardToggle] = input.checked;
            saveSettings();
            applySettings();
        });
    });

    resetSettingsButton.addEventListener("click", () => {
        settings = JSON.parse(JSON.stringify(defaultSettings));
        saveSettings();
        applySettings();
    });
}

downloadDevRaw.href = devRawUrl;
refreshButton.addEventListener("click", updateStats);

setupSettingsHandlers();
applySettings();
setActiveSection(window.location.hash === "#settings" ? "settings" : "dashboard");
updateStats();
