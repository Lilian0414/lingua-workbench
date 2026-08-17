# Security Policy

請勿在公開 issue 貼出 API key、歌詞草稿或其他敏感資料。若發現安全問題，請透過 GitHub repository owner 的私人聯絡方式回報。

- `.env` 不會提交到 Git。
- API key 僅由部署者透過環境變數設定，不向一般網站使用者索取。
- 自訂 LLM 端點不接受訪客輸入，避免伺服器端請求偽造（SSRF）。
- 瀏覽器草稿儲存在使用者自己的 `localStorage`。
- 伺服器不建立歌詞資料庫；文字只在翻譯請求期間處理。
