
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
import os

def crawl_shops_seongdong(output_path='./data/shops_seongdong.csv', max_pages=2):
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