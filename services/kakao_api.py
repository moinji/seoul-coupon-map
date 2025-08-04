
import os
import requests
import streamlit as st
import config

@st.cache_data(show_spinner=False)
def geocode(address: str):
    """개선된 한글 주소 → (lat, lon) 튜플 반환"""
    if not address:
        return None, None

    REST_KEY = os.getenv(config.KAKAO_REST_API_KEY_ENV)
    if not REST_KEY:
        st.error(f"❌ {config.KAKAO_REST_API_KEY_ENV} 환경변수가 설정되지 않았습니다")
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
                st.error(f"💡 해결방법: .env 파일의 {config.KAKAO_REST_API_KEY_ENV} 확인")
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
