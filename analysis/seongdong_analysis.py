
import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from scipy.stats import entropy
import config
from services.seongdong_scraper import crawl_shops_seongdong

sns.set_style("whitegrid")

# 🔄 동 매핑 함수
DONG_MERGE_MAP = {
    "성수1가제1동": "성수동1가",
    "성수1가제2동": "성수동1가",
    "성수2가제1동": "성수동2가",
    "성수2가제3동": "성수동2가",
    "왕십리도선동": "왕십리도선동",
    "왕십리제1동": "왕십리제1동",
    "왕십리제2동": "왕십리제2동",
    "금호1가동": "금호1가동",
    "금호2,3가동": "금호2·3가동",
    "금호4가동": "금호4가동",
    "행당제1동": "행당동",
    "행당제2동": "행당동",
    "응봉동": "응봉동",
    "마장동": "마장동",
    "사근동": "사근동",
    "옥수동": "옥수동",
    "송정동": "송정동",
    "용답동": "용답동"
}

csv_path = "data/shops_seongdong.csv"
pop_path = "data/Seongdong_Population.csv"

def load_and_merge_data():
    shop_df = pd.read_csv(csv_path)
    pop_df = pd.read_csv(pop_path)

    pop_df["행정기관"] = pop_df["행정기관"].map(DONG_MERGE_MAP).fillna(pop_df["행정기관"])
    pop_df = pop_df.groupby("행정기관", as_index=False).sum(numeric_only=True)

    merged_df = pd.merge(shop_df, pop_df, left_on="dong", right_on="행정기관", how="left")
    return shop_df, pop_df, merged_df

def plot_bar(data, x, y, title, xlabel, ylabel, color="skyblue", rotate=45, height=400):
    fig, ax = plt.subplots(figsize=(10, height / 100))
    sns.barplot(data=data, x=x, y=y, ax=ax, color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=rotate)
    plt.tight_layout()
    st.pyplot(fig)

def run_seongdong_analysis():
    st.markdown("## 📊 성동구 소비쿠폰 + 인구 통합 분석")

    if not os.path.exists(csv_path):
        st.warning("⚠️ CSV 파일이 없습니다. 데이터를 먼저 수집해주세요.")
        if st.button("🕷️ [크롤링 실행] 성동구청 소비쿠폰 가맹점 데이터 수집"):
            with st.spinner("크롤링 중..."):
                try:
                    df = crawl_shops_seongdong(output_path=csv_path, max_pages=20)
                    st.success(f"✅ 크롤링 완료! {len(df)}개 매장 수집됨")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 크롤링 중 오류 발생: {e}")
        return

    df = pd.read_csv(csv_path)
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📁 데이터 개요", "👥 인구 통계", "🏪 가맹점 통계", "🔄 통합 분석", "📚 고급 분석"
    ])

    shop_df, pop_df, merged_df = load_and_merge_data()

    with tab0:
        st.markdown("### 🔍 데이터 컬럼 설명")
        st.write(shop_df.head(2))
        st.write(pop_df.head(2))

        st.markdown("### 🔗 동 매핑 방식")
        st.json(DONG_MERGE_MAP)

        st.markdown("### 🛠️ 전처리 흐름")
        st.markdown("""
        1. 크롤링 데이터 → shops_seongdong.csv 저장  
        2. 인구 데이터 → 행정기관 기준 병합  
        3. 성수1가제1동 + 성수1가제2동 → 성수동1가 식으로 매핑  
        """)

    with tab1:
        st.subheader("👨‍👩‍👧‍👦 동별 인구 통계")
        cols = ["총인구수", "남자인구수", "여자인구수", "5세이하인구수", "65세이상인구수"]
        for col in cols:
            plot_bar(pop_df.sort_values(col, ascending=False), "행정기관", col, f"{col} 순위", "동", "명")

        st.subheader("📈 전월대비 증감률 및 순위")
        plot_bar(pop_df.sort_values("전월대비", ascending=False), "행정기관", "전월대비", "전월대비 증감률", "동", "%")
        plot_bar(pop_df.sort_values("순위"), "행정기관", "순위", "총인구 순위", "동", "순위")

    with tab2:
        st.subheader("🏪 동별 가맹점 수")
        store_counts = shop_df["dong"].value_counts().reset_index()
        store_counts.columns = ["dong", "매장수"]
        plot_bar(store_counts, "dong", "매장수", "동별 소비쿠폰 가맹점 수", "동", "개수")

    with tab3:
        st.subheader("🔄 인구 + 매장 통합 지표")
        score_df = merged_df.groupby("dong").agg({
            "store_name": "count",
            "세대수": "mean"
        })
        score_df["생활편의도점수"] = score_df["store_name"] / score_df["세대수"] * 1000
        st.bar_chart(score_df["생활편의도점수"])

        merged_df["성비"] = merged_df["남자인구수"] / merged_df["여자인구수"]
        if "생활편의도점수" not in merged_df.columns:
            merged_df = merged_df.merge(score_df["생활편의도점수"], left_on="dong", right_index=True, how="left")
        st.scatter_chart(merged_df[["성비", "생활편의도점수"]].dropna())

    with tab4:
        st.subheader("📚 군집 분석 (KMeans)")
        features = ["총인구수", "남자인구수", "여자인구수", "5세이하인구수", "65세이상인구수", "세대수"]
        X = pop_df[features]
        X_scaled = StandardScaler().fit_transform(X)
        kmeans = KMeans(n_clusters=4, random_state=42)
        pop_df["군집"] = kmeans.fit_predict(X_scaled)

        fig, ax = plt.subplots(figsize=(10, 4))
        sns.countplot(x="군집", data=pop_df, palette="Set2", ax=ax)
        ax.set_title("군집별 동 수")
        st.pyplot(fig)

        st.markdown("### 군집별 평균값")
        st.dataframe(pop_df.groupby("군집")[features].mean().round(1))

        st.markdown("### 군집별 생활편의도 평균")
        merged_df = pd.merge(shop_df, pop_df[["행정기관", "군집"]], left_on="dong", right_on="행정기관", how="left")
        score_by_cluster = merged_df.groupby("군집").size() / merged_df.groupby("군집")["세대수"].sum() * 1000
        st.bar_chart(score_by_cluster.rename("생활편의도점수"))
