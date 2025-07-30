import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium # 이 부분이 중요합니다!
import os

# --- 1. 데이터 로드 및 전처리 함수 (기존 코드와 동일) ---
@st.cache_data
def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        st.error(f"오류: '{csv_path}' 파일을 찾을 수 없습니다. 'app.py'와 같은 폴더에 두거나 경로를 확인해주세요.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
        required_cols = ['store_name', 'address', 'industry_type', 'latitude', 'longitude']
        if not all(col in df.columns for col in required_cols):
            st.error(f"CSV 파일에 필수 컬럼({', '.join(required_cols)})이 모두 포함되어 있지 않습니다. CSV 파일을 확인해주세요.")
            return pd.DataFrame()

        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df.dropna(subset=['latitude', 'longitude'], inplace=True)

        if df.empty:
            st.warning("CSV 파일에 유효한 위도/경도 데이터가 없습니다. 파일을 확인해주세요.")
            return pd.DataFrame()

        df['district'] = df['address'].apply(
            lambda x: x.split(' ')[1] if len(x.split(' ')) > 1 else '기타'
        )
        return df
    except Exception as e:
        st.error(f"데이터 로드 및 전처리 중 오류 발생: {e}")
        return pd.DataFrame()

# --- Streamlit 앱 메인 (기존 코드와 동일) ---
st.set_page_config(layout="wide", page_title="내 주변 소비쿠폰 사용처", page_icon="💸")
st.title("💸 내 주변 소비쿠폰 사용처, 한눈에 보자!")
st.markdown("CSV 파일에서 로드된 서울시 소비쿠폰 사용 가능 매장을 지도로 쉽게 찾아보세요.")
st.markdown("---")

csv_file = 'shops.csv'
df_shops = load_and_preprocess_data(csv_file)

if df_shops.empty:
    st.stop()

st.sidebar.header("필터 설정")
all_industries = ['전체'] + sorted(df_shops['industry_type'].unique().tolist())
selected_industry = st.sidebar.selectbox("업종 선택", all_industries)

all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
selected_district = st.sidebar.selectbox("지역구 선택", all_districts)

st.sidebar.markdown("---")
st.sidebar.header("내 위치 설정")
if 'user_location' not in st.session_state:
    st.session_state.user_location = (37.5665, 126.9780)

col1, col2 = st.sidebar.columns(2)
user_lat = col1.number_input("내 위치 위도", value=st.session_state.user_location[0], format="%.4f")
user_lon = col2.number_input("내 위치 경도", value=st.session_state.user_location[1], format="%.4f")

if st.sidebar.button("내 위치로 지도 이동"):
    st.session_state.user_location = (user_lat, user_lon)
    st.sidebar.success("내 위치가 설정되었습니다!")

filtered_df = df_shops.copy()
if selected_industry != '전체':
    filtered_df = filtered_df[filtered_df['industry_type'] == selected_industry]
if selected_district != '전체':
    filtered_df = filtered_df[filtered_df['district'] == selected_district]

st.subheader(f"현재 지도에 표시된 매장 수: {len(filtered_df)}개")

# --- Folium 지도 생성 및 마커 추가 (이 부분을 수정합니다) ---

map_center_lat = st.session_state.user_location[0]
map_center_lon = st.session_state.user_location[1]

m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=12)
marker_cluster = MarkerCluster().add_to(m)

# '내 위치' 마커 추가 (이전과 동일)
folium.Marker(
    location=[st.session_state.user_location[0], st.session_state.user_location[1]],
    icon=folium.Icon(color='red', icon='info-sign'),
    popup="<b>내 현재 위치</b>"
).add_to(m)

# --- 업종별 아이콘 설정 정의 ---
# 'prefix'는 아이콘 폰트 라이브러리를 의미합니다. 'fa'는 Font Awesome을 의미해요.
# https://fontawesome.com/v4/icons/ 여기서 아이콘 이름을 확인할 수 있습니다.
# 'glyphicon'도 사용 가능합니다.
icon_mapping = {
    '마트': {'color': 'blue', 'icon': 'shopping-cart', 'prefix': 'fa'},
    '베이커리': {'color': 'orange', 'icon': 'cutlery', 'prefix': 'fa'}, # 식칼 모양
    '음식점': {'color': 'green', 'icon': 'spoon', 'prefix': 'fa'},    # 숟가락 모양
    '카페': {'color': 'purple', 'icon': 'coffee', 'prefix': 'fa'},
    '의류': {'color': 'pink', 'icon': 'shopping-bag', 'prefix': 'fa'}, # 혹은 t-shirt, female 등
    '시장': {'color': 'darkgreen', 'icon': 'shopping-basket', 'prefix': 'fa'},
    '서점': {'color': 'cadetblue', 'icon': 'book', 'prefix': 'fa'},
    # 여기에 더 많은 업종과 아이콘을 추가할 수 있습니다.
    # 매핑되지 않은 업종을 위한 기본값
    '기타': {'color': 'gray', 'icon': 'info-sign', 'prefix': 'glyphicon'}
}

# 필터링된 가맹점 마커 추가
for idx, row in filtered_df.iterrows():
    if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
        # 현재 가맹점의 업종을 가져옵니다.
        industry = row['industry_type']
        
        # icon_mapping에서 해당 업종에 맞는 아이콘 정보를 가져오거나, 없으면 '기타' 아이콘 정보를 사용합니다.
        icon_info = icon_mapping.get(industry, icon_mapping['기타'])

        # 팝업 내용 정의 (이전과 동일)
        popup_html = f"<b>매장명:</b> {row['store_name']}<br>" \
                     f"<b>업종:</b> {row['industry_type']}<br>" \
                     f"<b>주소:</b> {row['address']}"
        
        # Folium 마커 생성 시 icon 인자에 folium.Icon 객체를 전달합니다.
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(
                color=icon_info['color'],
                icon=icon_info['icon'],
                prefix=icon_info['prefix']
            )
        ).add_to(marker_cluster)

# --- Streamlit에 지도 표시 (기존 코드와 동일) ---
if not filtered_df.empty or st.session_state.user_location:
    st_folium(m, width=1200, height=600)
else:
    st.warning("선택하신 조건에 해당하는 매장이 없습니다. 필터를 조정해주세요.")

st.markdown("---")
st.caption("프로젝트 제안: SK Shieldus 4th Rookies Mini Project1")