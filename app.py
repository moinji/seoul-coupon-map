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
        st.error(f"오류: '{csv_path}' 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    with st.spinner('대용량 데이터를 불러오고 전처리하는 중...'):
        try:
            encodings = ['utf-8', 'euc-kr', 'cp949', 'utf-8-sig']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding, skipinitialspace=True, quoting=1)
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                st.error("지원되는 인코딩으로 파일을 읽을 수 없습니다.")
                return pd.DataFrame()
            
            df.columns = df.columns.str.strip()
            
            required_cols = ['이름', '서울페이업종코드', '주소', '상세주소', '위도', '경도']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"CSV 파일에 다음 필수 컬럼이 없습니다: {', '.join(missing_cols)}")
                return pd.DataFrame()

            df = df.rename(columns={
                '이름': 'store_name',
                '서울페이업종코드': 'industry_code',
                '주소': 'address',
                '상세주소': 'detail_address',
                '위도': 'latitude',
                '경도': 'longitude'
            })
            
            df['full_address'] = df['address'].astype(str) + ' ' + df['detail_address'].fillna('').astype(str)
            df['full_address'] = df['full_address'].str.strip()

            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            df.dropna(subset=['latitude', 'longitude'], inplace=True)

            if df.empty:
                st.warning("CSV 파일에 유효한 위도/경도 데이터가 없습니다.")
                return pd.DataFrame()

            seoul_districts = [
                '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구',
                '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구',
                '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'
            ]
            
            def get_seoul_district_exact(address):
                if not isinstance(address, str):
                    return '기타'
                for district_name in seoul_districts:
                    if district_name in address:
                        return district_name
                return '기타'

            df['district'] = df['address'].apply(get_seoul_district_exact)
            
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
csv_file = 'result11.csv'
df_shops = load_and_preprocess_data(csv_file)

if df_shops.empty:
    st.stop()

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")

# 검색 기능 추가
search_query = st.sidebar.text_input("매장 이름 검색")

# 지역구 필터
all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
selected_district = st.sidebar.selectbox("지역구 선택", all_districts)

# 업종코드 필터
all_industry_codes = ['전체'] + sorted(df_shops['industry_code'].unique().tolist())
selected_industry_code = st.sidebar.selectbox("업종코드 선택", all_industry_codes)

# 거리 필터
st.sidebar.markdown("---")
st.sidebar.header("📍 내 위치 설정")

if 'user_location' not in st.session_state:
    st.session_state.user_location = (37.5665, 126.9780)  # 서울 시청

col1, col2 = st.sidebar.columns(2)
user_lat = col1.number_input("위도", value=st.session_state.user_location[0], format="%.4f")
user_lon = col2.number_input("경도", value=st.session_state.user_location[1], format="%.4f")

max_distance = st.sidebar.slider("내 위치에서 최대 거리 (km)", 0.5, 20.0, 1.0, 0.5)

if st.sidebar.button("내 위치로 지도 이동"):
    st.session_state.user_location = (user_lat, user_lon)
    st.sidebar.success("위치가 설정되었습니다!")

# --- 데이터 필터링 ---
filtered_df = df_shops.copy()

# 검색어 필터
if search_query:
    filtered_df = filtered_df[filtered_df['store_name'].str.contains(search_query, case=False, na=False)]

# 지역구 필터
if selected_district != '전체':
    filtered_df = filtered_df[filtered_df['district'] == selected_district]

# 업종코드 필터
if selected_industry_code != '전체':
    filtered_df = filtered_df[filtered_df['industry_code'] == selected_industry_code]

# 거리 계산 및 필터링
if not filtered_df.empty:
    filtered_df['distance'] = filtered_df.apply(
        lambda row: calculate_distance(user_lat, user_lon, row['latitude'], row['longitude']), 
        axis=1
    )
    filtered_df = filtered_df[filtered_df['distance'] <= max_distance]
    filtered_df = filtered_df.sort_values('distance').head(1000)  # 가장 가까운 1000개만 표시

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

# --- 업종별 아이콘 설정 ---
icon_mapping_by_code = {
    'A01': {'color': 'green', 'icon': 'cutlery', 'prefix': 'fa'},
    'A02': {'color': 'purple', 'icon': 'paint-brush', 'prefix': 'fa'},
    'A03': {'color': 'red', 'icon': 'heartbeat', 'prefix': 'fa'},
    'A04': {'color': 'pink', 'icon': 'shopping-bag', 'prefix': 'fa'},
    'A05': {'color': 'orange', 'icon': 'home', 'prefix': 'fa'},
    'A06': {'color': 'darkblue', 'icon': 'pencil', 'prefix': 'fa'},
    'A07': {'color': 'cadetblue', 'icon': 'language', 'prefix': 'fa'},
    'A08': {'color': 'darkgreen', 'icon': 'code', 'prefix': 'fa'},
    'A09': {'color': 'blue', 'icon': 'truck', 'prefix': 'fa'},
    'A10': {'color': 'lightred', 'icon': 'futbol-o', 'prefix': 'fa'},
    'A11': {'color': 'darkred', 'icon': 'car', 'prefix': 'fa'},
    'A12': {'color': 'black', 'icon': 'tv', 'prefix': 'fa'},
    'A13': {'color': 'lightgray', 'icon': 'wrench', 'prefix': 'fa'},
    'A14': {'color': 'darkpurple', 'icon': 'plane', 'prefix': 'fa'},
    'A15': {'color': 'beige', 'icon': 'print', 'prefix': 'fa'},
    '기타': {'color': 'gray', 'icon': 'info-circle', 'prefix': 'fa'}
}

# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3 = st.tabs(["🗺️ 지도 보기", "📋 리스트 보기", "📊 통계"])

with tab1:
    map_center_lat = st.session_state.user_location[0]
    map_center_lon = st.session_state.user_location[1]
    
    map_style = st.selectbox("지도 스타일", ["기본", "위성", "지형"])
    show_heatmap = st.checkbox("히트맵으로 매장 밀집도 보기")
    
    if not filtered_df.empty:
        loading_placeholder = st.empty()
        loading_placeholder.info(f"🗺️ {len(filtered_df)}개 매장의 지도를 생성하는 중...")
        
        # 기존 코드 수정
        m = folium.Map(
        location=[37.5665, 126.9780],
        zoom_start=13,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",  # OSM 타일 사용
        attr='OpenStreetMap',
        prefer_canvas=True  # 대용량 마커 시 성능 향상
        )
        
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
            radius=max_distance * 1000,
            color='red',
            fill=False,
            opacity=0.3,
            popup=f"검색 반경: {max_distance}km"
        ).add_to(m)

        if show_heatmap:
            heat_data = filtered_df[['latitude', 'longitude']].values.tolist()
            HeatMap(heat_data).add_to(m)

        # 마커 클러스터
        marker_cluster = MarkerCluster(
            name="매장 클러스터",
            options={
                'maxClusterRadius': 60,  # 클러스터링 반경 조정
                'disableClusteringAtZoom': 15  # 이 줌 레벨 이상에서는 클러스터링 해제
            }
        ).add_to(m)
        
        # 매장 마커 추가 (줌 레벨에 따라 동적으로 표시)
        for idx, row in filtered_df.iterrows():
            if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                industry_code = row['industry_code']
                icon_info = icon_mapping_by_code.get(industry_code, icon_mapping_by_code['기타'])

                popup_html = f"""
                <div style="width: 250px;">
                    <h4>🏪 {row['store_name']}</h4>
                    <p><b>업종코드:</b> {row['industry_code']}</p>
                    <p><b>주소:</b> {row['full_address']}</p>
                    <p><b>거리:</b> {row['distance']:.2f} km</p>
                </div>
                """
                
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{row['store_name']} ({row['distance']:.2f}km)",
                    icon=folium.Icon(
                        color=icon_info['color'],
                        icon=icon_info['icon'],
                        prefix=icon_info['prefix']
                    )
                ).add_to(marker_cluster)
        
        loading_placeholder.empty()
        st.success(f"🎉 {len(filtered_df)}개 매장이 표시된 지도가 준비되었습니다!")
        st_folium(m, width=1200, height=600, key="main_map")
    else:
        m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=13)
        folium.Marker(
            location=[st.session_state.user_location[0], st.session_state.user_location[1]],
            icon=folium.Icon(color='red', icon='home'),
            popup="<b>🏠 내 위치</b>",
            tooltip="내 현재 위치"
        ).add_to(m)
        
        st.info("선택된 조건에 해당하는 매장이 없습니다. 필터를 조정해주세요.")
        st_folium(m, width=1200, height=600, key="empty_map")

with tab2:
    st.subheader("📋 매장 리스트")
    
    if not filtered_df.empty:
        sort_option = st.selectbox("정렬 기준", ["거리순", "이름순"])
        
        if sort_option == "거리순":
            display_df = filtered_df.sort_values('distance')
        else:
            display_df = filtered_df.sort_values('store_name')
        
        for idx, row in display_df.head(1000).iterrows():  # 1000개만 표시
            with st.expander(f"🏪 {row['store_name']} ({row['distance']:.2f}km)"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**업종코드:** {row['industry_code']}")
                    st.write(f"**주소:** {row['full_address']}")
                    st.write(f"**지역구:** {row['district']}")
                with col2:
                    st.metric("거리", f"{row['distance']:.2f} km")
        
        if len(display_df) > 1000:
            st.info(f"총 {len(display_df)}개 매장 중 상위 1000개만 표시됩니다.")
    else:
        st.warning("조건에 맞는 매장이 없습니다.")

with tab3:
    st.subheader("📊 통계 정보")
    
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**지역구별 매장 수**")
            district_counts = filtered_df['district'].value_counts()
            st.bar_chart(district_counts)
        
        with col2:
            st.write("**업종코드별 매장 수**")
            industry_code_counts = filtered_df['industry_code'].value_counts()
            st.bar_chart(industry_code_counts)
        
        st.write("**매장 밀도 (거리 구간별)**")
        if len(filtered_df) > 1:
            distance_bins = pd.cut(filtered_df['distance'], bins=min(len(filtered_df), 10), include_lowest=True)
            density_data = filtered_df.groupby(distance_bins).size()
            density_df = pd.DataFrame({
                '거리구간': [str(interval) for interval in density_data.index],
                '매장수': density_data.values
            }).set_index('거리구간')
            st.bar_chart(density_df)
        
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