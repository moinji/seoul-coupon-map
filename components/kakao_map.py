
import streamlit as st
import pandas as pd
import json
import html

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
