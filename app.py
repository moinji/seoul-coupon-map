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
@st.cache_data # 캐싱을 사용하여 데이터 로드 및 전처리 속도 향상
def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        st.error(f"오류: '{csv_path}' 파일을 찾을 수 없습니다. 'app.py'와 같은 폴더에 두거나 경로를 확인해주세요.")
        return pd.DataFrame()

    # 데이터 로딩 스피너 추가
    with st.spinner('대용량 데이터를 불러오고 전처리하는 중... 잠시만 기다려주세요! (첫 로딩 시 다소 소요될 수 있습니다)'):
        try:
            df = pd.read_csv(csv_path)
            # 필수 컬럼 확인 및 에러 메시지 개선
            # industry_type 컬럼을 다시 추가했습니다.
            required_cols = ['store_name', 'address', 'industry_type', 'latitude', 'longitude']
            missing_cols = [col for col in df.columns if col not in required_cols] # 존재하지 않는 컬럼 찾는 방식으로 변경
            if missing_cols:
                st.error(f"CSV 파일에 다음 필수 컬럼이 없습니다: {', '.join(missing_cols)}. 파일을 확인해주세요.")
                return pd.DataFrame()

            # 위도/경도 데이터 타입 변환 및 유효하지 않은 행 제거
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            df.dropna(subset=['latitude', 'longitude'], inplace=True)

            if df.empty:
                st.warning("CSV 파일에 유효한 위도/경도 데이터가 없습니다. 모든 행이 제거되었을 수 있습니다. 파일을 확인해주세요.")
                return pd.DataFrame()

            # 'district' 컬럼 생성
            df['district'] = df['address'].apply(
                lambda x: x.split(' ')[1] if len(x.split(' ')) > 1 else '기타'
            )
            return df
        except Exception as e:
            st.error(f"데이터 로드 및 전처리 중 오류 발생: {e}. CSV 파일 형식 또는 내용이 올바른지 확인해주세요.")
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
    st.stop() # 데이터 로드 실패 시 앱 실행 중단

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")

# 지역구 필터
all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
selected_district = st.sidebar.selectbox("지역구 선택", all_districts)

# 업종 필터 (새로 추가)
all_industries = ['전체'] + sorted(df_shops['industry_type'].unique().tolist())
selected_industry = st.sidebar.selectbox("업종 선택", all_industries)


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

# 업종 필터 적용
if selected_industry != '전체':
    filtered_df = filtered_df[filtered_df['industry_type'] == selected_industry]


# 거리 필터 적용
if not filtered_df.empty:
    # 거리를 계산하기 전에 필터링된 데이터가 있는지 확인
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

# --- 업종별 아이콘 설정 정의 ---
# 'prefix'는 아이콘 폰트 라이브러리를 의미합니다. 'fa'는 Font Awesome을 의미해요.
# https://fontawesome.com/v4/icons/ 여기서 아이콘 이름을 확인할 수 있습니다.
# 'glyphicon'도 사용 가능합니다.
icon_mapping = {
    '음식점/식음료업': {'color': 'green', 'icon': 'spoon', 'prefix': 'fa'}, # 숟가락
    '예술교육': {'color': 'purple', 'icon': 'paint-brush', 'prefix': 'fa'}, # 페인트 브러쉬
    '보건/복지': {'color': 'red', 'icon': 'heartbeat', 'prefix': 'fa'}, # 심장박동
    '의류/잡화': {'color': 'pink', 'icon': 'shopping-bag', 'prefix': 'fa'}, # 쇼핑백
    '생활/리빙': {'color': 'orange', 'icon': 'home', 'prefix': 'fa'}, # 집
    '입시/교습학원': {'color': 'darkblue', 'icon': 'pencil', 'prefix': 'fa'}, # 연필
    '외국어/언어': {'color': 'cadetblue', 'icon': 'language', 'prefix': 'fa'}, # 언어
    '기술/기능교육': {'color': 'darkgreen', 'icon': 'code', 'prefix': 'fa'}, # 코드
    '식자재/유통': {'color': 'blue', 'icon': 'truck', 'prefix': 'fa'}, # 트럭 (유통)
    '문화/체육': {'color': 'lightred', 'icon': 'futbol-o', 'prefix': 'fa'}, # 축구공
    '자동차/주유': {'color': 'darkred', 'icon': 'car', 'prefix': 'fa'}, # 자동차
    '가전/통신': {'color': 'black', 'icon': 'tv', 'prefix': 'fa'}, # TV
    '건축/철물': {'color': 'lightgray', 'icon': 'wrench', 'prefix': 'fa'}, # 렌치
    '여행/숙박': {'color': 'darkpurple', 'icon': 'plane', 'prefix': 'fa'}, # 비행기
    '디자인/인쇄': {'color': 'beige', 'icon': 'paint-brush', 'prefix': 'fa'}, # 페인트 브러쉬 (예술교육과 동일)
    '기타': {'color': 'gray', 'icon': 'info-circle', 'prefix': 'fa'} # 정보
}
# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3 = st.tabs(["🗺️ 지도 보기", "📋 리스트 보기", "📊 통계"])

with tab1:
    # --- 지도 생성 ---
    map_center_lat = st.session_state.user_location[0]
    map_center_lon = st.session_state.user_location[1]
    
    # 지도 렌더링 스피너 추가
    with st.spinner('지도를 그리는 중... (매장이 많을 경우 잠시 기다려주세요)'):
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

        # 히트맵 옵션 추가
        show_heatmap = st.checkbox("히트맵으로 매장 밀집도 보기", help="매장 분포 밀집도를 색상으로 보여줍니다. (마커와 함께 표시 가능)")

        if show_heatmap and not filtered_df.empty:
            heat_data = filtered_df[['latitude', 'longitude']].values.tolist()
            # HeatMap 레이어는 마커보다 먼저 추가하면 시각적으로 더 자연스러울 수 있습니다.
            HeatMap(heat_data).add_to(m)

        # 마커 클러스터
        marker_cluster = MarkerCluster().add_to(m)
        
        # 매장 마커 추가
        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                    industry = row['industry_type'] # industry_type 컬럼 사용
                    icon_info = icon_mapping.get(industry, icon_mapping['기타'])

                    popup_html = f"""
                    <div style="width: 250px;">
                        <h4>🏪 {row['store_name']}</h4>
                        <p><b>업종:</b> {row['industry_type']}</p>
                        <p><b>주소:</b> {row['address']}</p>
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
        else:
            # 필터링 후 데이터가 없을 경우 지도에 텍스트 마커 추가
            folium.Marker(
                location=[map_center_lat, map_center_lon],
                icon=folium.DivIcon(html="<div style='font-size: 16px; color: gray; text-align: center;'>선택된 조건에 해당하는 매장이 없습니다.</div>"),
                popup="선택하신 조건에 해당하는 매장이 없습니다. 필터를 조정해주세요."
            ).add_to(m)

        # 지도 표시
        st_folium(m, width=1200, height=600)

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
                    st.write(f"**업종:** {row['industry_type']}") # 업종 정보 추가
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
            st.write("**매장 밀도 (거리 구간별)**") # 제목 변경
            # 거리 구간별 매장 밀도 계산
            # bins를 동적으로 설정하여 데이터가 없을 때 오류 방지
            if len(filtered_df) > 1: # 데이터가 1개 초과일 때만 bins 계산
                distance_bins = pd.cut(filtered_df['distance'], bins=min(len(filtered_df), 10), include_lowest=True)
            else: # 데이터가 0개 또는 1개일 경우 단일 bin으로 처리
                distance_bins = pd.cut(filtered_df['distance'], bins=1, include_lowest=True)

            density_data = filtered_df.groupby(distance_bins).size()
            density_df = pd.DataFrame({
                '거리구간': [str(interval) for interval in density_data.index],
                '매장수': density_data.values
            }).set_index('거리구간')
            st.bar_chart(density_df)
        
        # 거리별 분포 (히스토그램)
        st.write("**거리별 매장 분포**")
        import numpy as np
        distances = filtered_df['distance']
        # bins를 동적으로 설정하여 데이터가 없을 때 오류 방지
        if len(distances) > 0:
            hist_data, bin_edges = np.histogram(distances, bins=min(len(distances), 10))
            # 구간별로 데이터프레임 생성
            hist_df = pd.DataFrame({
                '거리구간 (km)': [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(len(hist_data))],
                '매장수': hist_data
            }).set_index('거리구간 (km)')
            st.bar_chart(hist_df)
        else:
            st.info("표시할 거리 분포 데이터가 없습니다.")


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