# Instascribe: LLM Dataset Optimizer

**Instascribe** is a professional-grade Python utility that transforms messy Instagram DM JSON exports into structured, high-signal datasets. It is specifically designed to optimize personal conversation history for deep analysis by Large Language Models (LLMs) like GPT-4o and Claude 3.5.

## 🌟 Why Instascribe?

Instagram's raw data export is built for archival, not for machine intelligence. It uses broken "mojibake" encoding for emojis, lacks conversational turn-taking structure, and is bloated with tracking metadata. **Instascribe** fixes these issues by restructuring the logs into a clean, behavioral dataset.

### Key Features:
- **Encoding Correction:** Fully resolves broken Unicode characters, ensuring emojis and non-Latin scripts (Farsi, Arabic, etc.) are readable.
- **Conversational Grouping:** Groups rapid-fire messages under a single header with "↳" pointers to help the LLM identify natural speech patterns.
- **LLM Contextualization:** 
    - **Self-Awareness:** Optionally tag your own messages as `[YOU]` to clarify roles for the AI.
    - **Time Gaps:** Injects markers for significant breaks (e.g., `--- TIME GAP: 14.5 hours ---`).
- **Hidden Context Recovery:** Explicitly labels **Unsent Messages**, **Geoblocked Content**, **Voice Notes**, and **Vanishing Media**.
- **Token Optimization:** Cleans tracking junk from URLs and offers an "Optimized" mode to strip marketing spam and hashtags from shared captions.
- **Interactive Batch Processing:** Point the script at your main `inbox` folder to list, select, and process multiple conversations at once.

## 📥 How to Export Your Data

To use Instascribe, you must request a **JSON** export from the **[Official Instagram Help Center](https://help.instagram.com/181231772500920)**.

### ⚠️ Crucial Requirements:
1.  **Information Type:** Select **Messages** only.
2.  **Format:** You must select **JSON** (HTML is not supported).
3.  **Media Quality:** Select **Low** to expedite the download.

## 🚀 Usage

1. Download and unzip your Instagram export.
2. Run the script:
   ```bash
   python3 instascribe.py
