# Lingua Workbench

一個以「語言包」為核心的歌詞翻譯工作台。目前支援：

- 日文 → 台灣繁體中文＋Hepburn 羅馬字
- 韓文 → 台灣繁體中文＋韓文修訂式羅馬字
- 任意 OpenAI-compatible AI 服務的整首翻譯與逐句重新生成
- Googletrans 快速翻譯與逐句候選
- 保留原文分行、譯文直接編輯、瀏覽器草稿、複製與 TXT 匯出

此 repository 是從既有日文翻譯專案抽出的新架構；原專案與其部署不受影響。

## 選擇要安裝的語言

這個框架在下載／部署時就能決定要帶哪些語言：

```bash
# 只做日文版
pip install -r requirements-ja.txt
export ENABLED_LANGUAGES=ja

# 只做韓文版
pip install -r requirements-ko.txt
export ENABLED_LANGUAGES=ko

# 日韓都要（預設）
pip install -r requirements-all.txt
export ENABLED_LANGUAGES=ja,ko
```

只啟用一種語言時，網頁不顯示語言切換器。`DEFAULT_SOURCE_LANGUAGE` 可指定多語言版本預設選取哪一種。

## 架構

```text
core/       分行、資料模型、結果組裝與錯誤
languages/  日文與韓文的拼音、翻譯提示與語言 metadata
providers/  通用 LLM、Googletrans，僅依賴 LanguagePack 介面
templates/  Flask 頁面
static/     無框架的互動與紙本視覺
tests/      核心、語言包、供應商與 Flask 路由測試
```

新增語言時，只需實作 `LanguagePack` 並註冊到 `languages/registry.py`，翻譯服務與 UI 不必複製一套。

## 本機啟動

需要 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask --app app run --debug
```

AI 翻譯由部署者設定，網站的一般使用者不需要也不會被要求填 API key。若只使用 Google 翻譯，可以不設定 AI 服務。

## 選擇 AI 廠商

任何提供 OpenAI-compatible `POST /chat/completions` 的服務都能使用：

```env
LLM_API_KEY=your_provider_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
LLM_DISPLAY_NAME=AI 翻譯
LLM_RESPONSE_FORMAT=json_schema
```

例如可接 OpenAI、OpenRouter、DeepSeek 或其他相容廠商，只需換掉 `LLM_BASE_URL`、`LLM_MODEL` 與 API key。自訂端點只接受部署環境變數，不開放網站訪客填寫，以免公開服務出現 SSRF 風險。

各廠商支援的結構化輸出不同：

- `json_schema`：最嚴格，適合支援 JSON Schema 的模型。
- `json_object`：廠商只支援 JSON mode 時使用。
- `prompt_only`：完全不支援 `response_format` 時使用，框架仍會驗證每個行號。


## 測試

```bash
pytest -q
node --check static/app.js
python -m compileall -q .
```

## Vercel

1. 將 repository 匯入 Vercel。
2. 新增 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 環境變數。
3. 部署；`vercel.json` 已將 Flask 入口指向 `app.py`。


## 技術選擇

- Flask：維持既有 Python 後端的低遷移成本。
- `pykakasi`：日文 Hepburn 羅馬字。
- `koroman`：韓文修訂式羅馬字與常見發音規則。
- OpenAI-compatible Chat Completions＋回傳驗證：支援不同 AI 廠商並確保譯文逐行對齊。
- 原生 JavaScript：避免前端框架負擔，保持手機操作輕量。

## 授權

[MIT](LICENSE)
