import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

# 동 매핑 함수 (인구 데이터의 행정동을 통합동으로 매핑)
DONG_MERGE_MAP = {
    "성수1가제1동": "성수동1가",
    "성수1가제2동": "성수동1가", 
    "성수2가제1동": "성수동2가",
    "성수2가제3동": "성수동2가",
    "왕십리도선동": "도선동",
    "왕십리제1동": "상왕십리",
    "왕십리제2동": "하왕십리",
    "금호1가동": "금호동1가",
    "금호2,3가동": "금호동2가", 
    "금호4가동": "금호동4가",
    "행당제1동": "행당동",
    "행당제2동": "행당동",
    "응봉동": "응봉동",
    "마장동": "마장동", 
    "사근동": "사근동",
    "옥수동": "옥수동",
    "송정동": "송정동",
    "용답동": "용답동"
}

SEONGDONG_DATA_PATH = "data/shops_seongdong.csv"
SEONGDONG_POPULATION_DATA_PATH = "data/seongdong_population.csv"

def load_and_merge_data():
    """데이터 로드 및 병합"""
    try:
        # 1. 데이터 로드
        shop_df = pd.read_csv(SEONGDONG_DATA_PATH)
        pop_df = pd.read_csv(SEONGDONG_POPULATION_DATA_PATH, encoding='utf-8-sig')
        
        # 컬럼명 정리
        pop_df.columns = pop_df.columns.str.strip()
        shop_df.columns = shop_df.columns.str.strip()
        
        # 2. 인구 데이터 동 매핑 및 집계
        pop_df["행정기관"] = pop_df["행정기관"].map(DONG_MERGE_MAP).fillna(pop_df["행정기관"])
        pop_df = pop_df.groupby("행정기관", as_index=False).sum(numeric_only=True)
        
        # 3. 가맹점 데이터 동 매핑
        if 'dong' in shop_df.columns:
            shop_df['dong'] = shop_df['dong'].map(DONG_MERGE_MAP).fillna(shop_df['dong'])
        
        # 4. 공통 동 확인
        shop_dongs = set(shop_df['dong'].unique()) if 'dong' in shop_df.columns else set()
        pop_dongs = set(pop_df['행정기관'].unique())
        common_dongs = shop_dongs.intersection(pop_dongs)
        
        # 5. 데이터 병합
        merged_df = pd.merge(shop_df, pop_df, left_on="dong", right_on="행정기관", how="left")
        
        return shop_df, pop_df, merged_df
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류: {e}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def plot_bar(data, x, y, title, xlabel, ylabel, color="skyblue", rotate=45, height=6, top_n=None):
    """막대그래프 그리기"""
    if data.empty:
        st.warning("표시할 데이터가 없습니다.")
        return
        
    plot_data = data.copy()
    if top_n:
        plot_data = plot_data.nlargest(top_n, y)
    
    fig, ax = plt.subplots(figsize=(12, height))
    bars = sns.barplot(data=plot_data, x=x, y=y, ax=ax, palette="viridis")
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    
    # 값 표시
    for bar in bars.patches:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}', ha='center', va='bottom', fontsize=10)
    
    plt.xticks(rotation=rotate)
    plt.tight_layout()
    st.pyplot(fig)

def create_folium_map(merged_df):
    """Folium 지도 생성"""
    # 성동구 중심 좌표
    center_lat, center_lon = 37.5636, 127.0369
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    
    # 동별 매장수와 인구밀도 계산
    dong_stats = merged_df.groupby('dong').agg({
        'store_name': 'count',
        '총인구수': 'first'
    }).reset_index()
    
    dong_stats['인구대비매장밀도'] = dong_stats['store_name'] / dong_stats['총인구수'] * 10000
    
    # 대략적인 동별 좌표
    dong_coords = {
        '성수동1가': [37.5445, 127.0557],
        '성수동2가': [37.5398, 127.0557], 
        '도선동': [37.5618, 127.0369],
        '상왕십리': [37.5645, 127.0336],
        '하왕십리': [37.5663, 127.0396],
        '금호동1가': [37.5486, 127.0196],
        '금호동2가': [37.5516, 127.0236],
        '금호동4가': [37.5546, 127.0276],
        '행당동': [37.5586, 127.0436],
        '응봉동': [37.5486, 127.0436],
        '마장동': [37.5636, 127.0469],
        '사근동': [37.5726, 127.0399],
        '옥수동': [37.5396, 127.0186],
        '송정동': [37.5756, 127.0529],
        '용답동': [37.5696, 127.0589]
    }
    
    # 마커 추가
    for _, row in dong_stats.iterrows():
        dong = row['dong']
        if dong in dong_coords and not pd.isna(row['총인구수']):
            coords = dong_coords[dong]
            popup_text = f"""
            <b>{dong}</b><br>
            매장수: {row['store_name']}개<br>
            총인구수: {row['총인구수']:,}명<br>
            인구 1만명당 매장수: {row['인구대비매장밀도']:.2f}개
            """
            
            folium.CircleMarker(
                location=coords,
                radius=min(row['인구대비매장밀도'] * 2, 20),
                popup=folium.Popup(popup_text, max_width=200),
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.6
            ).add_to(m)
    
    return m