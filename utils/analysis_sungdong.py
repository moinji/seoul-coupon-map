# utils/analysis_sungdong.py

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 분석/시각화 함수
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from wordcloud import WordCloud
import numpy as np
from scipy.stats import entropy
import os

def crawl_shops_sungdong(output_path='shops_sungdong.csv', max_pages=2):
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
            print(f"[INFO] 페이지 {page} 처리 중...")
            driver.get(base_url.format(page))

            # 테이블 로딩 대기
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
        print(f"[ERROR] 크롤링 중 에러 발생: {e}")

    finally:
        driver.quit()

    df = pd.DataFrame(result_list)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"[SUCCESS] 총 {len(df)}건 저장 완료: {output_path}")
    return df


def run_sungdong_analysis():
    import streamlit as st

    st.subheader("🏬 성동구청 소비쿠폰 가맹점 데이터 크롤링")
    max_pages = st.number_input("크롤링할 페이지 수", min_value=1, max_value=1681, value=2)

    if st.button("🕸️ 데이터 크롤링 실행"):
        with st.spinner("데이터 수집 중..."):
            df = crawl_shops_sungdong(max_pages=max_pages)
            st.success(f"✅ 총 {len(df)}건 수집 완료")
            st.dataframe(df)

            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 CSV 다운로드", data=csv, file_name="shops_sungdong.csv", mime="text/csv")


    st.subheader("📊 성동구 소비쿠폰 가맹점 분석")

    # 데이터 로드
    csv_path = "shops_sungdong.csv"
    if not os.path.exists(csv_path):
        st.warning("CSV 파일이 없습니다. 먼저 데이터를 크롤링해주세요.")
        return

    df = pd.read_csv(csv_path)

    st.markdown("### 📋 원본 데이터")
    st.dataframe(df.head(10))

    st.markdown("### 📈 소재지(동)별 가맹점 수")
    dong_counts = df["dong"].value_counts().sort_values(ascending=True)

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    dong_counts.plot(kind="barh", ax=ax1)
    ax1.set_title("소재지별 가맹점 수")
    ax1.set_xlabel("가맹점 수")
    st.pyplot(fig1)

    st.markdown("### 📌 소재지 다양성 지수 (Entropy)")
    p = dong_counts / dong_counts.sum()
    diversity_score = entropy(p)
    st.metric("🧠 소재지 다양성 (Shannon entropy)", f"{diversity_score:.3f}")