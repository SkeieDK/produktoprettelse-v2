import streamlit as st
import pandas as pd
import os
from csv_manager import CSVManager

st.set_page_config(page_title="CSV Data Dashboard", layout="wide")
st.title("CSV Data Dashboard")

uploaded_file = st.file_uploader("Upload en CSV-fil", type=["csv"])

st.header("Indlæs CSV via CSVManager (lokal sti)")
default_path = r"C:\Users\anton\OneDrive - Bunzl Continental Europe\Power BI\til_excel\Produktoprettelse-AI-pluspack.csv"
csv_path = st.text_input("CSV filsti", value=default_path)
csv_data = None
if os.path.exists(csv_path):
    csv_manager = CSVManager(csv_path)
    csv_data = csv_manager.load_csv()
    st.success(f"CSVManager: Indlæst {len(csv_data)} rækker.")
    if csv_data:
        st.dataframe(pd.DataFrame(csv_data), use_container_width=True)
else:
    st.warning("CSVManager: Filen blev ikke fundet.")

st.header("Indlæs CSV via upload (pandas)")
df = None
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.success(f"Pandas: Indlæst {len(df)} rækker og {len(df.columns)} kolonner.")
    st.dataframe(df, use_container_width=True)
    st.write("Kolonner:", list(df.columns))
    selected_cols = st.multiselect("Vælg kolonner til visning", options=list(df.columns), default=list(df.columns))
    st.dataframe(df[selected_cols], use_container_width=True)
else:
    st.info("Upload en CSV-fil for at se data.")

# Sammenlign data hvis begge er tilgængelige
if csv_data is not None and df is not None:
    st.header("Sammenligning af CSVManager og Pandas data")
    df_csvmanager = pd.DataFrame(csv_data)
    same_shape = df_csvmanager.shape == df.shape
    same_columns = list(df_csvmanager.columns) == list(df.columns)
    st.write(f"Samme antal rækker og kolonner: {'✅' if same_shape else '❌'}")
    st.write(f"Samme kolonnenavne: {'✅' if same_columns else '❌'}")
    # Vis forskelle hvis der er
    if not same_shape or not same_columns:
        st.write("CSVManager kolonner:", list(df_csvmanager.columns))
        st.write("Pandas kolonner:", list(df.columns))
    # Eksempel: Vis første 5 rækker fra begge
    st.subheader("Første 5 rækker fra CSVManager")
    st.dataframe(df_csvmanager.head(), use_container_width=True)
    st.subheader("Første 5 rækker fra Pandas")
    st.dataframe(df.head(), use_container_width=True)
