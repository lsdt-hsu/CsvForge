# CsvForge

An Antigravity-powered, row-by-row CSV processing workspace.

> 本專案是 1% 的軟體工程師與 99% 的 Antigravity IDE + Gemini 網頁版。
> 
> This project is 1% software engineer and 99% Antigravity IDE + Gemini Web App.

---

## 🇹🇼 繁體中文說明

`CsvForge` 是一個用來批次處理CSV（Comma-Separated Values）檔案的的輕量級工作台。你可以直接使用內建功能，或者自己（或叫你的AI伙伴）建立你想要的外掛，投入這個熔爐中。

這個專案是我自己做好玩的，不保證會認真維護。如果你有任何想法，可以自行開發外掛，不必貢獻回本專案。

### 內建功能

*   **精密範圍過濾 (Advanced Scope Filtering)：** 內建強大的過濾引擎，支援複雜的過濾規則（包括 Regular Expression 與語系檢查），讓你自由且精準地控制需要處理的資料範圍。
*   **高速批次翻譯 (High-Throughput Translation)：** 整合 Google 翻譯 API，特別針對**大量小字串**進行批次優化，大幅提升多語系資料的處理效率。
*   **動態 AI 提示詞加工 (Dynamic AI Prompt Engineering)：** 支援逐行將指定欄位的內容動態帶入自訂 Prompt 中（例如：`把 "{1. 物件名稱}" 翻譯成英文`）。*註：目前支援的 AI 後台較為有限。*
*   **條件式欄位覆寫 (Conditional Value Overwrite)：** 支援在目標欄位中批次貼上手動輸入值，或直接複製同檔案中其他欄位的內容。結合「範圍過濾」功能，可實現極為靈活的條件式局部覆寫。
*   **AI 友善的外掛架構 (AI-Friendly Plugin Architecture)：** 採用高度解耦的外掛介面。專案內附一份**完整的外掛開發指南**，你可以直接把指南餵給大型語言模型（LLM），讓 AI 幫你秒級生成符合標準的自訂外掛功能。

---

## English Description

`CsvForge` is a lightweight workspace built for batch-processing CSV (Comma-Separated Values) files. You can stick with the built-in tools, or forge your own custom plugins—either by yourself or by teaming up with your AI sidekick—and toss them right into the furnace.

This project is just a personal side project built for fun, and I make zero promises about maintaining it. If you have any wild ideas, just build your own plugin—no need to contribute back to this repo.

### Built-In Features

*   **Advanced Scope Filtering:** Features a robust filtering engine supporting complex rules, including Regular Expressions and Language/Locale detection, giving you full control over the exact range of data to process.
*   **High-Throughput Translation:** Integrated with the Google Translation API, highly optimized for batch-translating **massive amounts of short strings** with exceptional speed.
*   **Dynamic AI Prompt Engineering:** Allows you to dynamically inject specific column values into custom prompts row-by-row (e.g., `"Translate '{1. Item Name}' into English"`). *Note: Currently supports a limited selection of AI backends.*
*   **Conditional Value Overwrite:** Supports batch-pasting manually entered values into target columns or duplicating contents from another column within the same file. When paired with the "Scope Filtering" feature, it enables highly flexible conditional overwrites.
*   **AI-Friendly Plugin Architecture:** Built on a highly decoupled plugin interface. Accompanied by a **comprehensive Plugin Development Guide**, which you can feed directly to any LLM to let AI generate compliant, custom plugin extensions in seconds.
