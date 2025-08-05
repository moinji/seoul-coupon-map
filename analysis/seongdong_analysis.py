import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from streamlit_folium import st_folium
from services.seongdong_scraper import crawl_shops_seongdong
from utils.seongdong_analysis_utils import (
    DONG_MERGE_MAP,
    SEONGDONG_DATA_PATH,
    SEONGDONG_POPULATION_DATA_PATH,
    load_and_merge_data,
    plot_bar,
    create_folium_map
)
from components.seongdong_analysis_ui import (
    display_data_summary_tab,
    display_population_stats_tab,
    display_shop_stats_tab,
    display_integrated_analysis_tab,
    display_advanced_analysis_tab
)
from analysis.seongdong_analysis_core import (
    calculate_dong_analysis,
    perform_kmeans_clustering
)

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

def run_seongdong_analysis():
    
    # 데이터 파일 존재 확인 및 크롤링
    if not os.path.exists(SEONGDONG_DATA_PATH):
        st.warning("⚠️ CSV 파일이 없습니다. 데이터를 먼저 수집해주세요.")
        if st.button("🕷️ [크롤링 실행] 성동구청 소비쿠폰 가맹점 데이터 수집"):
            with st.spinner("크롤링 중..."):
                try:
                    df = crawl_shops_seongdong(output_path=SEONGDONG_DATA_PATH, max_pages=20)
                    st.success(f"✅ 크롤링 완료! {len(df)}개 매장 수집됨")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 크롤링 중 오류 발생: {e}")
        return
    
    # 데이터 로드
    shop_df, pop_df, merged_df = load_and_merge_data()
    
    if shop_df.empty or pop_df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        return

    # 통합 분석을 위한 dong_analysis 계산
    dong_analysis = calculate_dong_analysis(merged_df)

    # KMeans 군집 분석
    cluster_results = perform_kmeans_clustering(pop_df, shop_df, merged_df)

    # 탭 구성
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📁 데이터 요약", "👥 인구 통계", "🏪 가맹점 통계", "🔄 통합 분석", "📚 고급 분석"
    ])
    
    with tab0:
        display_data_summary_tab(shop_df, pop_df, merged_df)
    
    with tab1:
        display_population_stats_tab(pop_df)
    
    with tab2:
        display_shop_stats_tab(shop_df)
    
    with tab3:
        display_integrated_analysis_tab(shop_df, pop_df, merged_df, dong_analysis)
    
    with tab4:
        display_advanced_analysis_tab(shop_df, pop_df, merged_df, dong_analysis, cluster_results)

if __name__ == "__main__":
    run_seongdong_analysis()