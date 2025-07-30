import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

def draw_store_map(df):
    if df.empty:
        return

    center = [df['위도'].mean(), df['경도'].mean()]
    m = folium.Map(location=center, zoom_start=13)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=f"{row['상호명']}<br>{row['업종']}<br>{row['도로명주소']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)

    st_folium(m, width=1000, height=600)
