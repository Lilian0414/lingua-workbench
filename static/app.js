(() => {
  "use strict";

  const DRAFT_KEY = "lingua-workbench-draft-v1";
  const form = document.querySelector("#translation-form");
  const lyrics = document.querySelector("#lyrics");
  const results = document.querySelector("#results");
  const savedStatus = document.querySelector("#saved-status");
  let saveTimer;

  const lineElements = () => Array.from(document.querySelectorAll(".translation-line"));

  function sourceLanguage() {
    return document.querySelector('input[name="source_language"]:checked')?.value ||
      results?.dataset.language || "ja";
  }

  function currentTranslations() {
    return Object.fromEntries(lineElements().map((line) => [
      line.dataset.lineId,
      line.querySelector(".translation-input").value,
    ]));
  }

  function saveDraft() {
    if (!lyrics) return;
    const draft = {
      sourceLanguage: sourceLanguage(),
      provider: document.querySelector("#provider")?.value || "groq",
      lyrics: lyrics.value,
      translations: currentTranslations(),
      savedAt: Date.now(),
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    if (savedStatus) savedStatus.textContent = "已儲存在這台裝置。";
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    if (savedStatus) savedStatus.textContent = "正在儲存變更…";
    saveTimer = setTimeout(saveDraft, 350);
  }

  function restoreDraft() {
    let draft;
    try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch { return; }
    if (!draft) return;
    if (lyrics && !lyrics.value && !results && draft.lyrics) {
      lyrics.value = draft.lyrics;
      const languageControl = document.querySelector(
        `input[name="source_language"][value="${draft.sourceLanguage}"]`
      );
      if (languageControl) languageControl.checked = true;
      const providerControl = document.querySelector("#provider");
      if (providerControl && ["groq", "google"].includes(draft.provider)) {
        providerControl.value = draft.provider;
      }
    }
    if (results && draft.lyrics === lyrics?.value && draft.sourceLanguage === sourceLanguage()) {
      lineElements().forEach((line) => {
        const value = draft.translations?.[line.dataset.lineId];
        if (typeof value === "string") line.querySelector(".translation-input").value = value;
      });
    }
  }

  function sourceText() {
    if (lyrics?.value) return lyrics.value;
    return lineElements().map((line) => line.dataset.original).join("\n");
  }

  function setBusy(line, busy, message = "") {
    line.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
    line.querySelector(".line-status").textContent = message;
  }

  function showCandidate(line, translation, provider) {
    const candidate = line.querySelector(".candidate");
    candidate.querySelector(".candidate-provider").textContent = provider;
    candidate.querySelector(".candidate-text").textContent = translation;
    candidate.hidden = false;
  }

  async function requestCandidate(line, endpoint, instruction = "") {
    setBusy(line, true, "正在整理這一行…");
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lyrics: sourceText(),
          source_language: sourceLanguage(),
          target_id: Number(line.dataset.lineId),
          current_translations: currentTranslations(),
          instruction,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "暫時無法取得翻譯");
      showCandidate(line, payload.translation, payload.provider);
      line.querySelector(".line-status").textContent = "新的候選譯文已經準備好。";
    } catch (error) {
      line.querySelector(".line-status").textContent = error.message;
    } finally {
      setBusy(line, false, line.querySelector(".line-status").textContent);
    }
  }

  lineElements().forEach((line) => {
    const input = line.querySelector(".translation-input");
    const panel = line.querySelector(".instruction-panel");
    const candidate = line.querySelector(".candidate");
    input.addEventListener("input", scheduleSave);
    line.querySelector(".google-button").addEventListener("click", () => requestCandidate(line, "/api/google-line"));
    line.querySelector(".regenerate-button").addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) panel.querySelector("input").focus();
    });
    line.querySelector(".regenerate-confirm").addEventListener("click", () => {
      requestCandidate(line, "/api/regenerate-line", panel.querySelector("input").value);
      panel.hidden = true;
    });
    line.querySelector(".apply-candidate").addEventListener("click", () => {
      input.value = candidate.querySelector(".candidate-text").textContent;
      line.querySelector(".provider-badge").textContent = candidate.querySelector(".candidate-provider").textContent;
      candidate.hidden = true;
      scheduleSave();
    });
    line.querySelector(".dismiss-candidate").addEventListener("click", () => { candidate.hidden = true; });
  });

  function exportText() {
    const readingLabel = results?.dataset.readingLabel || "拼音";
    const blocks = lineElements().map((line) => [
      line.dataset.original,
      `${readingLabel}：${line.dataset.reading}`,
      `中文：${line.querySelector(".translation-input").value}`,
    ].join("\n"));
    return blocks.join("\n\n");
  }

  document.querySelector("#copy-button")?.addEventListener("click", async (event) => {
    await navigator.clipboard.writeText(exportText());
    event.currentTarget.textContent = "已複製";
    setTimeout(() => { event.currentTarget.textContent = "複製全文"; }, 1400);
  });

  document.querySelector("#download-button")?.addEventListener("click", () => {
    const blob = new Blob([exportText()], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${sourceLanguage() === "ko" ? "韓文" : "日文"}歌詞翻譯.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  });

  form?.addEventListener("submit", () => {
    const button = document.querySelector("#submit-button");
    const status = document.querySelector("#form-status");
    if (button) button.disabled = true;
    if (status) status.textContent = "正在保留分行並整理翻譯，請稍候…";
    saveDraft();
  });

  lyrics?.addEventListener("input", scheduleSave);
  document.querySelectorAll('input[name="source_language"], #provider').forEach((control) => {
    control.addEventListener("change", scheduleSave);
  });
  restoreDraft();
})();
