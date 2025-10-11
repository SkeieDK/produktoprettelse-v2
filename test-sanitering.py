import streamlit as st
import pandas as pd
from csv_data_transformation.sanitering import CSVSanitering

st.title("Test af sanitering")

csv_path = st.text_input(
    "CSV-fil",
    value="C:\\Users\\anton\\OneDrive - Bunzl Continental Europe\\Power BI\\til_excel\\Produktoprettelse-AI-pluspack.csv",
    key="csv_path_input"
)
uploaded_excel = st.file_uploader(
    "Upload Excel resultat til sammenligning",
    type=["xlsx"],
    key="excel_upload"
)

df_trans = None

if csv_path:
    try:
        df = pd.read_csv(csv_path)
        sanitering = CSVSanitering(df)
        df_trans = sanitering.process()
        st.success("Sanitering gennemført!")
        st.dataframe(df_trans)
        # Gem til Excel
        df_trans.to_excel("saniteret_output.xlsx", index=False)
        st.info("Saniteret output gemt som saniteret_output.xlsx")
    except Exception as e:
        st.error(f"Fejl: {e}")

if df_trans is not None and uploaded_excel is not None:
    try:
        df_excel = pd.read_excel(uploaded_excel)
        st.subheader("Sammenligning med uploadet Excel-resultat")
        st.dataframe(df_excel)
        # Tilpas kolonner og index før sammenligning
        df_excel = df_excel.reindex(columns=df_trans.columns)
        df_excel.index = df_trans.index
        diff = df_trans.compare(df_excel, keep_shape=True, keep_equal=False)
        st.subheader("Forskelle mellem saniteret output og Excel-resultat")
        st.dataframe(diff)
    except Exception as e:
        st.error(f"Fejl ved sammenligning: {e}")