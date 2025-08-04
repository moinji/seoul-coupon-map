import streamlit as st

# --- Streamlit 앱 설정 (가장 먼저 실행되어야 함) ---
st.set_page_config(layout="wide", page_title="민생회복 소비쿠폰 사용처", page_icon="💸")

import pandas as pd
import streamlit.components.v1 as components
import os
import math
from datetime import datetime
import json
import html  # HTML 이스케이프를 위해 추가
from utils.data_analysis import generate_analysis
from dotenv import load_dotenv
from utils.analysis_sungdong import run_sungdong_analysis

# matplotlib 한글 폰트 설정
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import warnings
import platform

def configure_matplotlib_fonts():
    """matplotlib 한글 폰트 설정"""
    try:
        warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
        warnings.filterwarnings('ignore', message='findfont: Font family')
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        system = platform.system()
        if system == 'Windows':
            preferred = ['Malgun Gothic','Gulim','Dotum','Arial Unicode MS','DejaVu Sans']
        elif system == 'Darwin':
            preferred = ['Arial Unicode MS','AppleGothic','Helvetica','DejaVu Sans']
        else:
            preferred = ['DejaVu Sans','Liberation Sans','Arial','sans-serif']
        for font in preferred:
            if font in available_fonts or font=='sans-serif':
                plt.rcParams['font.family']=font
                break
        plt.rcParams['axes.unicode_minus']=False
        plt.rcParams['font.size']=10
        plt.rcParams['figure.figsize']=(10,6)
    except:
        plt.rcParams['font.family']='sans-serif'
        plt.rcParams['axes.unicode_minus']=False

configure_matplotlib_fonts()
load_dotenv()
KAKAO_MAP_API_KEY = os.getenv("KAKAO_MAP_API_KEY")

def calculate_distance(lat1, lon1, lat2, lon2):
    R=6371
    a=(math.sin(math.radians(lat2-lat1)/2)**2+
       math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*
       math.sin(math.radians(lon2-lon1)/2)**2)
    return R*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

@st.cache_data
def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        st.error(f"'{csv_path}' 파일을 찾을 수 없습니다.")
        return pd.DataFrame()
    encs=['utf-8','euc-kr','cp949','utf-8-sig']
    for enc in encs:
        try:
            df=pd.read_csv(csv_path,encoding=enc,skipinitialspace=True,quoting=1)
            break
        except:
            df=None
    if df is None:
        st.error("읽을 수 있는 인코딩이 없습니다.")
        return pd.DataFrame()
    df.columns=df.columns.str.strip()
    req=['이름','서울페이업종코드','주소','상세주소','위도','경도']
    for c in req:
        if c not in df.columns:
            st.error(f"필수 컬럼 {c} 누락")
            return pd.DataFrame()
    df=df.rename(columns={
        '이름':'store_name','서울페이업종코드':'industry_code',
        '주소':'address','상세주소':'detail_address',
        '위도':'latitude','경도':'longitude'
    })
    df['full_address']=df['address'].fillna('')+' '+df['detail_address'].fillna('')
    df['latitude']=pd.to_numeric(df['latitude'],errors='coerce')
    df['longitude']=pd.to_numeric(df['longitude'],errors='coerce')
    df.dropna(subset=['latitude','longitude'],inplace=True)
    seoul_districts=[ '강남구','강동구','강북구','강서구','관악구','광진구','구로구','금천구','노원구',
        '도봉구','동대문구','동작구','마포구','서대문구','서초구','성동구','성북구','송파구',
        '양천구','영등포구','용산구','은평구','종로구','중구','중랑구'
    ]
    def get_dist(addr):
        for d in seoul_districts:
            if d in addr: return d
        return '기타'
    df['district']=df['address'].apply(get_dist)
    return df

def create_kakao_map(filtered_df,user_lat,user_lon,max_distance,kakao_api_key):
    if not kakao_api_key:
        return "<div style='color:red'>API 키 없음</div>"
    markers=[]
    for _,r in filtered_df.iterrows():
        markers.append({
            'lat':float(r['latitude']),'lng':float(r['longitude']),
            'name':html.escape(r['store_name']),'addr':html.escape(r['full_address']),
            'dist':round(r['distance'],2)
        })
    if not markers:
        return "<div>표시할 매장 없음</div>"
    mj=json.dumps(markers,ensure_ascii=False)
    html_content=f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
#map{{width:100%;height:600px}}#loading{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);}}
</style></head><body>
<div id="loading">지도 로딩 중...</div><div id="map"></div>
<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_api_key}&libraries=clusterer&autoload=false"></script>
<script>
function hideL(){{document.getElementById('loading').style.display='none';}}
kakao.maps.load(function(){{
 hideL();
 var map=new kakao.maps.Map(document.getElementById('map'),{{
   center:new kakao.maps.LatLng({user_lat},{user_lon}),level:5
 }});
 var userPos=new kakao.maps.LatLng({user_lat},{user_lon});
 new kakao.maps.Marker({{position:userPos,map:map}});
 new kakao.maps.Circle({{map:map,center:userPos,radius:{max_distance*1000},strokeWeight:2,fillOpacity:0.1}});
 var data={mj},markers=[];
 data.forEach(function(d){{
   var m=new kakao.maps.Marker({{position:new kakao.maps.LatLng(d.lat,d.lng),map:map}});
   var iw=new kakao.maps.InfoWindow({{content:`<div><strong>${{d.name}}</strong><br/>거리:${{d.dist}}km</div>`}});
   kakao.maps.event.addListener(m,'click',function(){{iw.open(map,m);}});
 }});
}});
</script></body></html>
"""
    return html_content

st.title("💸 민생회복 소비쿠폰 사용처 찾기")
st.markdown("**쿠폰 사용 가능 매장 조회 & 즐겨찾기**")

csv_file='./data/result11.csv'
df_shops=load_and_preprocess_data(csv_file)
if df_shops.empty: st.stop()

# --- 사이드바 필터 ---
st.sidebar.header("🔍 필터 설정")
search_query=st.sidebar.text_input("매장 이름 검색")
all_districts=['전체']+sorted(df_shops['district'].unique())
sel_district=st.sidebar.selectbox("지역구 선택",all_districts)
all_codes=['전체']+sorted(df_shops['industry_code'].unique())
sel_code=st.sidebar.selectbox("업종코드 선택",all_codes)
st.sidebar.markdown("---")
st.sidebar.header("📍 내 위치 설정")
if 'user_loc' not in st.session_state:
    st.session_state.user_loc=(37.5665,126.9780)
col1,col2=st.sidebar.columns(2)
user_lat=col1.number_input("위도",value=st.session_state.user_loc[0])
user_lon=col2.number_input("경도",value=st.session_state.user_loc[1])
max_distance=st.sidebar.slider("반경 (km)",0.5,20.0,5.0,0.5)
if st.sidebar.button("내 위치로 이동"):
    st.session_state.user_loc=(user_lat,user_lon)
    st.sidebar.success("위치 업데이트됨")

# --- 필터 적용 ---
fdf=df_shops.copy()
if search_query:
    fdf=fdf[fdf['store_name'].str.contains(search_query,case=False,na=False)]
if sel_district!='전체':
    fdf=fdf[fdf['district']==sel_district]
if sel_code!='전체':
    fdf=fdf[fdf['industry_code']==sel_code]
if not fdf.empty:
    fdf['distance']=fdf.apply(lambda r:calculate_distance(user_lat,user_lon,r['latitude'],r['longitude']),axis=1)
    fdf=fdf[fdf['distance']<=max_distance].sort_values('distance').head(1000)

# --- 메트릭스 ---
c1,c2,c3,c4=st.columns(4)
c1.metric("전체 매장 수",len(df_shops))
c2.metric("필터 매장 수",len(fdf))
c3.metric("평균 거리",f"{fdf['distance'].mean():.1f} km" if not fdf.empty else "0 km")
c4.metric("지역구 수",f"{fdf['district'].nunique()}" if not fdf.empty else "0")

# --- 탭 ---
tab1,tab2,tab3,tab4=st.tabs(["🗺️ 카카오맵","📋 리스트","📊 통계","⭐️ 즐겨찾기"])

with tab1:
    st.subheader("📍 매장 위치 (카카오맵)")
    if not fdf.empty:
        html=create_kakao_map(fdf,user_lat,user_lon,max_distance,KAKAO_MAP_API_KEY)
        components.html(html,height=650)
    else:
        st.warning("표시할 매장 없음")

with tab2:
    st.subheader("📋 매장 리스트")
    if not fdf.empty:
        disp=fdf[['store_name','industry_code','full_address','district','distance']].copy()
        disp.columns=['매장명','업종코드','주소','지역구','거리(km)']
        disp['거리(km)']=disp['거리(km)'].round(2)
        st.dataframe(disp,use_container_width=True,height=400)
        csv=fdf.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("📥 CSV 다운로드",data=csv,file_name="stores.csv")
    else:
        st.warning("표시할 매장 없음")

with tab3:
    st.subheader("📊 통계 정보")
    if not fdf.empty:
        generate_analysis(df_shops)

        # (2) 👥 인구 대비 가맹점 수 (1,000명당)
        st.markdown("### 👥 인구 대비 가맹점 수 (1,000명당)")
        store_counts=df_shops.groupby("district").size().reset_index(name="stores")
        pop_df=pd.read_csv("data/district_population.csv",
                           skiprows=2,usecols=[0,2],
                           names=["district","population"],header=None)
        pop_df=pop_df.merge(store_counts,on="district")
        pop_df["stores_per_1000"]=pop_df["stores"]/pop_df["population"]*1000

        import altair as alt
        bubble=(
            alt.Chart(pop_df)
            .mark_circle(opacity=0.7)
            .encode(
                x=alt.X("population:Q",title="인구수"),
                y=alt.Y("stores:Q",title="매장 수"),
                size=alt.Size("stores_per_1000:Q",
                              title="1,000명당 매장 수",
                              scale=alt.Scale(range=[100,2000])),
                color=alt.Color("stores_per_1000:Q",
                                title="1,000명당 매장 수",
                                scale=alt.Scale(scheme="reds")),
                tooltip=["district","stores","population",alt.Tooltip("stores_per_1000:Q",format=".2f")]
            )
            .properties(height=400)
        )
        st.altair_chart(bubble,use_container_width=True)

        # (3) 🌐 구면적 대비 매장 밀도 (개/km²)
        st.markdown("### 🌐 구면적 대비 매장 밀도 (개/km²)")
        area_df=pd.read_csv("data/district_area_km2.csv",
                            skiprows=3,usecols=[1,3],
                            names=["district","area_km2"],header=None)
        area_df=area_df.merge(store_counts,on="district")
        area_df["density"]=area_df["stores"]/area_df["area_km2"]
        bar=(
            alt.Chart(area_df.sort_values("density",ascending=False))
            .mark_bar()
            .encode(
                x=alt.X("density:Q",title="개/km²"),
                y=alt.Y("district:N",sort=alt.EncodingSortField("density",order="descending")),
                tooltip=["district","stores","area_km2",alt.Tooltip("density:Q",format=".2f")]
            )
            .properties(height=400)
        )
        st.altair_chart(bar,use_container_width=True)
    else:
        st.warning("통계 표시할 데이터 없음")

with tab4:
    st.subheader("⭐️ 즐겨찾기")
    if 'favorites' not in st.session_state:
        st.session_state.favorites=[]
    if not fdf.empty:
        # 지도 클릭 시 자바스크립트로 favorites 배열에 추가되도록 구현 필요
        st.info("지도에서 ☆ 아이콘을 클릭하면 여기에 추가됩니다.")
    if st.session_state.favorites:
        st.table(pd.DataFrame(st.session_state.favorites,columns=["매장명","주소","거리(km)"]))
    else:
        st.info("아직 즐겨찾기가 없습니다.")

# --- 푸터 ---
st.markdown("---")
st.markdown("🔧 카카오맵 API 기반 서울 민생회복 소비쿠폰 사용처 대시보드")

