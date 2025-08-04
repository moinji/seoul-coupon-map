import streamlit as st
# pip install streamlit-bridge

# --- Streamlit 앱 설정 (가장 먼저 실행되어야 함) ---
st.set_page_config(layout="wide", page_title="민생회복 소비쿠폰 사용처", page_icon="💸")

import requests
import pandas as pd
import streamlit.components.v1 as components
import os
import math
from datetime import datetime
import json
import html  # HTML 이스케이프를 위해 추가
from utils.data_analysis import generate_analysis
from dotenv import load_dotenv
from urllib.parse import quote
# matplotlib 한글 폰트 설정
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import warnings
import platform
import altair as alt

def configure_matplotlib_fonts():
    """matplotlib 한글 폰트 설정"""
    try:
        # 폰트 경고 무시
        warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
        warnings.filterwarnings('ignore', message='findfont: Font family')

        # 사용 가능한 폰트 확인
        available_fonts = [f.name for f in fm.fontManager.ttflist]

        # 운영체제별 우선순위 폰트 리스트
        system = platform.system()
        if system == 'Windows':
            preferred_fonts = ['Malgun Gothic', 'Gulim', 'Dotum', 'Arial Unicode MS', 'DejaVu Sans']
        elif system == 'Darwin':  # macOS
            preferred_fonts = ['Arial Unicode MS', 'AppleGothic', 'Helvetica', 'DejaVu Sans']
        else:  # Linux
            preferred_fonts = ['DejaVu Sans', 'Liberation Sans', 'Arial', 'sans-serif']

        # 첫 번째로 사용 가능한 폰트 설정
        font_found = False
        for font in preferred_fonts:
            if font in available_fonts or font == 'sans-serif':
                plt.rcParams['font.family'] = font
                font_found = True
                break

        if not font_found:
            plt.rcParams['font.family'] = 'sans-serif'

        # 추가 설정
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 깨짐 방지
        plt.rcParams['font.size'] = 10              # 기본 폰트 크기
        plt.rcParams['figure.figsize'] = (10, 6)    # 기본 그림 크기

    except Exception as e:
        # 오류 발생 시 최소한의 설정
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        print(f"폰트 설정 중 오류 발생: {e}")

# 폰트 설정 실행
configure_matplotlib_fonts()

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

# --- 수정된 카카오맵 생성 함수 ---
def create_kakao_map(filtered_df, user_lat, user_lon, max_distance, kakao_api_key):
    """수정된 카카오맵을 생성하는 함수 - kakao.maps.load() 사용"""

    if not kakao_api_key:
        return "<div style='padding:20px; text-align:center; color:red;'>❌ API 키가 없어서 지도를 표시할 수 없습니다.</div>"

    # 마커 데이터를 JSON 형태로 준비 (안전하게 처리)
    markers_data = []
    for idx, row in filtered_df.iterrows():
        try:
            if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                # HTML 이스케이프 처리로 XSS 방지
                markers_data.append({
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'name': html.escape(str(row['store_name'])[:50]),
                    'address': html.escape(str(row['full_address'])[:100]),
                    'industry_code': html.escape(str(row['industry_code'])),
                    'distance': round(float(row['distance']), 2)
                })
        except Exception as e:
            # 개별 마커 오류는 무시하고 계속 진행
            continue

    if not markers_data:
        return "<div style='padding:20px; text-align:center;'>📍 표시할 매장이 없습니다.</div>"

    # JSON 안전하게 생성
    try:
        markers_json = json.dumps(markers_data, ensure_ascii=False)
    except Exception as e:
        st.error(f"JSON 데이터 생성 오류: {e}")
        return "<div style='padding:20px; text-align:center; color:red;'>❌ 데이터 처리 오류</div>"



    kakao_map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>카카오맵 - 민생회복 소비쿠폰 사용처</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            text-align: center;
            font-family: Arial, sans-serif;
        }}
        .error {{
            color: red;
            padding: 20px;
            text-align: center;
            font-family: Arial, sans-serif;
        }}
    </style>
</head>
<body>
    <div id="loading">
        🗺️ 지도 로딩 중...<br>
        <small>잠시만 기다려주세요</small>
    </div>
    <div id="map"></div>

    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_api_key}&libraries=services,clusterer&autoload=false"></script>
    <script>
        console.log('스크립트 로딩 시작');

        function hideLoading() {{
            const loading = document.getElementById('loading');
            if (loading) loading.style.display = 'none';
        }}

        function showError(message) {{
            hideLoading();
            document.getElementById('map').innerHTML = '<div class="error">❌ ' + message + '</div>';
            console.error(message);
        }}

        // 전역 오류 처리
        window.onerror = function(msg, url, line, col, error) {{
            showError('JavaScript 오류: ' + msg);
            return true;
        }};

        // 🔑 핵심: kakao.maps.load() 함수 사용!
        try {{
            if (typeof kakao === 'undefined') {{
                throw new Error('카카오맵 스크립트가 로드되지 않았습니다. API 키를 확인해주세요.');
            }}

            console.log('카카오 객체 확인 완료');


            // 여기가 핵심! kakao.maps.load() 콜백 안에서 모든 지도 관련 코드 실행
            kakao.maps.load(function() {{
                console.log('카카오맵 라이브러리 로딩 완료');

                try {{
                    hideLoading();

                    // 지도 생성
                    var mapContainer = document.getElementById('map');
                    var mapOption = {{
                        center: new kakao.maps.LatLng({user_lat}, {user_lon}),
                        level: 5
                    }};
                    var map = new kakao.maps.Map(mapContainer, mapOption);

                    console.log('지도 생성 완료');

                    // 내 위치 마커
                    var userPosition = new kakao.maps.LatLng({user_lat}, {user_lon});
                    var userMarker = new kakao.maps.Marker({{
                        position: userPosition,
                        image: new kakao.maps.MarkerImage(
                            'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
                            new kakao.maps.Size(50, 50),
                            new kakao.maps.Point(25, 50)
                        )
                    }});
                    userMarker.setMap(map);

                    // 내 위치 정보창
                    var userInfowindow = new kakao.maps.InfoWindow({{
                        content: '<div style="padding:5px;font-size:12px;">🏠 내 위치</div>'
                    }});
                    userInfowindow.open(map, userMarker);

                    // 검색 반경 원
                    var circle = new kakao.maps.Circle({{
                        center: userPosition,
                        radius: {max_distance * 1000},
                        strokeWeight: 2,
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.8,
                        strokeStyle: 'dashed',
                        fillColor: '#FF0000',
                        fillOpacity: 0.1
                    }});
                    circle.setMap(map);

                    // 마커 클러스터러 생성 (조건부)
                    var clusterer = null;
                    var markersData = {markers_json};

                    console.log('매장 데이터 수:', markersData.length);

                    if (typeof kakao.maps.MarkerClusterer !== 'undefined' && markersData.length > 50) {{
                        clusterer = new kakao.maps.MarkerClusterer({{
                            map: map,
                            averageCenter: true,
                            minLevel: 4,
                            disableClickZoom: false,
                            styles: [{{
                                width: '53px', height: '52px',
                                background: 'rgba(255, 0, 0, 0.4)',
                                borderRadius: "50%",
                                color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '53px'
                            }}, {{
                                width: '56px', height: '55px',
                                background: 'rgba(255, 0, 0, 0.4)',
                                borderRadius: "50%",
                                color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '56px'
                            }}, {{
                                width: '66px', height: '65px',
                                background: 'rgba(255, 0, 0, 0.4)',
                                borderRadius: "50%",
                                color: '#fff', textAlign: 'center', fontWeight: 'bold', lineHeight: '66px'
                            }}]
                        }});
                        console.log('마커 클러스터러 생성 완료');
                    }} else {{
                        console.log('마커 클러스터러 사용하지 않음 (매장 수: ' + markersData.length + ')');
                    }}

                    // 매장 마커들 생성
                    var markers = [];
                    for (var i = 0; i < markersData.length; i++) {{
                        try {{
                            var data = markersData[i];
                            var marker = new kakao.maps.Marker({{
                                position: new kakao.maps.LatLng(data.lat, data.lng)
                            }});

                            // 인포윈도우 생성
                            var infowindow = new kakao.maps.InfoWindow({{
                                content: '<div style="padding:10px;min-width:200px;">' +
                                            '<strong>' + data.name + '</strong><br/>' +
                                            '<span style="font-size:12px;">업종: ' + data.industry_code + '</span><br/>' +
                                            '<span style="font-size:12px;">주소: ' + data.address + '</span><br/>' +
                                            '<span style="font-size:12px;">거리: ' + data.distance.toFixed(2) + 'km</span>' +
                                            '</div>',
                                removable : true
                            }});

                            // 마커 클릭 이벤트
                            (function(marker, infowindow) {{
                                kakao.maps.event.addListener(marker, 'click', function() {{
                                    console.log(infowindow);
                                    infowindow.open(map, marker);
                                }});
                            }})(marker, infowindow);

                            markers.push(marker);
                        }} catch (e) {{
                            console.error('마커 생성 오류:', e);
                        }}
                    }}

                    // 마커들을 지도에 추가
                    if (clusterer) {{
                        clusterer.addMarkers(markers);
                        console.log('클러스터러에 마커 추가 완료');
                    }} else {{
                        // 클러스터러가 없으면 직접 추가
                        for (var i = 0; i < markers.length; i++) {{
                            markers[i].setMap(map);
                        }}
                        console.log('지도에 마커 직접 추가 완료');
                    }}

                    // 지도 범위 조정
                    if (markers.length > 0) {{
                        var bounds = new kakao.maps.LatLngBounds();
                        bounds.extend(userPosition);

                        for (var i = 0; i < markersData.length; i++) {{
                            bounds.extend(new kakao.maps.LatLng(markersData[i].lat, markersData[i].lng));
                        }}

                        map.setBounds(bounds);
                        console.log('지도 범위 조정 완료');
                    }}

                    console.log('🎉 모든 지도 초기화 완료!');

                    // 지도 이동/확대/축소 시 경계 좌표를 Python으로 전송
                    kakao.maps.event.addListener(map, 'bounds_changed', function() {{
                        var bounds = map.getBounds();
                        var swLatlng = bounds.getSouthWest();
                        var neLatlng = bounds.getNorthEast();

                        var boundsData = {{
                            topLeftLat: neLatlng.getLat(),
                            topLeftLon: swLatlng.getLng(),
                            bottomRightLat: swLatlng.getLat(),
                            bottomRightLon: neLatlng.getLng()
                        }};

                        // Python으로 데이터 전송 필요

                    }});

                }} catch (error) {{
                    console.error('지도 생성 오류:', error);
                    showError('지도 생성 중 오류가 발생했습니다: ' + error.message);
                }}
            }});
        }} catch (error) {{
            console.error('카카오맵 초기화 오류:', error);
            showError('카카오맵을 초기화할 수 없습니다: ' + error.message);
        }}
    </script>
</body>
</html>
"""

    return kakao_map_html


# 주소검색------------------------------------------------fix:주소검색
@st.cache_data(show_spinner=False)
def geocode(address: str):
    """개선된 한글 주소 → (lat, lon) 튜플 반환"""
    if not address:
        return None, None

    REST_KEY = os.getenv("KAKAO_REST_API_KEY")
    if not REST_KEY:
        st.error("❌ KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다")
        return None, None

    # 여러 주소 형식으로 시도 (성공률 향상)
    address_variations = [
        address,
        address.replace("역", ""),  # "신림역" → "신림"
        f"서울 관악구 {address}" if "서울" not in address else address,
        f"서울특별시 관악구 {address}" if "서울특별시" not in address else address,
        f"서울특별시 관악구 신림동" if "신림" in address else address
    ]

    # 중복 제거
    address_variations = list(dict.fromkeys(address_variations))

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {REST_KEY}"}

    for i, test_address in enumerate(address_variations, 1):
        try:
            # 핵심: 올바른 URL 인코딩
            params = {"query": test_address}
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("documents"):
                    y = float(data["documents"][0]["y"])  # 위도
                    x = float(data["documents"][0]["x"])  # 경도
                    address_name = data["documents"][0].get("address_name", "")

                    st.info(f"✅ 주소 찾기 성공 ({i}번째 시도): {address_name}")
                    return y, x

            elif response.status_code == 401:
                st.error("❌ 401 오류: REST API 키가 잘못되었습니다")
                st.error("💡 해결방법: .env 파일의 KAKAO_REST_API_KEY 확인")
                break
            elif response.status_code == 403:
                st.error("❌ 403 오류: API 사용 권한이 없습니다")
                st.error("💡 해결방법: 카카오 개발자센터에서 도메인/IP 설정 확인")
                break
            else:
                st.warning(f"시도 {i}: '{test_address}' - HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            st.warning(f"시도 {i}: '{test_address}' - 네트워크 오류: {e}")
            continue

    st.error("❌ 모든 주소 형식으로 시도했지만 좌표를 찾을 수 없습니다")
    st.info("💡 다음 주소 형식들을 시도해보세요:")
    st.info("   • 서울특별시 관악구 신림동")
    st.info("   • 서울 관악구 신림로 378")
    st.info("   • 관악구 신림동")

    return None, None

# --- 환경 변수 로드 ---
st.title("💸 민생회복 소비쿠폰 사용처 찾기")
st.markdown("**쿠폰 사용 가능 매장을 카카오맵에서 한눈에 확인하고, 내 주변 가까운 곳을 찾아보세요!**")

# --- 사용자 위치 설정 UI (가장 위로 이동) ---
st.header("📍 내 위치 설정")
# 시연을 위해 기본값을 미리 설정
default_address = "성동구 왕십리로 58"
addr = st.text_input("주소를 입력하세요",
                     value=default_address,  # 미리 입력된 주소
                     placeholder="예: 서울 종로구 세종대로 172",
                     key="address_input")
if st.button("내 위치 찾기"):
    lat, lon = geocode(addr)
    if lat is None:
        st.error("좌표를 찾을 수 없습니다. 주소를 다시 확인하세요.")
    else:
        st.session_state["user_lat"] = lat
        st.session_state["user_lon"] = lon
        st.session_state["user_addr"] = addr # 주소 저장
        st.success(f"📌 {addr} → ({lat:.5f}, {lon:.5f})")

# 세션 상태에 저장된 위치가 없으면 기본값 사용
if "user_lat" not in st.session_state:
    st.session_state["user_lat"] = 37.5458  # 성동구청 위도
    st.session_state["user_lon"] = 127.0409  # 성동구청 경도
    st.session_state["user_addr"] = default_address

user_lat = st.session_state.get("user_lat")
user_lon = st.session_state.get("user_lon")
current_addr = st.session_state.get("user_addr")

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
st.markdown("---")
st.subheader("💡 현재 위치:")
st.info(f"**{current_addr}**")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # 포맷 개선
    st.metric("전체 매장 수", f"{len(df_shops):,}")

with col2:
    # 포맷 개선
    st.metric("필터된 매장 수", f"{len(filtered_df):,}")

with col3:
    if not filtered_df.empty:
        avg_distance = filtered_df['distance'].mean()
        st.metric("평균 거리", f"{avg_distance:.1f} km")
    else:
        st.metric("평균 거리", "0 km")

with col4:
    st.metric("지역구 수", len(filtered_df['district'].unique()) if not filtered_df.empty else 0)

# --- 탭으로 구분된 뷰 ---
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 카카오맵 보기", "📋 리스트 보기", "📊 통계", "📈 성동구청 크롤링 분석"])

with tab1:
    st.subheader("📍 카카오맵으로 매장 위치 확인")

    if not filtered_df.empty:
        # API 키 재확인
        if not KAKAO_MAP_API_KEY:
            st.error("🔑 카카오 맵 API 키가 없어서 지도를 표시할 수 없습니다.")
            st.info("💡 해결 방법:")
            st.code("""
1. .env 파일 생성 또는 확인
2. 다음 내용 추가: KAKAO_MAP_API_KEY=your_actual_api_key
3. 카카오 개발자 센터에서 API 키 발급: https://developers.kakao.com/
            """)
        else:
            with st.spinner(f'🗺️ {len(filtered_df)}개 매장의 카카오맵을 생성하는 중...'):
                try:
                    # 🔑 핵심: 수정된 함수 사용
                    kakao_map_html = create_kakao_map(filtered_df, user_lat, user_lon, max_distance, KAKAO_MAP_API_KEY)

                    components.html(kakao_map_html, height=650)

                except Exception as e:
                    st.error(f"❌ 지도 생성 중 오류 발생: {e}")
                    st.info("🔧 해결책:")
                    st.code("""
1. 브라우저 새로고침 (Ctrl+F5)
2. 다른 브라우저에서 시도
3. 카카오 개발자센터에서 도메인 등록 확인
4. API 키 재발급
                    """)

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
        try:
            # 전체 데이터를 사용한 종합 분석
            generate_analysis(df_shops)

            # ———————————————————————————————————————————
            # (2) 👥 인구 대비 가맹점 수 (1,000명당) - 여기서부터 추가
            # ———————————————————————————————————————————
            st.markdown("### 👥 인구 대비 가맹점 수 (1,000명당)")

            try:
                # 구별 매장 수 집계
                store_counts = df_shops.groupby("district").size().reset_index(name="stores")

                # 인구 데이터 읽어오기
                pop_df = pd.read_csv(
                    "data/district_population.csv",
                    skiprows=2,
                    usecols=[0, 2],
                    names=["district", "population"],
                    header=None
                )

                # 병합 및 1,000명당 계산
                pop_df = pop_df.merge(store_counts, on="district", how="inner")
                pop_df["stores_per_1000"] = pop_df["stores"] / pop_df["population"] * 1000

                # 버블 차트 생성
                bubble = (
                    alt.Chart(pop_df)
                    .mark_circle(opacity=0.7)
                    .encode(
                        x=alt.X("population:Q", title="인구수"),
                        y=alt.Y("stores:Q", title="매장 수"),
                        size=alt.Size("stores_per_1000:Q", title="1,000명당 매장 수", legend=None),
                        color=alt.Color("stores_per_1000:Q", scale=alt.Scale(scheme="reds"), title="1,000명당 매장 수"),
                        tooltip=["district", "stores", "population", alt.Tooltip("stores_per_1000:Q", format=".2f")]
                    )
                    .properties(height=300)
                )
                st.altair_chart(bubble, use_container_width=True)

            except FileNotFoundError:
                st.warning("인구 데이터 파일(data/district_population.csv)을 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"인구 대비 분석 중 오류: {e}")

            # ———————————————————————————————————————————
            # (3) 🌐 구면적 대비 매장 밀도 (개/km²)
            # ———————————————————————————————————————————
            st.markdown("### 🌐 구면적 대비 매장 밀도 (개/km²)")

            try:
                # 구별 매장 수 집계 (재사용)
                store_counts = df_shops.groupby("district").size().reset_index(name="stores")

                # 면적 데이터 읽어오기
                area_df = pd.read_csv(
                    "data/district_area_km2.csv",
                    skiprows=3,
                    usecols=[1, 3],
                    names=["district", "area_km2"],
                    header=None
                )

                # 병합 및 밀도 계산
                area_df = area_df.merge(store_counts, on="district", how="inner")
                area_df["density"] = area_df["stores"] / area_df["area_km2"]

                # 바 차트 생성
                bar = (
                    alt.Chart(area_df.sort_values("density", ascending=False))
                    .mark_bar()
                    .encode(
                        x=alt.X("density:Q", title="개/km²"),
                        y=alt.Y("district:N", sort=alt.EncodingSortField("density", order="descending")),
                        tooltip=["district", "stores", "area_km2", alt.Tooltip("density:Q", format=".2f")]
                    )
                    .properties(height=400)
                )
                st.altair_chart(bar, use_container_width=True)

            except FileNotFoundError:
                st.warning("면적 데이터 파일(data/district_area_km2.csv)을 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"면적 대비 분석 중 오류: {e}")

        except Exception as e:
            # 여기서부터는 원래 코드 그대로
            st.error(f"통계 분석 중 오류가 발생했습니다: {e}")
            st.info("기본 통계 정보를 표시합니다.")

            # 기본 통계 정보 표시
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("지역구별 매장 수")
                district_counts = df_shops['district'].value_counts()
                st.bar_chart(district_counts)

            with col2:
                st.subheader("업종별 매장 수")
                industry_counts = df_shops['industry_code'].value_counts().head(10)
                st.bar_chart(industry_counts)
    else:
        st.warning("조건에 맞는 매장이 없어서 기본 통계를 표시합니다.")
        # 필터링된 데이터가 없어도 전체 데이터로 분석
        if not df_shops.empty:
            try:
                generate_analysis(df_shops)
            except Exception as e:
                st.error(f"통계 분석 중 오류가 발생했습니다: {e}")
        else:
            st.error("데이터를 불러올 수 없습니다.")


with tab4:
    st.subheader("📈 성동구청 크롤링 분석")

    try:
        from utils.analysis_sungdong import run_sungdong_analysis
        run_sungdong_analysis()
    except ImportError:
        st.warning("⚠️ 분석 함수를 찾을 수 없습니다.")
        st.info("💡 현재 개발 중인 기능입니다.")
    except Exception as e:
        st.error(f"❌ 오류: {e}")

# --- 푸터 ---
st.markdown("---")
st.markdown("🔧 **카카오맵 API**를 활용한 민생회복 소비쿠폰 사용처 검색 서비스")