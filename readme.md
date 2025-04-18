# 📊 AJC Donation Table Viewer

This Streamlit app provides a powerful way to explore and analyze donation data collected in Excel spreadsheets across multiple years. It automatically processes and summarizes the data, offering interactive filtering, color-coded totals, and dynamic reporting.

---

## 🔧 What It Does

- 📂 **Upload** a multi-sheet Excel file (each sheet = donation year)
- 🧼 **Cleans** and combines data across sheets
- 📋 Displays a **detailed donation table** with:
  - Donor name, account, amount, and year
  - Filters for name, account, and sheet (year)
  - Yellow-highlighted total rows
  - Scrollable, fast-loading HTML table

- 📈 Shows a **pivot table summary** of total donations:
  - Columns = years (e.g. `24_25`, `23_24`)
  - Rows = donors
  - ✅ Green cells = donations ≥ threshold
  - ❌ Red cells = below threshold
  - Threshold adjustable by the user

---

## 🏗️ How It Works

- Uses `pandas` for data processing
- Caches both file loading and processing for ⚡ instant filters/searches
- Renders custom HTML tables for performance and styling
- Optional pivot table formatting with conditional coloring
