
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import altair as alt

import config
from components.kakao_map import create_kakao_map
from analysis.main_analysis import generate_analysis
from analysis.seongdong_analysis import run_seongdong_analysis

def create_sidebar(df_shops):
    st.sidebar.header("🔍 필터 설정")
    search_query = st.sidebar.text_input("매장 이름 검색")
    all_districts = ['전체'] + sorted(df_shops['district'].unique().tolist())
    selected_district = st.sidebar.selectbox("지역구 선택", all_districts)
    all_industry_codes = ['전체'] + sorted(df_shops['industry_code'].unique().tolist())
    selected_industry_code = st.sidebar.selectbox("업종코드 선택", all_industry_codes)
    max_distance = st.sidebar.slider("내 위치에서 최대 거리 (km)", 0.5, 20.0, 5.0, 0.5)
    return search_query, selected_district, selected_industry_code, max_distance

def display_main_stats(df_shops, filtered_df, current_addr):
    st.markdown("---")
    st.subheader("💡 현재 위치:")
    st.info(f"**{current_addr}**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("전체 매장 수", f"{len(df_shops):,}")

    with col2:
        st.metric("필터된 매장 수", f"{len(filtered_df):,}")

    with col3:
        if not filtered_df.empty:
            avg_distance = filtered_df['distance'].mean()
            st.metric("평균 거리", f"{avg_distance:.1f} km")
        else:
            st.metric("평균 거리", "0 km")

    with col4:
        st.metric("지역구 수", len(filtered_df['district'].unique()) if not filtered_df.empty else 0)

def create_tabs(filtered_df, df_shops, user_lat, user_lon, max_distance, KAKAO_MAP_API_KEY):
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 카카오맵 보기", "📋 리스트 보기", "📊 통계", "📈 성동구청 크롤링 분석"])

    with tab1:
        st.subheader("📍 카카오맵으로 매장 위치 확인")
        if not filtered_df.empty:
            if not KAKAO_MAP_API_KEY:
                st.error("🔑 카카오 맵 API 키가 없어서 지도를 표시할 수 없습니다.")
            else:
                with st.spinner(f'🗺️ {len(filtered_df)}개 매장의 카카오맵을 생성하는 중...'):
                    try:
                        kakao_map_html = create_kakao_map(filtered_df, user_lat, user_lon, max_distance, KAKAO_MAP_API_KEY)
                        components.html(kakao_map_html, height=650)
                    except Exception as e:
                        st.error(f"❌ 지도 생성 중 오류 발생: {e}")
                st.info(f"✅ 총 {len(filtered_df)}개의 매장이 지도에 표시되었습니다. 마커를 클릭하면 상세 정보를 볼 수 있습니다.")
        else:
            st.warning("필터 조건에 맞는 매장이 없습니다. 검색 조건을 조정해 주세요.")

    with tab2:
        st.subheader("📋 매장 목록")
        if not filtered_df.empty:
            display_columns = ['store_name', 'industry_code', 'full_address', 'district', 'distance']
            display_df = filtered_df[display_columns].copy()
            display_df['distance'] = display_df['distance'].round(2)
            display_df.columns = ['매장명', '업종코드', '주소', '지역구', '거리(km)']
            st.dataframe(display_df, use_container_width=True, height=400)
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
        st.subheader("📊 서울시 소비쿠폰 가맹점 통계 분석")
        if not filtered_df.empty:
            try:
                generate_analysis(df_shops)
                st.markdown("### 👥 인구 대비 가맹점 수 (1,000명당)")
                try:
                    store_counts = df_shops.groupby("district").size().reset_index(name="stores")
                    pop_df = pd.read_csv(config.POPULATION_DATA_PATH, skiprows=2, usecols=[0, 2], names=["district", "population"], header=None)
                    pop_df = pop_df.merge(store_counts, on="district", how="inner")
                    pop_df["stores_per_1000"] = pop_df["stores"] / pop_df["population"] * 1000
                    bubble = (alt.Chart(pop_df).mark_circle(opacity=0.7).encode(
                            x=alt.X("population:Q", title="인구수"),
                            y=alt.Y("stores:Q", title="매장 수"),
                            size=alt.Size("stores_per_1000:Q", title="1,000명당 매장 수", legend=None),
                            color=alt.Color("stores_per_1000:Q", scale=alt.Scale(scheme="reds"), title="1,000명당 매장 수"),
                            tooltip=["district", "stores", "population", alt.Tooltip("stores_per_1000:Q", format=".2f")]
                        ).properties(height=300))
                    st.altair_chart(bubble, use_container_width=True)
                except FileNotFoundError:
                    st.warning(f"인구 데이터 파일({config.POPULATION_DATA_PATH})을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"인구 대비 분석 중 오류: {e}")

                st.markdown("### 🌐 구면적 대비 매장 밀도 (개/km²)")
                try:
                    store_counts = df_shops.groupby("district").size().reset_index(name="stores")
                    area_df = pd.read_csv(config.AREA_DATA_PATH, skiprows=3, usecols=[1, 3], names=["district", "area_km2"], header=None)
                    area_df = area_df.merge(store_counts, on="district", how="inner")
                    area_df["density"] = area_df["stores"] / area_df["area_km2"]
                    bar = (alt.Chart(area_df.sort_values("density", ascending=False)).mark_bar().encode(
                            x=alt.X("density:Q", title="개/km²"),
                            y=alt.Y("district:N", sort=alt.EncodingSortField("density", order="descending")),
                            tooltip=["district", "stores", "area_km2", alt.Tooltip("density:Q", format=".2f")]
                        ).properties(height=400))
                    st.altair_chart(bar, use_container_width=True)
                except FileNotFoundError:
                    st.warning(f"면적 데이터 파일({config.AREA_DATA_PATH})을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"면적 대비 분석 중 오류: {e}")

            except Exception as e:
                st.error(f"통계 분석 중 오류가 발생했습니다: {e}")
                st.info("기본 통계 정보를 표시합니다.")
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
            run_seongdong_analysis()
        except ImportError:
            st.warning("⚠️ 분석 함수를 찾을 수 없습니다.")
            st.info("💡 현재 개발 중인 기능입니다.")
        except Exception as e:
            st.error(f"❌ 오류: {e}")
