# Contributing

謝謝你想改善 Lingua Workbench。請先建立 issue 說明使用情境，再提交小而明確的 pull request。

## 開發流程

1. Fork repository 並建立功能分支。
2. 安裝 `requirements-dev.txt`。
3. 修改程式與對應測試。
4. 執行 `pytest -q`、`node --check static/app.js` 與 `python -m compileall -q .`。
5. PR 內說明問題、做法與手動驗證結果。

新增語言請實作 `languages.base.LanguagePack`，再加入 registry；不要把特定語言判斷散落到 provider 或 UI。
