import pandas as pd
import streamlit as st

# --- HTML Table Renderer ---
def render_html_table(df):
    df = df.fillna("")
    html = """
    <div style="height:600px; overflow-y:auto; overflow-x:auto;">
    <table style="border-collapse:collapse; width:100%; font-family:sans-serif;">
    <thead>
        <tr style='background-color:#f0f0f0;'>
            <th style='padding:8px;'>Name</th>
            <th style='padding:8px;'>Account</th>
            <th style='padding:8px;'>Moneys</th>
            <th style='padding:8px;'>Sheet</th>
        </tr>
    </thead>
    <tbody>
    """
    for _, row in df.iterrows():
        bg = "background-color:#fff8b3;" if row["Is Total"] else ""
        html += f"<tr style='{bg}'>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Name']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Account']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Moneys']}</td>"
        html += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{row['Sheet']}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# --- Streamlit Config ---
st.set_page_config(page_title="AJC Donations", layout="wide")
st.title("📊 AJC Donation Table Viewer")

uploaded_file = st.file_uploader("Upload the AJC Excel File", type=["xlsx"])

if uploaded_file:
    def load_all_sheets_as_dataframe(file):
        all_sheets = pd.read_excel(file, sheet_name=None, header=0)
        df_list = []
        for sheet_name, df in all_sheets.items():
            df = df.copy()
            df["Sheet"] = sheet_name
            df_list.append(df)
        return pd.concat(df_list, ignore_index=True)

    def clean_and_classify_donations(df):
        df["Name"] = df["Name"].ffill()
        df["Is Total"] = df["Name"].astype(str).str.strip().str.startswith("Total ")
        return df

    def build_combined_table(final, final_total):
        combined_rows = []
        sheets = sorted(final["Sheet"].unique())
        for sheet in sheets:
            donors = final[final["Sheet"] == sheet]["Name"].unique()
            for donor in donors:
                indiv = final[(final["Sheet"] == sheet) & (final["Name"] == donor)]
                total = final_total[(final_total["Sheet"] == sheet) & (final_total["Name"].str.contains(donor))]
                combined_rows.append(indiv)
                if not total.empty:
                    combined_rows.append(total)
        return pd.concat(combined_rows, ignore_index=True)

    # --- Load and prep data
    df = load_all_sheets_as_dataframe(uploaded_file)
    df = df.rename(columns={"Unnamed: 0": "Name"})
    df = clean_and_classify_donations(df)
    df["Moneys"] = df["Amount"].combine_first(df["Credit"])
    df["Account"] = df["Account"].str.replace(r"^\d+\s*∑\s*", "", regex=True)

    df_total = df[df["Is Total"]]
    df_non_total = df[~df["Is Total"]]

    final = df_non_total[["Name", "Account", "Moneys", "Sheet", "Is Total"]].dropna(subset=["Moneys"])
    final_total = df_total[["Name", "Moneys", "Sheet", "Is Total"]].dropna(subset=["Moneys"])
    full_table = build_combined_table(final, final_total)

    # --- Filter Controls
    st.subheader("🔍 Filter Table")
    search_name = st.text_input("Search Donor Name")

    sheet_values = sorted(full_table["Sheet"].dropna().unique())
    account_values = sorted(full_table["Account"].dropna().unique())

    col1, col2 = st.columns(2)
    with col1:
        sheet_filter = st.selectbox("Filter by Sheet", options=["All"] + sheet_values, index=0)
    with col2:
        account_filter = st.selectbox("Filter by Account", options=["All"] + account_values, index=0)

    # --- Apply Filters
    filtered_table = full_table.copy()
    if search_name:
        filtered_table = filtered_table[filtered_table["Name"].str.contains(search_name, case=False, na=False)]
    if sheet_filter != "All":
        filtered_table = filtered_table[filtered_table["Sheet"] == sheet_filter]
    if account_filter != "All":
        filtered_table = filtered_table[filtered_table["Account"] == account_filter]

    # --- Display
    html_table = render_html_table(filtered_table)
    st.markdown(html_table, unsafe_allow_html=True)

else:
    st.info("📂 Upload an Excel file to begin.")