import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import math
from datetime import datetime
import json
from utils.data_analysis import generate_analysis
from dotenv import load_dotenv

load_dotenv()
KAKAO_MAP_API_KEY = os.getenv("KAKAO_MAP_API_KEY")

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

# --- 카카오맵 생성 함수 ---
def create_kakao_map(filtered_df, user_lat, user_lon, max_distance, kakao_api_key):
    
    """카카오맵을 생성하는 함수"""

    # 마커 데이터를 JSON 형태로 준비
    markers_data = []
    for idx, row in filtered_df.iterrows():
        if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
            markers_data.append({
                'lat': float(row['latitude']),
                'lng': float(row['longitude']),
                'name': str(row['store_name']),
                'address': str(row['full_address']),
                'industry_code': str(row['industry_code']),
                'distance': float(row['distance'])
            })

    markers_json = json.dumps(markers_data, ensure_ascii=False)

    kakao_map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>카카오맵 - 민생회복 소비쿠폰 사용처</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap" rel="stylesheet">
    <style>
        html, body {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
        }}
        #map {{
            width: 100%;
            height: 600px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>

    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_api_key}&libraries=services,clusterer"></script>
    <script>
    var mapContainer = document.getElementById('map'),
        mapOption = {{
            center: new kakao.maps.LatLng({user_lat}, {user_lon}),
            level: 5
        }};

    var map = new kakao.maps.Map(mapContainer, mapOption);

    // 내 위치 기본값 (서울 시청으로 설정)
    var userPosition = new kakao.maps.LatLng({user_lat}, {user_lon});

    // 내 위치 마커 생성
    var userMarker = new kakao.maps.Marker({{
        position: userPosition,
        image: new kakao.maps.MarkerImage(
            'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
            new kakao.maps.Size(40, 40),
            new kakao.maps.Point(20, 40)
        )
    }});

    userMarker.setMap(map);

    // 반경 원 생성
    var circle = new kakao.maps.Circle({{
        center: userPosition,
        radius: {max_distance * 1000},
        strokeWeight: 3,
        strokeColor: '#1E90FF',
        strokeOpacity: 0.7,
        strokeStyle: 'solid',
        fillColor: '#1E90FF',
        fillOpacity: 0.15
    }});

    circle.setMap(map);

    // 실제 브라우저 GPS로 위치 업데이트
    navigator.geolocation.getCurrentPosition((position) => {{
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        userPosition = new kakao.maps.LatLng(lat, lon);
        map.setCenter(userPosition);
        userMarker.setPosition(userPosition);
        circle.setPosition(userPosition);
    }});

    // 내 위치 마커 클릭 시 실제 GPS 위치로 이동
    kakao.maps.event.addListener(userMarker, 'click', function() {{
        map.panTo(userPosition);
        map.setLevel(3, {{animate: {{duration: 500}}}});
    }});

    // 원(circle) 마우스 오버 효과
    kakao.maps.event.addListener(circle, 'mouseover', function() {{
        circle.setOptions({{fillOpacity: 0.3, strokeWeight: 4}});
    }});

    kakao.maps.event.addListener(circle, 'mouseout', function() {{
        circle.setOptions({{fillOpacity: 0.15, strokeWeight: 3}});
    }});

    // 마커 클러스터러 및 매장 마커 생성 (기존 코드 유지)
    var clusterer = new kakao.maps.MarkerClusterer({{
        map: map,
        averageCenter: true,
        minLevel: 5,
        disableClickZoom: false,
        styles: [{{
            width: '53px', height: '52px',
            background: 'url(//t1.daumcdn.net/localimg/localimages/07/mapapidoc/red1.png) no-repeat',
            color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '53px'
        }}, {{
            width: '56px', height: '55px', 
            background: 'url(//t1.daumcdn.net/localimg/localimages/07/mapapidoc/red2.png) no-repeat',
            color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '56px'
        }}, {{
            width: '66px', height: '65px',
            background: 'url(//t1.daumcdn.net/localimg/localimages/07/mapapidoc/red3.png) no-repeat',
            color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '66px'
        }}]
    }});

    var markersData = {{markers_json}};
    var markers = [];

    for (var i = 0; i < markersData.length; i++) {{
        var data = markersData[i];
        var marker = new kakao.maps.Marker({{
            position: new kakao.maps.LatLng(data.lat, data.lng)
        }});

        var infowindow = new kakao.maps.InfoWindow({{
            content: '<div style="padding:10px;min-width:200px;">' +
                     '<strong>' + data.name + '</strong><br/>' +
                     '<span style="font-size:12px;">업종: ' + data.industry_code + '</span><br/>' +
                     '<span style="font-size:12px;">주소: ' + data.address + '</span><br/>' +
                     '<span style="font-size:12px;">거리: ' + data.distance.toFixed(2) + 'km</span>' +
                     '</div>'
        }});

        (function(marker, infowindow) {{
            kakao.maps.event.addListener(marker, 'click', function() {{
                infowindow.open(map, marker);
            }});
        }})(marker, infowindow);

        markers.push(marker);
    }}

    clusterer.addMarkers(markers);

    if (markers.length > 0) {{
        var bounds = new kakao.maps.LatLngBounds();
        bounds.extend(userPosition);

        for (var i = 0; i < markersData.length; i++) {{
            bounds.extend(new kakao.maps.LatLng(markersData[i].lat, markersData[i].lng));
        }}

        map.setBounds(bounds);
    }}
</script>

</body>
</html>
"""

    return kakao_map_html

# --- Streamlit 앱 설정 ---
st.set_page_config(layout="wide", page_title="민생회복 소비쿠폰 사용처", page_icon="💸")

# --- 헤더 ---
st.title("💸 민생회복 소비쿠폰 사용처 찾기")
st.markdown("**쿠폰 사용 가능 매장을 카카오맵에서 한눈에 확인하고, 내 주변 가까운 곳을 찾아보세요!**")

# --- 데이터 로드 ---
csv_file = './data/result11.csv'
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

address_input = st.sidebar.text_input("주소로 위치 검색", placeholder="예: 서울특별시 중구 세종대로 110")
# 주소 → 좌표 변환 함수 추가
def address_to_coords(address, kakao_api_key):
    import requests

    url = f'https://dapi.kakao.com/v2/local/search/address.json?query={address}'
    headers = {'Authorization': f'KakaoAK {kakao_api_key}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200 and response.json()['documents']:
        result = response.json()['documents'][0]
        return float(result['y']), float(result['x'])
    else:
        st.sidebar.error("주소를 찾을 수 없습니다. 다시 입력해주세요.")
        return None

# 주소 입력 처리
if address_input and st.sidebar.button("주소로 위치 설정"):
    coords = address_to_coords(address_input, KAKAO_MAP_API_KEY)
    if coords:
        st.session_state.user_location = coords
        st.sidebar.success("위치가 설정되었습니다!")

# 사용자 위치 초기 설정
if 'user_location' not in st.session_state:
    st.session_state.user_location = (37.5665, 126.9780)  # 서울 시청 (기본 위치)

user_lat, user_lon = st.session_state.user_location

# 거리 슬라이더 추가 (반경 설정을 위한 필수 입력)
max_distance = st.sidebar.slider("내 위치에서 최대 거리 (km)", 0.5, 20.0, 5.0, 0.5)

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

# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3 = st.tabs(["🗺️ 카카오맵 보기", "📋 리스트 보기", "📊 통계"])

with tab1:
    st.subheader("📍 카카오맵으로 매장 위치 확인")

    if not filtered_df.empty:
        with st.spinner(f'🗺️ {len(filtered_df)}개 매장의 카카오맵을 생성하는 중...'):
            kakao_map_html = create_kakao_map(filtered_df, user_lat, user_lon, max_distance, KAKAO_MAP_API_KEY)

            components.html(kakao_map_html, height=650)

        st.info(f"✅ 총 {len(filtered_df)}개의 매장이 지도에 표시되었습니다. 마커를 클릭하면 상세 정보를 볼 수 있습니다.")
    else:
        st.warning("필터 조건에 맞는 매장이 없습니다. 검색 조건을 조정해 주세요.")

with tab2:
    st.subheader("📋 매장 목록")

    if not filtered_df.empty:
        # 표시할 컬럼 선택
        display_columns = ['store_name', 'industry_code', 'full_address', 'district', 'distance']
        display_df = filtered_df[display_columns].copy()
        display_df['distance'] = display_df['distance'].round(2)
        display_df.columns = ['매장명', '업종코드', '주소', '지역구', '거리(km)']

        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )

        # CSV 다운로드 버튼
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 파일로 다운로드",
            data=csv,
            file_name=f"민생회복_소비쿠폰_사용처_{len(filtered_df)}개.csv",
            mime="text/csv"
        )
    else:
        st.warning("표시할 매장이 없습니다.")

with tab3:
    st.subheader("📊 통계 정보")
    
    # data_analysis 모듈의 분석 함수 호출
    if not filtered_df.empty:
        # 전체 데이터를 사용한 종합 분석
        generate_analysis(df_shops)
    else:
        st.warning("조건에 맞는 매장이 없어서 기본 통계를 표시합니다.")
        # 필터링된 데이터가 없어도 전체 데이터로 분석
        if not df_shops.empty:
            generate_analysis(df_shops)
        else:
            st.error("데이터를 불러올 수 없습니다.")

# --- 푸터 ---
st.markdown("---")
st.markdown("🔧 **카카오맵 API**를 활용한 민생회복 소비쿠폰 사용처 검색 서비스")