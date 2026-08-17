(() => {
  "use strict";

  const DRAFT_KEY = "lingua-workbench-draft-v2";
  const form = document.querySelector("#lyrics-form");
  const lyrics = document.querySelector("#lyrics");
  const submitButton = document.querySelector("#submit-button");
  const results = document.querySelector("#results");
  const feedbackTimers = new WeakMap();
  let saveTimer;

  const lyricLines = () => Array.from(document.querySelectorAll("#lyrics-output .lyric-line"));

  function sourceLanguage() {
    return document.querySelector('input[name="source_language"]:checked')?.value ||
      document.querySelector('input[name="source_language"]')?.value ||
      results?.dataset.language || "ja";
  }

  function selectedProvider() {
    return document.querySelector('input[name="provider"]:checked')?.value || "ai";
  }

  function currentTranslation(article) {
    return article.querySelector(".translation-editor").value.trim();
  }

  function collectTranslations() {
    return Object.fromEntries(
      lyricLines().map((article) => [article.dataset.lineId, currentTranslation(article)])
    );
  }

  function buildSourceLyrics() {
    if (lyrics?.value) return lyrics.value;
    return Array.from(document.querySelectorAll("#lyrics-output > *"))
      .map((element) => element.classList.contains("paragraph-break") ? "" : element.dataset.original)
      .join("\n");
  }

  function buildPlainText() {
    const readingLabel = results?.dataset.readingLabel || "拼音";
    let output = "";
    let preservedBlankLines = 0;
    for (const element of document.querySelectorAll("#lyrics-output > *")) {
      if (element.classList.contains("paragraph-break")) {
        preservedBlankLines += 1;
        continue;
      }
      if (output) output += "\n".repeat(2 + preservedBlankLines);
      output += [
        element.dataset.original,
        `${readingLabel}：${element.dataset.reading}`,
        `中文：${currentTranslation(element)}`,
      ].join("\n");
      preservedBlankLines = 0;
    }
    return output;
  }

  function setStatus(message, type = "") {
    const status = document.querySelector("#interaction-status");
    if (!status) return;
    status.textContent = message;
    status.className = `status ${type}`.trim();
  }

  function setLineStatus(article, message, type = "") {
    const status = article.querySelector(".line-status");
    status.textContent = message;
    status.className = `line-status ${type}`.trim();
  }

  function flashButton(button, temporaryLabel, type = "success", duration = 1500) {
    if (!button) return;
    const idleLabel = button.dataset.idleLabel || button.textContent.trim();
    button.dataset.idleLabel = idleLabel;
    button.textContent = temporaryLabel;
    button.classList.remove("feedback-success", "feedback-error");
    button.classList.add(type === "error" ? "feedback-error" : "feedback-success");
    clearTimeout(feedbackTimers.get(button));
    feedbackTimers.set(button, setTimeout(() => {
      button.textContent = idleLabel;
      button.classList.remove("feedback-success", "feedback-error");
    }, duration));
  }

  function setButtonLoading(button, loading, label = "處理中…") {
    if (loading) {
      button.dataset.idleLabel = button.textContent.trim();
      button.textContent = label;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      return;
    }
    button.textContent = button.dataset.idleLabel;
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }

  function updateProviderBadge(article, provider, displayName = "") {
    article.dataset.provider = provider;
    const badge = article.querySelector(".provider-badge");
    badge.textContent = provider === "google" ? "Google" :
      (displayName || results?.dataset.aiProviderName || "AI");
    badge.className = `provider-badge ${provider}`;
  }

  function updateEditedState(article) {
    const edited = currentTranslation(article) !== article.dataset.initialTranslation;
    article.querySelector(".edited-badge").hidden = !edited;
    article.classList.toggle("is-edited", edited);
  }

  function saveDraft() {
    if (!lyrics) return;
    const lines = Object.fromEntries(lyricLines().map((article) => [article.dataset.lineId, {
      text: article.querySelector(".translation-editor").value,
      provider: article.dataset.provider,
    }]));
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        sourceLanguage: sourceLanguage(),
        provider: selectedProvider(),
        lyrics: lyrics.value,
        lines,
      }));
    } catch {
      // Browser storage is optional.
    }
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    setStatus("正在儲存變更…");
    saveTimer = setTimeout(() => {
      saveDraft();
      setStatus("已儲存在這台裝置。", "success");
    }, 350);
  }

  function restoreDraft() {
    let draft;
    try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch { return; }
    if (!draft) return;
    if (!results && lyrics && !lyrics.value && draft.lyrics) {
      lyrics.value = draft.lyrics;
      document.querySelector(`input[name="source_language"][value="${draft.sourceLanguage}"]`)?.click();
      document.querySelector(`input[name="provider"][value="${draft.provider}"]`)?.click();
      return;
    }
    if (!results || draft.lyrics !== lyrics?.value || draft.sourceLanguage !== sourceLanguage()) return;
    for (const article of lyricLines()) {
      const saved = draft.lines?.[article.dataset.lineId];
      if (!saved || typeof saved.text !== "string") continue;
      article.querySelector(".translation-editor").value = saved.text;
      if (["ai", "google"].includes(saved.provider)) updateProviderBadge(article, saved.provider);
      updateEditedState(article);
    }
    setStatus("已恢復上次尚未完成的修改。", "success");
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "服務暫時沒有回應，請稍後再試。");
    return data;
  }

  for (const article of lyricLines()) {
    article.dataset.initialProvider = article.dataset.provider;
    const editor = article.querySelector(".translation-editor");

    editor.addEventListener("input", () => {
      updateEditedState(article);
      scheduleSave();
      setLineStatus(article, "已儲存在這台裝置的瀏覽器中。", "success");
    });

    article.querySelector(".reset-line-button").addEventListener("click", (event) => {
      editor.value = article.dataset.initialTranslation;
      updateProviderBadge(article, article.dataset.initialProvider);
      updateEditedState(article);
      article.querySelectorAll(".candidate-panel").forEach((panel) => { panel.hidden = true; });
      scheduleSave();
      setLineStatus(article, "已還原這一句。", "success");
      flashButton(event.currentTarget, "✓ 已還原");
    });

    article.querySelector(".regenerate-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      const style = article.querySelector(".style-select").value;
      const custom = article.querySelector(".custom-instruction").value.trim();
      const instruction = custom ? `${style}；補充要求：${custom}` : style;
      let label = "✓ 已產生";
      let type = "success";
      setButtonLoading(button, true, "AI 生成中…");
      setLineStatus(article, "正在參考完整歌詞重新翻譯這一句…");
      try {
        const data = await postJson("/api/regenerate-line", {
          lyrics: buildSourceLyrics(),
          source_language: sourceLanguage(),
          target_id: Number(article.dataset.lineId),
          current_translations: collectTranslations(),
          instruction,
        });
        const panel = article.querySelector(".ai-candidate");
        panel.querySelector(".candidate-text").textContent = data.translation;
        panel.querySelector(".candidate-title").textContent = `${data.provider}候選版本`;
        panel.dataset.displayName = data.provider;
        panel.hidden = false;
        setLineStatus(article, "AI 候選版本已產生，確認後再套用。", "success");
      } catch (error) {
        setLineStatus(article, error.message, "error");
        label = "重試";
        type = "error";
      } finally {
        setButtonLoading(button, false);
        flashButton(button, label, type);
      }
    });

    article.querySelector(".google-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      let label = "✓ 已取得";
      let type = "success";
      setButtonLoading(button, true, "Google 翻譯中…");
      setLineStatus(article, "正在取得 Google 參考版本…");
      try {
        const data = await postJson("/api/google-line", {
          lyrics: buildSourceLyrics(),
          source_language: sourceLanguage(),
          target_id: Number(article.dataset.lineId),
        });
        const panel = article.querySelector(".google-candidate");
        panel.querySelector(".candidate-text").textContent = data.translation;
        panel.hidden = false;
        setLineStatus(article, "Google 參考版本已取得，確認後再套用。", "success");
      } catch (error) {
        setLineStatus(article, error.message, "error");
        label = "重試";
        type = "error";
      } finally {
        setButtonLoading(button, false);
        flashButton(button, label, type);
      }
    });

    for (const panel of article.querySelectorAll(".candidate-panel")) {
      panel.querySelector(".apply-candidate").addEventListener("click", (event) => {
        editor.value = panel.querySelector(".candidate-text").textContent;
        updateProviderBadge(article, panel.dataset.provider, panel.dataset.displayName);
        updateEditedState(article);
        panel.hidden = true;
        scheduleSave();
        setLineStatus(article, "已套用候選翻譯。", "success");
        flashButton(event.currentTarget, "✓ 已套用");
      });
      panel.querySelector(".dismiss-candidate").addEventListener("click", (event) => {
        panel.hidden = true;
        setLineStatus(article, "已保留目前的翻譯。", "success");
        flashButton(event.currentTarget, "✓ 已保留");
      });
    }
  }

  async function copyText(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.className = "clipboard-helper";
    document.body.appendChild(helper);
    helper.select();
    const copied = document.execCommand("copy");
    helper.remove();
    if (!copied) throw new Error("copy failed");
  }

  document.querySelector("#copy-button")?.addEventListener("click", async (event) => {
    try {
      await copyText(buildPlainText());
      setStatus("✓ 已複製目前編輯的完整結果。", "success");
      flashButton(event.currentTarget, "✓ 已複製");
    } catch {
      setStatus("無法自動複製，請手動選取內容。", "error");
      flashButton(event.currentTarget, "複製失敗", "error");
    }
  });

  document.querySelector("#download-button")?.addEventListener("click", (event) => {
    const blob = new Blob([buildPlainText()], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${sourceLanguage() === "ko" ? "韓文" : "日文"}歌詞翻譯.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
    setStatus("✓ 下載已開始，內容包含目前所有修改。", "success");
    flashButton(event.currentTarget, "✓ 下載中");
  });

  form?.addEventListener("submit", () => {
    saveDraft();
    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");
    submitButton.querySelector(".button-label").hidden = true;
    submitButton.querySelector(".loading-label").hidden = false;
  });

  document.querySelector("#clear-button")?.addEventListener("click", (event) => {
    lyrics.value = "";
    document.querySelector("#form-error")?.remove();
    results?.remove();
    submitButton.disabled = false;
    submitButton.removeAttribute("aria-busy");
    submitButton.querySelector(".button-label").hidden = false;
    submitButton.querySelector(".loading-label").hidden = true;
    try { localStorage.removeItem(DRAFT_KEY); } catch { /* optional */ }
    flashButton(event.currentTarget, "已清空");
    lyrics.focus();
  });

  lyrics?.addEventListener("input", scheduleSave);
  document.querySelectorAll('input[name="source_language"], input[name="provider"]').forEach((control) => {
    control.addEventListener("change", scheduleSave);
  });
  restoreDraft();
})();
