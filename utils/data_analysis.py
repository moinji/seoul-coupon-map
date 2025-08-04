
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import entropy

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def calculate_diversity_index(series):
    counts = series.value_counts()
    probs = counts / counts.sum()
    return entropy(probs, base=2)

def generate_analysis(df):

    df = df.rename(columns={
    'district': '자치구',
    'industry_code': '업종명',
    'store_name': '상호명',
    'full_address': '주소'
})


    if df.empty:
        st.warning("⚠️ 분석할 데이터가 없습니다.")
        return

    st.header("📊 서울시 소비쿠폰 가맹점 통계 분석")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("총 가맹점 수", f"{len(df):,}개")
    col2.metric("자치구 수", f"{df['자치구'].nunique()}개")
    col3.metric("업종 수", f"{df['업종명'].nunique()}개")

    st.subheader("🏷️ 업종별 가맹점 수")
    top_industries = df['업종명'].value_counts()
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    sns.barplot(y=top_industries.index, x=top_industries.values, ax=ax1)
    ax1.set_xlabel("가맹점 수")
    st.pyplot(fig1)

    st.subheader("🗺️ 자치구별 업종 분포 히트맵")
    heatmap_data = df[df['자치구'] != '기타'].pivot_table(index='자치구', columns='업종명', aggfunc='size', fill_value=0)
    fig2, ax2 = plt.subplots(figsize=(14, 10))
    sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlGnBu', ax=ax2)
    st.pyplot(fig2)

    st.subheader("🔍 자치구별 업종 다양성 지수 (엔트로피)")
    entropy_df = df[df['자치구'] != '기타'].groupby('자치구')['업종명'].apply(calculate_diversity_index).sort_values(ascending=False)
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    sns.barplot(x=entropy_df.values, y=entropy_df.index, ax=ax3, palette="viridis")
    ax3.set_xlabel("다양성 지수")
    st.pyplot(fig3)

    st.subheader("📊 자치구별 전체 가맹점 수")
    district_counts = df[df['자치구'] != '기타']['자치구'].value_counts()
    fig4, ax4 = plt.subplots(figsize=(12, 6))
    sns.barplot(x=district_counts.index, y=district_counts.values, ax=ax4)
    ax4.set_ylabel("가맹점 수")
    plt.xticks(rotation=45)
    st.pyplot(fig4)

    st.subheader("🍽️ 음식점/식음료업 집중도")
    df_food = df[df['업종명'] == '음식점/식음료업']
    food_ratio = df_food['자치구'].value_counts() / df['자치구'].value_counts() * 100
    food_ratio = food_ratio.dropna().sort_values(ascending=False)
    fig5, ax5 = plt.subplots(figsize=(10, 6))
    sns.barplot(x=food_ratio.index, y=food_ratio.values, ax=ax5)
    ax5.set_ylabel("음식점 비율 (%)")
    plt.xticks(rotation=45)
    st.pyplot(fig5)

    st.subheader("🏥 의료/복지 업종 비율")
    df['의료여부'] = df['업종명'].apply(lambda x: x == '보건/복지')
    medical_ratio = df[df['자치구'] != '기타'].groupby('자치구')['의료여부'].mean() * 100
    medical_ratio = medical_ratio.sort_values(ascending=False)
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    sns.barplot(x=medical_ratio.index, y=medical_ratio.values, ax=ax6)
    ax6.set_ylabel("의료/복지 업종 비율 (%)")
    plt.xticks(rotation=45)
    st.pyplot(fig6)

    st.success("✅ 분석이 완료되었습니다.")