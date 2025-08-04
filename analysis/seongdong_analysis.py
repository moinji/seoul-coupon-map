
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import numpy as np
from scipy.stats import entropy
import os
import re
from services.seongdong_scraper import crawl_shops_seongdong
import config

sns.set_style("whitegrid")

def extract_district(address):
    match = re.search(r"서울특별시 (.*?)구", address)
    return match.group(1) + "구" if match else "확인불가"

def near_subway_keywords(text):
    keywords = ["왕십리", "뚝섬", "성수", "서울숲", "한양대"]
    return any(k in text for k in keywords)

def is_franchise(store_name):
    franchise_keywords = ["이마트", "GS25", "CU", "세븐일레븐", "미니스톱", "투썸", "스타벅스"]
    return any(k in store_name.upper() for k in franchise_keywords)

def guess_category(text):
    category_keywords = {
        "약국": ["약국", "약"],
        "미용실": ["미용", "헤어", "뷰티", "살롱"],
        "편의점": ["CU", "GS25", "이마트24", "세븐일레븐", "미니스톱"],
        "카페": ["카페", "커피", "투썸", "스타벅스"],
        "식당": ["식당", "밥", "한식", "분식", "김밥", "고기", "정식"]
    }
    for category, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            return category
    return "기타"

def render_bar_chart(data, title, xlabel, ylabel="", color="skyblue", rotate=30, figsize=(10, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    data.plot(kind="bar", color=color, ax=ax)
    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    plt.xticks(rotation=rotate)
    plt.tight_layout()
    st.pyplot(fig)

def run_seongdong_analysis():
    st.markdown("## 🔍 데이터 흐름 요약")
    st.info("데이터 흐름: 웹스크래핑 → CSV 저장 (shops_seongdong.csv) → CSV 불러오기 → 컬럼 생성 및 전처리 → 분석 및 시각화")

    # 파일 설명
    st.markdown(f"**사용 데이터 파일:** `{config.SEONGDONG_DATA_PATH}` (성동구청 소비쿠폰 가맹점 목록)")

    st.sidebar.markdown("## 🎤 발표 설정")
    small_mode = st.sidebar.checkbox("발표 모드 (폰트/그래프 축소)", value=False)
    chart_height = st.sidebar.slider("📏 그래프 높이", 300, 600, 400)

    fontsize = 10 if small_mode else 12
    title_size = 12 if small_mode else 14
    figsize = (8, chart_height / 100)

    # 사용 데이터 파일 경로
    csv_path = config.SEONGDONG_DATA_PATH

    st.subheader("🏬 성동구청 소비쿠폰 가맹점 데이터 분석")

    # ✅ CSV 파일이 없으면 크롤링 버튼 제공
    if not os.path.exists(csv_path):
        st.warning("⚠️ CSV 파일이 없습니다. 데이터를 먼저 수집해주세요.")

        if st.button("🕷️ [크롤링 실행] 성동구청 소비쿠폰 가맹점 데이터 수집"):
            with st.spinner("크롤링 중..."):
                try:
                    df = crawl_shops_seongdong(output_path=csv_path, max_pages=20)
                    st.success(f"✅ 크롤링 완료! {len(df)}개 매장 수집됨")
                    st.rerun()  # 크롤링 후 자동 새로고침
                except Exception as e:
                    st.error(f"❌ 크롤링 중 오류 발생: {e}")
        return  # 파일 없으면 이후 분석 로직은 실행하지 않음

    # ✅ CSV가 있을 경우 분석 진행
    df = pd.read_csv(csv_path)

    # 데이터 구조 확인
    st.markdown("### 🔢 데이터 컬럼 구조")
    st.write(df.columns.tolist())

    # ---- 데이터 전처리 단계 ----
    st.markdown("## 🛠️ 데이터 전처리")

    st.write("- 주소에서 자치구 추출 → `district` 컬럼 생성")
    st.write("- 주소에 지하철 키워드 포함 여부 → `near_subway` 컬럼 생성")
    st.write("- 상호명이 프랜차이즈인지 여부 → `franchise` 컬럼 생성")
    st.write("- 상호명+주소 기반 업종 추정 → `category` 컬럼 생성")

    df['district'] = df['address'].apply(extract_district)
    df['near_subway'] = df['address'].apply(near_subway_keywords)
    df['franchise'] = df['store_name'].apply(is_franchise)
    df['category'] = (df['store_name'] + ' ' + df['address']).apply(guess_category)

    tabs = st.tabs(["📌 가맹점 분포", "🏪 업종 분석", "🏙️ 지역 분석", "🧠 요약 지표"])

        # -------------------- [NEW] tab0: 인구 + 가맹점 요약 --------------------
    tab0, tab1, tab2, tab3 = tabs

    with tab0:
        st.markdown("### 👥 성동구 인구 & 소비쿠폰 통계 요약")

        # 인구 데이터 불러오기
        pop_df = pd.read_csv("data/Seongdong_Population.csv")
        shop_df = pd.read_csv("data/shops_sungdong.csv")

        # 컬럼 이름 정제
        pop_df.columns = pop_df.columns.str.strip()

        # 메트릭 데이터 계산
        total_population = int(pop_df["총인구수"].sum())
        total_shops = len(shop_df)
        unique_dong_count = shop_df["dong"].nunique()
        elderly_population = int(pop_df["65세이상"].sum())
        elderly_ratio = elderly_population / total_population * 100
        child_ratio = pop_df["5세이하"].sum() / total_population * 100

        # 메트릭 레이아웃
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 총 인구수", f"{total_population:,}")
        col2.metric("🏪 총 가맹점 수", f"{total_shops:,}")
        col3.metric("🏘️ 행정동 수", f"{unique_dong_count:,}")
        col4.metric("🧓 고령자 비율", f"{elderly_ratio:.1f}%")

        col5, _ = st.columns([1, 3])
        col5.metric("🧒 5세 이하 유아 비율", f"{child_ratio:.1f}%")

        st.markdown("### 📊 연령별 인구 분포")

        # 시각화 대상 연령 컬럼 선택
        age_cols = ["5세이하", "18세이상", "65세이상"]
        age_df = pop_df[age_cols].sum().sort_values()

        # 폰트 설정
        plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

        # 수평 바 차트
        fig, ax = plt.subplots(figsize=(10, 5))
        age_df.plot(kind='barh', color='skyblue', ax=ax)
        ax.set_title("연령대별 인구수 분포", fontsize=13)
        ax.set_xlabel("인구 수", fontsize=11)
        ax.set_ylabel("연령대", fontsize=11)
        for i, v in enumerate(age_df.values):
            ax.text(v + 100, i, f"{int(v):,}", va='center', fontsize=10)
        plt.tight_layout()
        st.pyplot(fig)

        st.markdown("#### 📌 발표 TIP")
        st.info("성동구는 **고령 인구 비중(65세 이상)**이 약 **{:.1f}%**이며,\n5세 이하 인구도 {:.1f}%로 보육 수요를 고려한 정책 설계 필요".format(elderly_ratio, child_ratio))


    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 추정 업종 분포")
            category_counts = df['category'].value_counts()
            render_bar_chart(category_counts, "업종 분포", "업종", color="green", figsize=figsize)

        with col2:
            st.markdown("#### 프랜차이즈 vs 비프랜차이즈")
            franchise_counts = df['franchise'].value_counts().rename(index={True: "프랜차이즈", False: "비프랜차이즈"})
            render_bar_chart(franchise_counts, "프랜차이즈 여부", "구분", color="orange", figsize=figsize)

        st.markdown("### 분석 요약")
        st.write("- 편의점, 프랜차이즈 카페 등 대형 브랜드의 비중이 높은지 확인")

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 소재지(동)별 가맹점 수")
            dong_counts = df["dong"].value_counts().sort_values(ascending=True)
            fig6, ax6 = plt.subplots(figsize=figsize)
            dong_counts.plot(kind="barh", ax=ax6)
            ax6.set_title("소재지별 가맹점 수", fontsize=title_size)
            ax6.set_xlabel("가맹점 수", fontsize=fontsize)
            plt.tight_layout()
            st.pyplot(fig6)

        with col2:
            st.markdown("#### 동별 프랜차이즈 비율")
            dong_franchise = df.groupby('dong')['franchise'].value_counts(normalize=True).unstack().fillna(0)
            fig_dong, ax_dong = plt.subplots(figsize=(figsize[1], figsize[0]))
            dong_franchise.plot(kind='barh', stacked=True, ax=ax_dong, color=['gray', 'orange'])
            ax_dong.set_title("동별 프랜차이즈 비율", fontsize=title_size)
            ax_dong.set_xlabel("비율", fontsize=fontsize)
            plt.tight_layout()
            st.pyplot(fig_dong)

    with tabs[3]:
        st.markdown("#### 지하철역 인접 매장 비율")
        subway_counts = df['near_subway'].value_counts().rename(index={True: '역 근처', False: '기타'})
        render_bar_chart(subway_counts, "지하철역 인접 매장 여부", "구분", color=["skyblue", "lightgray"], figsize=figsize)

        st.markdown("#### 소재지 다양성 지수 (Shannon Entropy)")
        dong_counts = df["dong"].value_counts()
        p = dong_counts / dong_counts.sum()
        diversity_score = entropy(p)
        st.metric("🧠 소재지 다양성 (Entropy)", f"{diversity_score:.3f}")
