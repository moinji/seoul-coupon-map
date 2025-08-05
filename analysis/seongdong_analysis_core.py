import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def calculate_dong_analysis(merged_df):
    """인구 대비 매장 밀도 및 성비 등 동별 분석 데이터를 계산합니다."""
    dong_analysis = pd.DataFrame()
    valid_merged = merged_df[merged_df['총인구수'].notna() & (merged_df['총인구수'] > 0)]
    if len(valid_merged) > 0:
        dong_analysis = valid_merged.groupby('dong').agg({
            'store_name': 'count',
            '총인구수': 'first',
            '남자인구수': 'first',
            '여자인구수': 'first'
        }).reset_index()
        dong_analysis.columns = ['dong', '매장수', '총인구수', '남자인구수', '여자인구수']
        dong_analysis['인구대비매장밀도'] = dong_analysis['매장수'] / dong_analysis['총인구수'] * 10000
        dong_analysis['성비'] = dong_analysis['남자인구수'] / dong_analysis['여자인구수']
    return dong_analysis

def perform_kmeans_clustering(pop_df, shop_df, merged_df):
    """KMeans 군집 분석을 수행하고 결과를 반환합니다."""
    cluster_results = {'pop_df_clustered': None, 'cluster_store_counts': None, 'available_features': None, 'n_clusters': 0}
    cluster_features = ['총인구수', '남자인구수', '여자인구수', '5세이하인구수', '65세이상인구수']
    available_features = [col for col in cluster_features if col in pop_df.columns]
    
    if len(available_features) >= 3:
        cluster_data = pop_df[available_features].copy()
        cluster_data = cluster_data.dropna()
        
        if len(cluster_data) >= 4:
            scaler = StandardScaler()
            cluster_data_scaled = scaler.fit_transform(cluster_data)
            n_clusters = min(4, len(cluster_data))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(cluster_data_scaled)
            
            pop_df_clustered = pop_df.iloc[cluster_data.index].copy()
            pop_df_clustered['군집'] = cluster_labels
            
            cluster_store_counts = pd.DataFrame()
            if 'dong' in shop_df.columns:
                cluster_merged = merged_df.merge(pop_df_clustered[['행정기관', '군집']], 
                                               left_on='dong', right_on='행정기관', how='left')
                cluster_store_counts = cluster_merged.groupby('군집')['store_name'].count().reset_index()
                cluster_store_counts.columns = ['군집', '총매장수']
            
            cluster_results = {
                'pop_df_clustered': pop_df_clustered,
                'cluster_store_counts': cluster_store_counts,
                'available_features': available_features,
                'n_clusters': n_clusters
            }
    return cluster_results