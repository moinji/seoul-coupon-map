import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import numpy as np
from scipy.stats import entropy
import os
import re

sns.set_style("whitegrid")

def crawl_shops_sungdong(output_path='data/shops_sungdong.csv', max_pages=2):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    base_url = "https://www.sd.go.kr/main/webRecoveryCouponList.do?searchName=&searchEmdNm=&searchAddress=&searchBizRegNo=&key=5269&pageIndex={}"

    result_list = []

    try:
        for page in range(1, max_pages + 1):
            driver.get(base_url.format(page))
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.table tbody tr"))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "th")
                if len(cols) < 3:
                    continue
                store = {
                    "store_name": cols[0].text.strip(),
                    "dong": cols[1].text.strip(),
                    "address": cols[2].text.strip()
                }
                result_list.append(store)
            time.sleep(0.8)

    except Exception as e:
        st.error(f"[ERROR] 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()

    df = pd.DataFrame(result_list)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    return df


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



def run_sungdong_analysis():
    # 👁️ 데이터 흐름 설명 출력
    st.markdown("## 🔍 데이터 흐름 요약")
    st.info("데이터 흐름: 웹스크래핑 → CSV 저장 (shops_sungdong.csv) → CSV 불러오기 → 컬럼 생성 및 전처리 → 분석 및 시각화")

    # 파일 설명
    st.markdown("**사용 데이터 파일:** `shops_sungdong.csv` (성동구청 소비쿠폰 가맹점 목록)")

    st.sidebar.markdown("## 🎤 발표 설정")
    small_mode = st.sidebar.checkbox("발표 모드 (폰트/그래프 축소)", value=False)
    chart_height = st.sidebar.slider("📏 그래프 높이", 300, 600, 400)

    fontsize = 10 if small_mode else 12
    title_size = 12 if small_mode else 14
    figsize = (8, chart_height / 100)

    st.subheader("🏬 성동구청 소비쿠폰 가맹점 데이터 분석")

    csv_path = "data/shops_sungdong.csv"
    if not os.path.exists(csv_path):
        st.warning("CSV 파일이 없습니다. 먼저 데이터를 크롤링해주세요.")
        return

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

    with tabs[0]:
        st.markdown("### 자치구별 가맹점 비율")
        district_counts = df['district'].value_counts()
        fig, ax = plt.subplots(figsize=figsize)
        district_counts.plot.pie(autopct='%1.1f%%', startangle=90, ax=ax)
        ax.set_ylabel("")
        ax.set_title("자치구별 비율", fontsize=title_size)
        plt.tight_layout()
        st.pyplot(fig)
        st.markdown("### 분석 요약")
        st.write("- 성동구 외 타 자치구 데이터 포함 여부 확인 필요")

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