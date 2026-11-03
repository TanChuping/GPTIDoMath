// Use as an MV3 content script or run this entire expression in the page.
(() => {
  "use strict";
  const GLOBAL = "__gptidomathDriveApproval";
  const LOG_KEY = "gptidomath.drive-approval.log";
  if (window[GLOBAL]?.running) return window[GLOBAL].status();
  if (location.hostname !== "chatgpt.com") return { status: "wrong-host" };
  if (!document.body) return { status: "no-body" };

  const CARD = 'div[class~="@container/approval-card"]';
  const IGNORED = 'pre, code, [data-markdown-copy="code-block"], [contenteditable]:not([contenteditable="false"])';
  const LABELS = new Set(["Always allow", "始终允许"]);
  const normalize = (text) => (text || "").replace(/\s+/g, " ").trim();

  function findRequest(card) {
    if (!card.matches(CARD) || card.closest(IGNORED) || !card.isConnected) return null;
    if (card.querySelector(CARD) || card.closest('[hidden], [aria-hidden="true"]')) return null;
    const alert = card.querySelector('[role="alert"]');
    if (!alert || alert.closest(IGNORED) || !/允许|Allow/i.test(alert.textContent || "")) return null;
    if (normalize(alert.querySelector("span")?.textContent) !== "Google Drive") return null;
    const buttons = Array.from(card.querySelectorAll("form button")).filter(
      (button) => LABELS.has(normalize(button.textContent)),
    );
    if (buttons.length !== 1) return null;
    const button = buttons[0];
    if (button !== card.querySelector("form button") || button.closest(IGNORED)) return null;
    if (button.closest('[hidden], [aria-hidden="true"]')) return null;
    const text = normalize(alert.textContent);
    const match = text.match(/ChatGPT\s*将调用\s*Google Drive\s*的\s*(.{1,120}?)\s*工具/)
      ?? text.match(/ChatGPT will (?:call|use) Google Drive['’]s\s+(.{1,120}?)\s+tool\b/i);
    const tool = normalize(match?.[1]);
    if (!tool) return null;
    return {
      button,
      tool,
      signature: JSON.stringify(["Google Drive", tool]),
      enabled: !button.matches(":disabled") && button.getAttribute("aria-disabled") !== "true",
    };
  }

  function getLog() {
    try {
      const entries = JSON.parse(localStorage.getItem(LOG_KEY) || "[]");
      return Array.isArray(entries) ? entries.slice(-50) : [];
    } catch {
      return [];
    }
  }

  function record(tool, path, result) {
    try {
      const entries = getLog();
      entries.push({ time: new Date().toISOString(), tool, path, result });
      localStorage.setItem(LOG_KEY, JSON.stringify(entries.slice(-50)));
    } catch {
      // Storage availability does not determine whether a click may proceed.
    }
  }

  let running = true;
  let dispatching = false;
  const timers = new Map();
  const requests = new WeakMap();
  const cancel = (card) => {
    window.clearTimeout(timers.get(card));
    timers.delete(card);
  };

  function checkCard(card) {
    if (!running) return;
    const request = findRequest(card);
    if (!request) {
      cancel(card);
      return;
    }
    let state = requests.get(card);
    if (!state || state.signature !== request.signature) {
      cancel(card);
      state = {
        signature: request.signature,
        path: location.pathname,
        button: request.button,
        attempts: 0,
        lastAttemptAt: null,
        stopped: false,
      };
      requests.set(card, state);
    }
    if (state.stopped || state.path !== location.pathname || !request.enabled) {
      cancel(card);
      return;
    }
    if (state.button !== request.button) {
      cancel(card);
      state.button = request.button;
    }
    if (timers.has(card)) return;
    const active = state;
    const cooldown = state.lastAttemptAt === null
      ? 0 : Math.max(0, state.lastAttemptAt + 4000 - Date.now());
    // Delay mounting and replacements; never click inside a mutation callback.
    const timer = window.setTimeout(() => {
      timers.delete(card);
      if (!running || requests.get(card) !== active || active.stopped) return;
      if (active.path !== location.pathname) return;
      const current = findRequest(card);
      if (!current || !current.enabled) return;
      if (current.signature !== active.signature || current.button !== active.button) {
        checkCard(card);
        return;
      }
      if (active.attempts >= 3) {
        active.stopped = true;
        record(current.tool, active.path, "exhausted");
        return;
      }
      active.attempts += 1;
      active.lastAttemptAt = Date.now();
      try {
        dispatching = true;
        current.button.click();
        record(current.tool, active.path, "clicked");
      } catch {
        record(current.tool, active.path, "click-error");
      } finally {
        dispatching = false;
      }
      checkCard(card);
    }, cooldown + 1000 + Math.floor(Math.random() * 2001));
    timers.set(card, timer);
  }

  function onClick(event) {
    if (dispatching) return;
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest("button");
    const card = button?.closest(CARD);
    if (!card || !button?.closest("form") || button.closest(IGNORED)) return;
    cancel(card);
    const request = findRequest(card);
    if (request) {
      // A person's approval, denial, or dropdown choice stops this request.
      requests.set(card, {
        signature: request.signature,
        path: location.pathname,
        button: request.button,
        attempts: 0,
        lastAttemptAt: null,
        stopped: true,
      });
    }
  }

  function collectCards(root, cards) {
    if (root.closest(IGNORED)) return;
    const parent = root.closest(CARD);
    if (parent) cards.add(parent);
    root.querySelectorAll(CARD).forEach((card) => cards.add(card));
  }

  const observer = new MutationObserver((records) => {
    const cards = new Set();
    const added = new Set();
    for (const mutation of records) {
      const target = mutation.target instanceof Element ? mutation.target : mutation.target.parentElement;
      if (target?.closest(IGNORED)) continue;
      const card = target?.closest(CARD);
      if (card) cards.add(card);
      if (target && mutation.type === "attributes" && !card && mutation.attributeName !== "class") {
        added.add(target);
      }
      for (const node of mutation.addedNodes) {
        if (node instanceof Element) added.add(node);
      }
    }
    for (const root of added) {
      let parent = root.parentElement;
      while (parent && !added.has(parent)) parent = parent.parentElement;
      if (!parent) collectCards(root, cards);
    }
    cards.forEach(checkCard);
    for (const card of timers.keys()) {
      const state = requests.get(card);
      if (!card.isConnected || state?.path !== location.pathname) cancel(card);
    }
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["disabled", "aria-disabled", "hidden", "aria-hidden", "class"],
  });
  document.addEventListener("click", onClick, true);

  const api = {
    get running() { return running; },
    status() { return { status: running ? "watching" : "stopped", pending: timers.size }; },
    getLog,
    stop() {
      running = false;
      observer.disconnect();
      document.removeEventListener("click", onClick, true);
      timers.forEach((timer) => window.clearTimeout(timer));
      timers.clear();
      return api.status();
    },
  };
  window[GLOBAL] = api;
  const initial = new Set();
  collectCards(document.body, initial);
  initial.forEach(checkCard);
  return api.status();
})();
