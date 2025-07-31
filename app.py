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

# --- 서울페이 업종코드를 업종명으로 변환하는 함수 (사용하지 않지만 참고용으로 유지) ---
# def get_industry_name(code):
#     """서울페이 업종코드를 업종명으로 변환"""
#     industry_mapping = {
#         'A01': '음식점/식음료업',
#         'A02': '예술교육',
#         'A03': '보건/복지',
#         'A04': '의류/잡화',
#         'A05': '생활/리빙',
#         'A06': '입시/교습학원',
#         'A07': '외국어/언어',
#         'A08': '기술/기능교육',
#         'A09': '식자재/유통',
#         'A10': '문화/체육',
#         'A11': '자동차/주유',
#         'A12': '가전/통신',
#         'A13': '건축/철물',
#         'A14': '여행/숙박',
#         'A15': '디자인/인쇄',
#         # 추가 코드들은 필요에 따라 확장
#     }
#     return industry_mapping.get(code, '기타')

# --- 데이터 로드 및 전처리 함수 ---
@st.cache_data # 캐싱을 사용하여 데이터 로드 및 전처리 속도 향상
def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        st.error(f"오류: '{csv_path}' 파일을 찾을 수 없습니다. 'app.py'와 같은 폴더에 두거나 경로를 확인해주세요.")
        return pd.DataFrame()

    # 데이터 로딩 스피너 추가
    with st.spinner('대용량 데이터를 불러오고 전처리하는 중... 잠시만 기다려주세요! (첫 로딩 시 다소 소요될 수 있습니다)'):
        try:
            # 다양한 인코딩으로 시도
            encodings = ['utf-8', 'euc-kr', 'cp949', 'utf-8-sig']
            df = None
            
            for encoding in encodings:
                try:
                    # CSV 파싱 옵션 추가
                    df = pd.read_csv(csv_path, encoding=encoding, 
                                     skipinitialspace=True,  # 앞쪽 공백 제거
                                     quoting=1)  # 따옴표 처리
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                st.error("지원되는 인코딩으로 파일을 읽을 수 없습니다. 파일 인코딩을 확인해주세요.")
                return pd.DataFrame()
            
            # 컬럼명 정리 (공백 제거)
            df.columns = df.columns.str.strip()
            
            # 필수 컬럼 확인 및 에러 메시지 개선
            required_cols = ['이름', '서울페이업종코드', '주소', '상세주소', '위도', '경도']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"CSV 파일에 다음 필수 컬럼이 없습니다: {', '.join(missing_cols)}. 파일을 확인해주세요.")
                return pd.DataFrame()

            # 컬럼명을 기존 코드에서 사용하던 이름으로 변경
            df = df.rename(columns={
                '이름': 'store_name',
                '서울페이업종코드': 'industry_code',
                '주소': 'address',
                '상세주소': 'detail_address',
                '위도': 'latitude',
                '경도': 'longitude',
                '변환상태': 'conversion_status'
            })
            
            # 전체 주소 생성 (주소 + 상세주소)
            df['full_address'] = df['address'].astype(str) + ' ' + df['detail_address'].fillna('').astype(str)
            df['full_address'] = df['full_address'].str.strip()  # 공백 제거

            # 위도/경도 데이터 타입 변환 및 유효하지 않은 행 제거
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            
            df.dropna(subset=['latitude', 'longitude'], inplace=True)

            if df.empty:
                st.warning("CSV 파일에 유효한 위도/경도 데이터가 없습니다. 모든 행이 제거되었을 수 있습니다. 파일을 확인해주세요.")
                return pd.DataFrame()

            # --- 'district' 컬럼 생성 (서울 25개 구 이름 기반으로 정확성 강화) ---
            seoul_districts = [
                '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구',
                '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구',
                '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'
            ]
            
            def get_seoul_district_exact(address):
                if not isinstance(address, str):
                    return '기타'
                for district_name in seoul_districts:
                    if district_name in address: # 주소 문자열에 해당 구 이름이 포함되어 있는지 확인
                        return district_name
                return '기타' # 서울 구가 아닌 경우 또는 찾지 못한 경우

            df['district'] = df['address'].apply(get_seoul_district_exact)
            
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
csv_file = 'result11.csv'
df_shops = load_and_preprocess_data(csv_file)

if df_shops.empty:
    st.stop() # 데이터 로드 실패 시 앱 실행 중단

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")

# 지역구 필터
all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
selected_district = st.sidebar.selectbox("지역구 선택", all_districts)

# 업종코드 필터 (업종명 대신 업종코드를 사용)
all_industry_codes = ['전체'] + sorted(df_shops['industry_code'].unique().tolist())
selected_industry_code = st.sidebar.selectbox("업종코드 선택", all_industry_codes)

# 변환상태 필터 제거

# 거리 필터 추가
st.sidebar.markdown("---")
st.sidebar.header("📍 내 위치 설정")

if 'user_location' not in st.session_state:
    st.session_state.user_location = (37.5665, 126.9780)  # 서울 시청

col1, col2 = st.sidebar.columns(2)
user_lat = col1.number_input("위도", value=st.session_state.user_location[0], format="%.4f")
user_lon = col2.number_input("경도", value=st.session_state.user_location[1], format="%.4f")

# 거리 필터
max_distance = st.sidebar.slider("내 위치에서 최대 거리 (km)", 0.5, 20.0, 1.0, 0.5)

if st.sidebar.button("내 위치로 지도 이동"):
    st.session_state.user_location = (user_lat, user_lon)
    st.sidebar.success("위치가 설정되었습니다!")

# --- 데이터 필터링 ---
filtered_df = df_shops.copy()

# 지역구 필터
if selected_district != '전체':
    filtered_df = filtered_df[filtered_df['district'] == selected_district]

# 업종코드 필터 적용
if selected_industry_code != '전체':
    filtered_df = filtered_df[filtered_df['industry_code'] == selected_industry_code]

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

# --- 업종별 아이콘 설정 정의 (업종코드 기준으로 변경) ---
# 실제 사용하실 업종코드에 맞춰 이 부분을 상세하게 정의해야 합니다.
icon_mapping_by_code = {
    'A01': {'color': 'green', 'icon': 'cutlery', 'prefix': 'fa'}, # 음식점
    'A02': {'color': 'purple', 'icon': 'paint-brush', 'prefix': 'fa'}, # 예술교육
    'A03': {'color': 'red', 'icon': 'heartbeat', 'prefix': 'fa'}, # 보건/복지
    'A04': {'color': 'pink', 'icon': 'shopping-bag', 'prefix': 'fa'}, # 의류/잡화
    'A05': {'color': 'orange', 'icon': 'home', 'prefix': 'fa'}, # 생활/리빙
    'A06': {'color': 'darkblue', 'icon': 'pencil', 'prefix': 'fa'}, # 입시/교습학원
    'A07': {'color': 'cadetblue', 'icon': 'language', 'prefix': 'fa'}, # 외국어/언어
    'A08': {'color': 'darkgreen', 'icon': 'code', 'prefix': 'fa'}, # 기술/기능교육
    'A09': {'color': 'blue', 'icon': 'truck', 'prefix': 'fa'}, # 식자재/유통
    'A10': {'color': 'lightred', 'icon': 'futbol-o', 'prefix': 'fa'}, # 문화/체육
    'A11': {'color': 'darkred', 'icon': 'car', 'prefix': 'fa'}, # 자동차/주유
    'A12': {'color': 'black', 'icon': 'tv', 'prefix': 'fa'}, # 가전/통신
    'A13': {'color': 'lightgray', 'icon': 'wrench', 'prefix': 'fa'}, # 건축/철물
    'A14': {'color': 'darkpurple', 'icon': 'plane', 'prefix': 'fa'}, # 여행/숙박
    'A15': {'color': 'beige', 'icon': 'print', 'prefix': 'fa'}, # 디자인/인쇄
    '기타': {'color': 'gray', 'icon': 'info-circle', 'prefix': 'fa'} # 기본값
}

# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3 = st.tabs(["🗺️ 지도 보기", "📋 리스트 보기", "📊 통계"])

with tab1:
    # --- 지도 생성 ---
    map_center_lat = st.session_state.user_location[0]
    map_center_lon = st.session_state.user_location[1]
    
    # 지도 스타일 선택을 스피너 밖으로 이동
    map_style = st.selectbox("지도 스타일", 
                             ["기본", "위성", "지형"], 
                             help="지도의 표시 스타일을 선택하세요")
    
    show_heatmap = st.checkbox("히트맵으로 매장 밀집도 보기", help="매장 분포 밀집도를 색상으로 보여줍니다. (마커와 함께 표시 가능)")
    
    # 더 안정적인 로딩 표시 방법
    if not filtered_df.empty:
        # 로딩 메시지 표시
        loading_placeholder = st.empty()
        loading_placeholder.info(f"🗺️ {len(filtered_df)}개 매장의 지도를 생성하는 중...")
        
        # 지도 생성
        m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=13)
        
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

        if show_heatmap:
            heat_data = filtered_df[['latitude', 'longitude']].values.tolist()
            HeatMap(heat_data).add_to(m)

        # 마커 클러스터
        marker_cluster = MarkerCluster().add_to(m)
        
        # 매장 마커 추가
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
                    <p><b>변환상태:</b> {row['conversion_status']}</p>
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
        
        # 로딩 메시지 제거
        loading_placeholder.empty()
        
        # 성공 메시지와 지도 표시
        st.success(f"🎉 {len(filtered_df)}개 매장이 표시된 지도가 준비되었습니다!")
        st_folium(m, width=1200, height=600, key="main_map")
    else:
        # 빈 지도 표시
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
                    st.write(f"**업종코드:** {row['industry_code']}")
                    st.write(f"**주소:** {row['full_address']}")
                    st.write(f"**지역구:** {row['district']}")
                    st.write(f"**변환상태:** {row['conversion_status']}")
                with col2:
                    st.metric("거리", f"{row['distance']:.2f} km")
        
        if len(display_df) > 20:
            st.info(f"총 {len(display_df)}개 매장 중 상위 20개만 표시됩니다.")
    else:
        st.warning("조건에 맞는 매장이 없습니다.")

with tab3:
    st.subheader("📊 통계 정보")
    
    if not filtered_df.empty:
        # 지역구별 분포와 업종코드별 분포
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**지역구별 매장 수**")
            district_counts = filtered_df['district'].value_counts()
            st.bar_chart(district_counts)
        
        with col2:
            st.write("**업종코드별 매장 수**")
            industry_code_counts = filtered_df['industry_code'].value_counts()
            st.bar_chart(industry_code_counts)
        
        # 변환상태별 분포
        col3, col4 = st.columns(2)
        
        with col3:
            st.write("**변환상태별 분포**")
            status_counts = filtered_df['conversion_status'].value_counts()
            st.bar_chart(status_counts)
        
        with col4:
            st.write("**매장 밀도 (거리 구간별)**")
            if len(filtered_df) > 1:
                distance_bins = pd.cut(filtered_df['distance'], bins=min(len(filtered_df), 10), include_lowest=True)
            else:
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
        if len(distances) > 0:
            hist_data, bin_edges = np.histogram(distances, bins=min(len(distances), 10))
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