import streamlit as st
import pandas as pd
from utils.map_renderer import draw_store_map

st.set_page_config(page_title="서울 소비쿠폰 사용처 맵", layout="wide")
st.title("💳 서울시 소비쿠폰 사용처 지도")

@st.cache_data
def load_data():
    df = pd.read_csv("data/stores_gangnam_geo.csv")
    return df

df = load_data()
df["자치구"] = "강남구"

st.sidebar.header("🔍 필터 설정")
gu_options = sorted(df["자치구"].dropna().unique())
biz_options = sorted(df["업종"].dropna().unique())

selected_gu = st.sidebar.selectbox("자치구 선택", ["전체"] + gu_options)
selected_biz = st.sidebar.selectbox("업종 선택", ["전체"] + biz_options)

filtered_df = df.copy()
if selected_gu != "전체":
    filtered_df = filtered_df[filtered_df["자치구"] == selected_gu]
if selected_biz != "전체":
    filtered_df = filtered_df[filtered_df["업종"] == selected_biz]

draw_store_map(filtered_df)

st.markdown("### 📋 가맹점 목록")
st.dataframe(filtered_df[["상호명", "업종", "도로명주소"]].reset_index(drop=True))
