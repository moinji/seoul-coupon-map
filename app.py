import streamlit as st
import os
from dotenv import load_dotenv

import config
from services.kakao_api import geocode
from utils.helpers import calculate_distance, configure_matplotlib_fonts
from utils.data_loader import load_and_preprocess_data
from components.ui import create_sidebar, display_main_stats, create_tabs

def main():
    st.set_page_config(layout="wide", page_title="민생회복 소비쿠폰 사용처", page_icon="💸")
    configure_matplotlib_fonts()
    load_dotenv()
    KAKAO_MAP_API_KEY = os.getenv(config.KAKAO_MAP_API_KEY_ENV)

    st.title("💸 민생회복 소비쿠폰 사용처 찾기")
    st.markdown("**쿠폰 사용 가능 매장을 카카오맵에서 한눈에 확인하고, 내 주변 가까운 곳을 찾아보세요!**")

    st.header("📍 내 위치 설정")
    default_address = "성동구 왕십리로 58"
    addr = st.text_input("주소를 입력하세요",
                         value=default_address,
                         placeholder="예: 서울 종로구 세종대로 172",
                         key="address_input")
    if st.button("내 위치 찾기"):
        lat, lon = geocode(addr)
        if lat is None:
            st.error("좌표를 찾을 수 없습니다. 주소를 다시 확인하세요.")
        else:
            st.session_state["user_lat"] = lat
            st.session_state["user_lon"] = lon
            st.session_state["user_addr"] = addr
            st.success(f"📌 {addr} → ({lat:.5f}, {lon:.5f})")

    if "user_lat" not in st.session_state:
        st.session_state["user_lat"] = 37.5458
        st.session_state["user_lon"] = 127.0409
        st.session_state["user_addr"] = default_address

    user_lat = st.session_state.get("user_lat")
    user_lon = st.session_state.get("user_lon")
    current_addr = st.session_state.get("user_addr")

    df_shops = load_and_preprocess_data(config.MAIN_DATA_PATH)

    if df_shops.empty:
        st.stop()

    search_query, selected_district, selected_industry_code, max_distance = create_sidebar(df_shops)

    filtered_df = df_shops.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['store_name'].str.contains(search_query, case=False, na=False)]
    if selected_district != '전체':
        filtered_df = filtered_df[filtered_df['district'] == selected_district]
    if selected_industry_code != '전체':
        filtered_df = filtered_df[filtered_df['industry_code'] == selected_industry_code]

    if not filtered_df.empty:
        filtered_df['distance'] = filtered_df.apply(
            lambda row: calculate_distance(user_lat, user_lon, row['latitude'], row['longitude']),
            axis=1
        )
        filtered_df = filtered_df[filtered_df['distance'] <= max_distance]
        filtered_df = filtered_df.sort_values('distance').head(1000)

    display_main_stats(df_shops, filtered_df, current_addr)
    create_tabs(filtered_df, df_shops, user_lat, user_lon, max_distance, KAKAO_MAP_API_KEY)

    st.markdown("---")
    st.markdown("🔧 **카카오맵 API**를 활용한 민생회복 소비쿠폰 사용처 검색 서비스")

if __name__ == "__main__":
    main()