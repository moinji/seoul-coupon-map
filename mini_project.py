#streamlit run mini_project.py

import streamlit as st
import streamlit.components.v1 as components  # 중요: 직접 import 필요
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="민생회복 소비쿠폰 사용처 찾기",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 민생회복 소비쿠폰 사용처 찾기")
st.subheader("카카오맵으로 쉽게 찾는 소비쿠폰 가맹점")

# 사이드바 필터
with st.sidebar:
    st.header("🔍 검색 필터")
    
    # 지역 선택
    regions = ["전체", "강남구", "강북구", "마포구", "종로구", "중구", "용산구", 
               "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", 
               "도봉구", "노원구", "은평구", "서대문구", "양천구", "강서구", 
               "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구"]
    selected_region = st.selectbox("지역 선택", regions)
    
    # 업종 선택
    categories = ["전체", "음식점", "카페", "편의점", "미용실", "약국", 
                  "마트", "주유소", "세탁소", "문구점", "꽃집"]
    selected_category = st.selectbox("업종 선택", categories)
    
    # 매장명 검색
    store_name = st.text_input("매장명 검색", placeholder="매장명을 입력하세요")

# 메인 컨텐츠 영역
col1, col2 = st.columns([3, 1])

with col1:
    # 카카오맵 HTML 코드
    kakao_map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>민생회복소비쿠폰 사용처</title>
        <style>
            body {{ margin: 0; padding: 0; font-family: 'Malgun Gothic', sans-serif; }}
            #map {{ width: 100%; height: 600px; }}
            .info-window {{ padding: 10px; min-width: 200px; }}
            .info-title {{ font-size: 14px; font-weight: bold; margin-bottom: 5px; }}
            .info-content {{ font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        
        <!-- 카카오맵 API 로드 -->
        <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey="Java_Script_Kakao_API_Key"&libraries=services,clusterer"></script>
        
        <script>
            // 지도 생성
            var container = document.getElementById('map');
            var options = {{
                center: new kakao.maps.LatLng(37.5665, 126.9780), // 서울시청
                level: 8
            }};
            var map = new kakao.maps.Map(container, options);
            
            // 샘플 가맹점 데이터
            var storeData = [
                {{
                    title: '강남구 한식당 A',
                    latlng: new kakao.maps.LatLng(37.4979, 127.0276),
                    category: '음식점',
                    address: '서울 강남구 테헤란로 123',
                    phone: '02-1234-5678'
                }},
                {{
                    title: '마포구 카페 B',
                    latlng: new kakao.maps.LatLng(37.5563, 126.9226),
                    category: '카페',
                    address: '서울 마포구 홍대입구 456',
                    phone: '02-2345-6789'
                }},
                {{
                    title: '종로구 편의점 C',
                    latlng: new kakao.maps.LatLng(37.5735, 126.9788),
                    category: '편의점',
                    address: '서울 종로구 세종대로 789',
                    phone: '02-3456-7890'
                }},
                {{
                    title: '용산구 미용실 D',
                    latlng: new kakao.maps.LatLng(37.5326, 126.9906),
                    category: '미용실',
                    address: '서울 용산구 한강대로 101',
                    phone: '02-4567-8901'
                }},
                {{
                    title: '성동구 약국 E',
                    latlng: new kakao.maps.LatLng(37.5506, 127.0409),
                    category: '약국',
                    address: '서울 성동구 성수일로 202',
                    phone: '02-5678-9012'
                }}
            ];
            
            // 마커 생성 및 정보창 설정
            storeData.forEach(function(store) {{
                var marker = new kakao.maps.Marker({{
                    position: store.latlng,
                    map: map
                }});
                
                var infowindow = new kakao.maps.InfoWindow({{
                    content: `
                        <div class="info-window">
                            <div class="info-title">${{store.title}}</div>
                            <div class="info-content">
                                <div>업종: ${{store.category}}</div>
                                <div>주소: ${{store.address}}</div>
                                <div>전화: ${{store.phone}}</div>
                            </div>
                        </div>
                    `
                }});
                
                kakao.maps.event.addListener(marker, 'click', function() {{
                    infowindow.open(map, marker);
                }});
            }});
            
            // 지도 확대/축소 컨트롤 추가
            var zoomControl = new kakao.maps.ZoomControl();
            map.addControl(zoomControl, kakao.maps.ControlPosition.TOPRIGHT);
        </script>
    </body>
    </html>
    """
    
    # 카카오맵 표시
    st.write("### 🗺️ 소비쿠폰 가맹점 지도")
    #st.info("⚠️ 실제 사용을 위해서는 카카오맵 API 키를 설정해야 합니다.")
    components.html(kakao_map_html, height=650)

with col2:
    # 통계 정보
    st.write("### 📊 가맹점 현황")
    
    # 샘플 통계 데이터
    total_stores = 1250
    region_stores = 85
    
    st.metric("총 가맹점 수", f"{total_stores:,}개")
    st.metric(f"{selected_region} 가맹점", f"{region_stores}개")
    
    # 업종별 분포 차트
    st.write("### 📈 업종별 분포")
    chart_data = pd.DataFrame({
        '업종': ['음식점', '카페', '편의점', '미용실', '약국', '기타'],
        '개수': [450, 280, 180, 150, 120, 70]
    })
    st.bar_chart(chart_data.set_index('업종'))
    
    # 소비쿠폰 안내
    st.write("### ℹ️ 소비쿠폰 안내")
    with st.expander("신청 기간"):
        st.write("**1차**: 2025.7.21 ~ 9.12")
        st.write("**2차**: 2025.9.22 ~ 10.31")
    
    with st.expander("지급 금액"):
        st.write("- 전 국민: 15만원")
        st.write("- 차상위·한부모: 30만원")
        st.write("- 기초생활수급자: 40만원")
        st.write("- 농어촌 지역: 5만원 추가")
    
    with st.expander("사용 제한"):
        st.write("- 연매출 30억원 이하 소상공인")
        st.write("- 유효기간: 2025.11.30까지")

# 하단 정보
st.write("---")
st.write("### 🏪 가맹점 목록")

# 샘플 가맹점 데이터
sample_stores = pd.DataFrame({
    '매장명': ['강남구 한식당 A', '마포구 카페 B', '종로구 편의점 C', '용산구 미용실 D', '성동구 약국 E'],
    '업종': ['음식점', '카페', '편의점', '미용실', '약국'],
    '주소': [
        '서울 강남구 테헤란로 123',
        '서울 마포구 홍대입구 456', 
        '서울 종로구 세종대로 789',
        '서울 용산구 한강대로 101',
        '서울 성동구 성수일로 202'
    ],
    '전화번호': ['02-1234-5678', '02-2345-6789', '02-3456-7890', '02-4567-8901', '02-5678-9012']
})

# 필터링 적용
filtered_stores = sample_stores.copy()
if selected_region != "전체":
    filtered_stores = filtered_stores[filtered_stores['주소'].str.contains(selected_region)]
if selected_category != "전체":
    filtered_stores = filtered_stores[filtered_stores['업종'] == selected_category]
if store_name:
    filtered_stores = filtered_stores[filtered_stores['매장명'].str.contains(store_name, case=False)]

st.dataframe(filtered_stores, use_container_width=True)

# 푸터
st.write("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    💡 이 앱은 민생회복소비쿠폰 정책의 실질적 활용도를 높이고 소상공인 매출 증대에 기여하고자 개발되었습니다.<br>
    📞 문의사항이 있으시면 관련 기관에 연락해주세요.
</div>
""", unsafe_allow_html=True)
