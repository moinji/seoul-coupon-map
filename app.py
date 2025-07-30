import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import os
import math
from datetime import datetime

# --- 거리 계산 함수 추가 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """두 지점 간의 거리를 계산 (km)"""
    R = 6371  # 지구의 반지름 (km)
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

# --- 데이터 로드 및 전처리 함수 ---
@st.cache_data
def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        st.error(f"오류: '{csv_path}' 파일을 찾을 수 없습니다. 'app.py'와 같은 폴더에 두거나 경로를 확인해주세요.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
        required_cols = ['store_name', 'address', 'latitude', 'longitude']
        if not all(col in df.columns for col in required_cols):
            st.error(f"CSV 파일에 필수 컬럼({', '.join(required_cols)})이 모두 포함되어 있지 않습니다.")
            return pd.DataFrame()

        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df.dropna(subset=['latitude', 'longitude'], inplace=True)

        if df.empty:
            st.warning("CSV 파일에 유효한 위도/경도 데이터가 없습니다.")
            return pd.DataFrame()

        df['district'] = df['address'].apply(
            lambda x: x.split(' ')[1] if len(x.split(' ')) > 1 else '기타'
        )
        return df
    except Exception as e:
        st.error(f"데이터 로드 및 전처리 중 오류 발생: {e}")
        return pd.DataFrame()

# --- Streamlit 앱 설정 ---
st.set_page_config(layout="wide", page_title="민생회복 소비쿠폰 사용처", page_icon="💸")

# --- 헤더 ---
st.title("💸 민생회복 소비쿠폰 사용처 찾기")
st.markdown("**쿠폰 사용 가능 매장을 지도에서 한눈에 확인하고, 내 주변 가까운 곳을 찾아보세요!**")

# --- 데이터 로드 ---
csv_file = 'shops.csv'
df_shops = load_and_preprocess_data(csv_file)

if df_shops.empty:
    st.stop()

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")

# 지역구 필터
all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
selected_district = st.sidebar.selectbox("지역구 선택", all_districts)

# 거리 필터 추가
st.sidebar.markdown("---")
st.sidebar.header("📍 내 위치 설정")

if 'user_location' not in st.session_state:
    st.session_state.user_location = (37.5665, 126.9780)  # 서울 시청

col1, col2 = st.sidebar.columns(2)
user_lat = col1.number_input("위도", value=st.session_state.user_location[0], format="%.4f")
user_lon = col2.number_input("경도", value=st.session_state.user_location[1], format="%.4f")

# 거리 필터
max_distance = st.sidebar.slider("내 위치에서 최대 거리 (km)", 0.5, 20.0, 5.0, 0.5)

if st.sidebar.button("내 위치로 지도 이동"):
    st.session_state.user_location = (user_lat, user_lon)
    st.sidebar.success("위치가 설정되었습니다!")

# --- 데이터 필터링 ---
filtered_df = df_shops.copy()

# 지역구 필터
if selected_district != '전체':
    filtered_df = filtered_df[filtered_df['district'] == selected_district]

# 거리 필터 적용
if not filtered_df.empty:
    filtered_df['distance'] = filtered_df.apply(
        lambda row: calculate_distance(
            user_lat, user_lon, row['latitude'], row['longitude']
        ), axis=1
    )
    filtered_df = filtered_df[filtered_df['distance'] <= max_distance]
    filtered_df = filtered_df.sort_values('distance')

# --- 통계 정보 표시 ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("전체 매장 수", len(df_shops))
with col2:
    st.metric("필터된 매장 수", len(filtered_df))
with col3:
    if not filtered_df.empty:
        avg_distance = filtered_df['distance'].mean()
        st.metric("평균 거리", f"{avg_distance:.1f} km")
    else:
        st.metric("평균 거리", "0 km")
with col4:
    st.metric("지역구 수", len(filtered_df['district'].unique()) if not filtered_df.empty else 0)

# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3 = st.tabs(["🗺️ 지도 보기", "📋 리스트 보기", "📊 통계"])

with tab1:
    # --- 지도 생성 ---
    map_center_lat = st.session_state.user_location[0]
    map_center_lon = st.session_state.user_location[1]
    
    m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=13)
    
    # 지도 스타일 선택
    map_style = st.selectbox("지도 스타일", 
                           ["기본", "위성", "지형"], 
                           help="지도의 표시 스타일을 선택하세요")
    
    if map_style == "위성":
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
    elif map_style == "지형":
        folium.TileLayer('Stamen Terrain').add_to(m)
    
    # 내 위치 마커
    folium.Marker(
        location=[st.session_state.user_location[0], st.session_state.user_location[1]],
        icon=folium.Icon(color='red', icon='home'),
        popup="<b>🏠 내 위치</b>",
        tooltip="내 현재 위치"
    ).add_to(m)
    
    # 반경 표시
    folium.Circle(
        location=[st.session_state.user_location[0], st.session_state.user_location[1]],
        radius=max_distance * 1000,  # 미터 단위
        color='red',
        fill=False,
        opacity=0.3,
        popup=f"검색 반경: {max_distance}km"
    ).add_to(m)
    
    # 마커 클러스터
    marker_cluster = MarkerCluster().add_to(m)
    
    # 매장 마커 추가
    for idx, row in filtered_df.iterrows():
        if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
            popup_html = f"""
            <div style="width: 250px;">
                <h4>🏪 {row['store_name']}</h4>
                <p><b>주소:</b> {row['address']}</p>
                <p><b>거리:</b> {row['distance']:.2f} km</p>
            </div>
            """
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['store_name']} ({row['distance']:.2f}km)",
                icon=folium.Icon(
                    color='blue',
                    icon='shopping-cart',
                    prefix='fa'
                )
            ).add_to(marker_cluster)
    
    # 지도 표시
    if not filtered_df.empty or st.session_state.user_location:
        st_folium(m, width=1200, height=600)
    else:
        st.warning("선택하신 조건에 해당하는 매장이 없습니다. 필터를 조정해주세요.")

with tab2:
    st.subheader("📋 매장 리스트")
    
    if not filtered_df.empty:
        # 정렬 옵션
        sort_option = st.selectbox("정렬 기준", ["거리순", "이름순"])
        
        if sort_option == "거리순":
            display_df = filtered_df.sort_values('distance')
        else:
            display_df = filtered_df.sort_values('store_name')
        
        # 매장 카드 형태로 표시
        for idx, row in display_df.head(20).iterrows():  # 상위 20개만 표시
            with st.expander(f"🏪 {row['store_name']} ({row['distance']:.2f}km)"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**주소:** {row['address']}")
                    st.write(f"**지역구:** {row['district']}")
                with col2:
                    st.metric("거리", f"{row['distance']:.2f} km")
        
        if len(display_df) > 20:
            st.info(f"총 {len(display_df)}개 매장 중 상위 20개만 표시됩니다.")
    else:
        st.warning("조건에 맞는 매장이 없습니다.")

with tab3:
    st.subheader("📊 통계 정보")
    
    if not filtered_df.empty:
        # 지역구별 분포
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**지역구별 매장 수**")
            district_counts = filtered_df['district'].value_counts()
            st.bar_chart(district_counts)
        
        with col2:
            st.write("**매장 밀도 (km당 매장 수)**")
            # 거리 구간별 매장 밀도 계산
            distance_bins = pd.cut(filtered_df['distance'], bins=5)
            density_data = filtered_df.groupby(distance_bins).size()
            density_df = pd.DataFrame({
                '거리구간': [str(interval) for interval in density_data.index],
                '매장수': density_data.values
            }).set_index('거리구간')
            st.bar_chart(density_df)
        
        # 거리별 분포
        st.write("**거리별 매장 분포**")
        # 히스토그램을 위한 데이터 준비
        import numpy as np
        distances = filtered_df['distance']
        hist_data, bin_edges = np.histogram(distances, bins=10)
        
        # 구간별로 데이터프레임 생성
        hist_df = pd.DataFrame({
            '거리구간 (km)': [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(len(hist_data))],
            '매장수': hist_data
        }).set_index('거리구간 (km)')
        
        st.bar_chart(hist_df)
        
        # 상세 통계표
        st.write("**상세 통계**")
        stats_df = pd.DataFrame({
            '항목': ['최근거리', '최원거리', '평균거리', '중간거리'],
            '값 (km)': [
                filtered_df['distance'].min(),
                filtered_df['distance'].max(),
                filtered_df['distance'].mean(),
                filtered_df['distance'].median()
            ]
        })
        st.table(stats_df.round(2))
    else:
        st.warning("통계를 표시할 데이터가 없습니다.")

# --- 푸터 ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: gray;">
        💡 <b>사용 팁:</b> 지도에서 마커를 클릭하면 매장 정보를 확인할 수 있습니다.<br>
        📱 모바일에서도 편리하게 이용하세요!<br><br>
        <small>프로젝트 제안: SK Shieldus 4th Rookies Mini Project1</small>
    </div>
    """, 
    unsafe_allow_html=True
)