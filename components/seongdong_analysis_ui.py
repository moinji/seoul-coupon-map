import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.seongdong_analysis_utils import DONG_MERGE_MAP, plot_bar

def display_data_summary_tab(shop_df, pop_df, merged_df):
    st.markdown("### 🔍 데이터 출처 및 설명")
    st.markdown("""
    - **shops_seongdong.csv**: 성동구청 소비쿠폰 가맹점 데이터 (웹 크롤링)
    - **seongdong_population.csv**: 성동구 인구 통계 데이터 (공공데이터)
    """)
    
    st.markdown("### 📊 데이터 구조")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**가맹점 데이터 샘플**")
        st.dataframe(shop_df.head(), use_container_width=True)
        
    with col2:
        st.markdown("**인구 데이터 샘플**")
        st.dataframe(pop_df.head(), use_container_width=True)
    
    st.markdown("### 🔗 동 매핑 방식")
    st.markdown("""
    **매핑 전략**: 행정동을 법정동으로 통합
    - 성수1가제1동 + 성수1가제2동 → 성수동1가
    - 행당제1동 + 행당제2동 → 행당동
    """)
    mapping_df = pd.DataFrame(list(DONG_MERGE_MAP.items()), columns=['행정동', '통합동'])
    st.dataframe(mapping_df, use_container_width=True)
    st.write(f"데이터 병합 후: {len(merged_df)}행, 총인구수 유효한 행: {merged_df['총인구수'].notna().sum()}개")
    st.markdown("### 🛠️ 전처리 흐름")
    st.markdown("""
    1. **데이터 수집**: 웹 크롤링으로 가맹점 데이터 수집
    2. **동 매핑**: 행정동을 법정동으로 매핑하여 통합
    3. **데이터 병합**: 가맹점 데이터와 인구 데이터 결합
    4. **파생변수 생성**: 인구 대비 매장 밀도, 성비 등 계산
    5. **시각화**: 다양한 차트와 지도로 인사이트 도출
    """)

def display_population_stats_tab(pop_df):
    st.markdown("### 👨‍👩‍👧‍👦 성동구 인구 통계 분석")
    
    # 전체 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 동 수", f"{len(pop_df)}개")
    with col2:
        st.metric("총 인구수", f"{pop_df['총인구수'].sum():,}명")
    with col3:
        st.metric("총 남성 인구", f"{pop_df['남자인구수'].sum():,}명")
    with col4:
        st.metric("총 여성 인구", f"{pop_df['여자인구수'].sum():,}명")
    
    # 동별 인구 통계 시각화
    st.markdown("#### 📊 동별 총인구수 순위")
    pop_sorted = pop_df.sort_values('총인구수', ascending=False)
    plot_bar(pop_sorted, "행정기관", "총인구수", "동별 총인구수", "동", "인구수(명)")
    
    st.markdown("#### 👶 연령대별 인구 분포")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**5세 이하 인구수**")
        plot_bar(pop_df.sort_values('5세이하인구수', ascending=False), 
                "행정기관", "5세이하인구수", "동별 5세 이하 인구수", "동", "인구수(명)", height=4)
    
    with col2:
        st.markdown("**65세 이상 인구수**")
        plot_bar(pop_df.sort_values('65세이상인구수', ascending=False), 
                "행정기관", "65세이상인구수", "동별 65세 이상 인구수", "동", "인구수(명)", height=4)
    
    st.markdown("#### 📈 전월대비 인구 증감률")
    st.info("💡 **전월대비**: 직전 달 대비 인구 증감률을 의미합니다. 양수는 인구 증가, 음수는 인구 감소를 나타냅니다.")
    plot_bar(pop_df.sort_values('전월대비', ascending=False), 
            "행정기관", "전월대비", "동별 전월대비 인구 증감률", "동", "증감률(%)")
    
    st.markdown("#### 🏆 인구수 순위")
    st.info("💡 **순위**: 성동구 내 동 중 총인구수 기준 순위입니다. 1위가 가장 인구가 많은 동입니다.")
    plot_bar(pop_df.sort_values('순위'), 
            "행정기관", "순위", "동별 인구수 순위", "동", "순위")

def display_shop_stats_tab(shop_df):
    st.markdown("### 🏪 소비쿠폰 가맹점 통계")
    
    if shop_df.empty:
        st.error("가맹점 데이터가 없습니다. 먼저 크롤링을 실행해주세요.")
        return
    
    # 전체 통계
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("전체 매장 수", f"{len(shop_df):,}개")
    with col2:
        unique_dongs = shop_df['dong'].nunique() if 'dong' in shop_df.columns else 0
        st.metric("가맹점 보유 동 수", f"{unique_dongs}개")
    with col3:
        if unique_dongs > 0:
            avg_stores = len(shop_df) / unique_dongs
            st.metric("동별 평균 매장 수", f"{avg_stores:.1f}개")
        else:
            st.metric("동별 평균 매장 수", "0개")
    
    # dong 컬럼 확인
    if 'dong' not in shop_df.columns:
        st.error("가맹점 데이터에 'dong' 컬럼이 없습니다. 데이터 구조를 확인해주세요.")
        st.write("현재 컬럼:", list(shop_df.columns))
        return
    
    # 동별 매장 수 통계
    store_counts = shop_df['dong'].value_counts().reset_index()
    store_counts.columns = ['dong', '매장수']
    
    if len(store_counts) == 0:
        st.warning("동별 매장 데이터가 없습니다.")
        return
    
    st.markdown("#### 📊 동별 가맹점 수 순위")
    plot_bar(store_counts, "dong", "매장수", "동별 소비쿠폰 가맹점 수", "동", "매장 수(개)")
    
    # 최다/최소 매장 보유 동
    if len(store_counts) >= 1:
        col1, col2 = st.columns(2)
        with col1:
            max_dong = store_counts.iloc[0]
            st.success(f"🥇 **가장 많은 동**: {max_dong['dong']} ({max_dong['매장수']}개)")
        with col2:
            min_dong = store_counts.iloc[-1]
            st.warning(f"🔻 **가장 적은 동**: {min_dong['dong']} ({min_dong['매장수']}개)")
    
    # 매장 분포 히스토그램
    if len(store_counts) > 1:
        st.markdown("#### 📈 매장 수 분포")
        fig, ax = plt.subplots(figsize=(10, 4))
        plt.hist(store_counts['매장수'], bins=min(10, len(store_counts)), alpha=0.7, color='skyblue', edgecolor='black')
        plt.title('동별 매장 수 분포')
        plt.xlabel('매장 수')
        plt.ylabel('동의 개수')
        plt.tight_layout()
        st.pyplot(fig)
    
    # 데이터 테이블 표시
    st.markdown("#### 📋 동별 매장 수 상세")
    st.dataframe(store_counts, use_container_width=True)

def display_integrated_analysis_tab(shop_df, pop_df, merged_df, dong_analysis=None):
    st.markdown("### 🔄 인구 + 가맹점 통합 분석")
    
    # 데이터 유효성 검사
    if merged_df.empty:
        st.error("통합 데이터가 없습니다. 데이터 병합을 확인해주세요.")
        return
    
    if 'dong' not in shop_df.columns:
        st.error("가맹점 데이터에 'dong' 컬럼이 없습니다.")
        return
    
    # 총인구수가 있는 데이터만 필터링 (더 유연한 접근)
    if '총인구수' not in merged_df.columns:
        st.error("병합된 데이터에 '총인구수' 컬럼이 없습니다!")
        return
    
    # NaN이 아닌 총인구수 데이터 확인
    valid_merged = merged_df[merged_df['총인구수'].notna() & (merged_df['총인구수'] > 0)]
    
    st.write(f"🔍 **통합 분석 데이터 현황**")
    st.write(f"전체 병합 데이터: {len(merged_df)}개")
    st.write(f"총인구수 정보가 있는 데이터: {len(valid_merged)}개")
    
    # 병합이 제대로 안된 경우를 위한 대안 - 동 이름으로 직접 매칭
    if len(valid_merged) == 0 or dong_analysis is None:
        st.warning("⚠️ 병합 데이터에서 총인구수를 찾을 수 없거나 분석 데이터가 없습니다. 대안 방법을 시도합니다.")
        
        # 가맹점 데이터의 동별 매장수 계산
        if 'dong' in shop_df.columns:
            store_counts = shop_df['dong'].value_counts().reset_index()
            store_counts.columns = ['dong', '매장수']
            
            # 인구 데이터에서 동별 총인구수 가져오기
            pop_summary = pop_df[['행정기관', '총인구수', '남자인구수', '여자인구수']].copy()
            
            # 수동으로 매칭해보기
            manual_merged = []
            for _, store_row in store_counts.iterrows():
                dong_name = store_row['dong']
                매장수 = store_row['매장수']
                
                # 인구 데이터에서 해당 동 찾기
                pop_match = pop_summary[pop_summary['행정기관'] == dong_name]
                
                if len(pop_match) > 0:
                    pop_data = pop_match.iloc[0]
                    manual_merged.append({
                        'dong': dong_name,
                        '매장수': 매장수,
                        '총인구수': pop_data['총인구수'],
                        '남자인구수': pop_data['남자인구수'],
                        '여자인구수': pop_data['여자인구수']
                    })
            
            if manual_merged:
                dong_analysis = pd.DataFrame(manual_merged)
                dong_analysis['인구대비매장밀도'] = dong_analysis['매장수'] / dong_analysis['총인구수'] * 10000
                dong_analysis['성비'] = dong_analysis['남자인구수'] / dong_analysis['여자인구수']
                
                st.success(f"✅ **수동 매칭 성공: {len(dong_analysis)}개 동 분석 가능**")
                
                # 인구 대비 매장 밀도 시각화
                st.markdown("#### 🏆 동별 인구 대비 매장 밀도 (인구 1만명당 매장 수)")
                st.info("💡 **인구 대비 매장 밀도**: 총인구수 대비 가맹점 수로 계산한 상권 밀도 지표입니다.")
                
                density_sorted = dong_analysis.sort_values('인구대비매장밀도', ascending=False)
                plot_bar(density_sorted, "dong", "인구대비매장밀도", 
                        "동별 인구 대비 매장 밀도", "동", "1만명당 매장수", color="green")
                
                # 상위/하위 동 강조
                if len(density_sorted) >= 1:
                    col1, col2 = st.columns(2)
                    with col1:
                        top_dong = density_sorted.iloc[0]
                        st.success(f"🥇 **매장밀도 1위**: {top_dong['dong']} ({top_dong['인구대비매장밀도']:.2f}개/만명)")
                    with col2:
                        if len(density_sorted) > 1:
                            bottom_dong = density_sorted.iloc[-1]
                            st.warning(f"🔻 **매장밀도 최하위**: {bottom_dong['dong']} ({bottom_dong['인구대비매장밀도']:.2f}개/만명)")
                
                # 성비와 매장수 관계 분석
                if len(dong_analysis) > 1:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    scatter = ax.scatter(dong_analysis['성비'], dong_analysis['매장수'], 
                                       c=dong_analysis['인구대비매장밀도'], cmap='viridis', s=100, alpha=0.7)
                    
                    for i, row in dong_analysis.iterrows():
                        ax.annotate(row['dong'], (row['성비'], row['매장수']), 
                                   xytext=(5, 5), textcoords='offset points', fontsize=8)
                    
                    plt.colorbar(scatter, label='인구 대비 매장 밀도')
                    plt.xlabel('성비 (남자/여자)')
                    plt.ylabel('매장 수')
                    plt.title('성비와 매장 수 관계 (색상: 인구 대비 매장 밀도)')
                    plt.tight_layout()
                    st.pyplot(fig)
                
                # 통합 분석 테이블
                st.markdown("#### 📋 동별 종합 분석 테이블")
                display_df = dong_analysis[['dong', '총인구수', '매장수', '인구대비매장밀도', '성비']].copy()
                display_df = display_df.sort_values('인구대비매장밀도', ascending=False)
                display_df['인구대비매장밀도'] = display_df['인구대비매장밀도'].round(2)
                display_df['성비'] = display_df['성비'].round(3)
                st.dataframe(display_df, use_container_width=True)
                
                return  # 성공적으로 분석했으므로 여기서 종료
        
        # 대안 분석도 실패한 경우
        st.markdown("#### 📊 기본 가맹점 통계")
        if len(shop_df) > 0:
            store_counts = shop_df['dong'].value_counts().reset_index()
            store_counts.columns = ['dong', '매장수']
            
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = sns.barplot(data=store_counts.head(10), x='dong', y='매장수', ax=ax)
            ax.set_title('동별 가맹점 수 (상위 10개)', fontsize=14, fontweight='bold')
            ax.set_xlabel('동', fontsize=12)
            ax.set_ylabel('매장 수', fontsize=12)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=10)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        
        return
    
    # 인구 대비 매장 밀도 계산
    # dong_analysis는 외부에서 계산되어 넘어온다고 가정
    if dong_analysis is None or dong_analysis.empty:
        st.warning("분석할 동 데이터가 없습니다.")
        return

    st.write(f"✅ **분석 가능한 동: {len(dong_analysis)}개**")
    
    # 인구 대비 매장 밀도 시각화
    st.markdown("#### 🏆 동별 인구 대비 매장 밀도 (인구 1만명당 매장 수)")
    st.info("💡 **인구 대비 매장 밀도**: 총인구수 대비 가맹점 수로 계산한 상권 밀도 지표입니다. 점수가 높을수록 인구 대비 매장이 많습니다.")
    
    density_sorted = dong_analysis.sort_values('인구대비매장밀도', ascending=False)
    plot_bar(density_sorted, "dong", "인구대비매장밀도", 
            "동별 인구 대비 매장 밀도", "동", "1만명당 매장수", color="green")
    
    # 상위/하위 동 강조
    if len(density_sorted) >= 1:
        col1, col2 = st.columns(2)
        with col1:
            top_dong = density_sorted.iloc[0]
            st.success(f"🥇 **매장밀도 1위**: {top_dong['dong']} ({top_dong['인구대비매장밀도']:.2f}개/만명)")
        with col2:
            if len(density_sorted) > 1:
                bottom_dong = density_sorted.iloc[-1]
                st.warning(f"🔻 **매장밀도 최하위**: {bottom_dong['dong']} ({bottom_dong['인구대비매장밀도']:.2f}개/만명)")
    
    # 성비와 매장수 관계 분석
    if len(dong_analysis) > 1:
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(dong_analysis['성비'], dong_analysis['매장수'], 
                           c=dong_analysis['인구대비매장밀도'], cmap='viridis', s=100, alpha=0.7)
        
        for i, row in dong_analysis.iterrows():
            ax.annotate(row['dong'], (row['성비'], row['매장수']), 
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        plt.colorbar(scatter, label='인구 대비 매장 밀도')
        plt.xlabel('성비 (남자/여자)')
        plt.ylabel('매장 수')
        plt.title('성비와 매장 수 관계 (색상: 인구 대비 매장 밀도)')
        plt.tight_layout()
        st.pyplot(fig)
    
    # 통합 분석 테이블
    st.markdown("#### 📋 동별 종합 분석 테이블")
    display_df = dong_analysis[['dong', '총인구수', '매장수', '인구대비매장밀도', '성비']].copy()
    display_df = display_df.sort_values('인구대비매장밀도', ascending=False)
    display_df['인구대비매장밀도'] = display_df['인구대비매장밀도'].round(2)
    display_df['성비'] = display_df['성비'].round(3)
    st.dataframe(display_df, use_container_width=True)

def display_advanced_analysis_tab(shop_df, pop_df, merged_df, dong_analysis=None, cluster_results=None):
    st.markdown("### 📚 고급 분석 및 종합 인사이트")
    
    # 데이터 유효성 확인
    if merged_df.empty or pop_df.empty or shop_df.empty:
        st.error("분석할 데이터가 부족합니다.")
        return
    
    # 유효한 데이터 확인
    valid_merged = merged_df.dropna(subset=['총인구수'])
    
    st.write(f"🔍 **고급 분석 데이터 현황**")
    st.write(f"유효한 통합 데이터: {len(valid_merged)}개")
    
    # 유효한 데이터가 있는 경우에만 고급 분석 진행
    if len(valid_merged) > 0 and dong_analysis is not None:
        # 1. 인구 대비 매장 밀도 최종 순위
        st.markdown("#### 🏆 인구 대비 매장 밀도 최종 순위")
        final_ranking = dong_analysis.sort_values('인구대비매장밀도', ascending=False)
        plot_bar(final_ranking, "dong", "인구대비매장밀도", 
                "최종 인구 대비 매장 밀도 순위", "동", "1만명당 매장수", color="gold")
        
        # 2. 인구 증감과 매장 수 관계
        st.markdown("#### 📈 인구 증감률과 매장 수 관계")
        if '전월대비' in merged_df.columns:
            growth_analysis = merged_df.dropna(subset=['전월대비']).groupby('dong').agg({
                'store_name': 'count',
                '전월대비': 'first'
            }).reset_index()
            
            if len(growth_analysis) > 1:
                fig, ax = plt.subplots(figsize=(10, 6))
                scatter = ax.scatter(growth_analysis['전월대비'], growth_analysis['store_name'], 
                                   s=100, alpha=0.7, c='coral')
                
                for i, row in growth_analysis.iterrows():
                    ax.annotate(row['dong'], (row['전월대비'], row['store_name']), 
                               xytext=(5, 5), textcoords='offset points', fontsize=8)
                
                plt.xlabel('전월대비 인구 증감률 (%)')
                plt.ylabel('매장 수')
                plt.title('인구 증감률과 매장 수 관계')
                plt.axvline(x=0, color='red', linestyle='--', alpha=0.5)
                plt.tight_layout()
                st.pyplot(fig)
        
        # 인사이트 표시
        st.markdown("#### 💡 핵심 인사이트")
        top_density = final_ranking.iloc[0]
        st.success(f"🥇 **매장밀도 1위**: {top_density['dong']} ({top_density['인구대비매장밀도']:.2f}개/만명)")
        
    else:
        # 기본 분석
        st.markdown("#### 📊 기본 가맹점 분석")
        if len(shop_df) > 0 and 'dong' in shop_df.columns:
            store_counts = shop_df['dong'].value_counts().reset_index()
            store_counts.columns = ['dong', '매장수']
            plot_bar(store_counts.head(10), "dong", "매장수", "동별 가맹점 수 (상위 10개)", "동", "매장수", color="skyblue")
            
            top_store = store_counts.iloc[0]
            st.success(f"🏪 **매장 수 1위**: {top_store['dong']} ({top_store['매장수']}개)")
        
        if len(pop_df) > 0:
            st.markdown("#### 👥 기본 인구 분석")
            pop_sorted = pop_df.sort_values('총인구수', ascending=False)
            plot_bar(pop_sorted.head(10), "행정기관", "총인구수", "동별 총인구수 (상위 10개)", "동", "인구수", color="green")
    
    # 4. KMeans 군집 분석
    st.markdown("#### 🎯 동별 특성 군집 분석")
    
    if cluster_results and cluster_results['pop_df_clustered'] is not None:
        pop_df_clustered = cluster_results['pop_df_clustered']
        cluster_labels = pop_df_clustered['군집']
        cluster_store_counts = cluster_results['cluster_store_counts']
        available_features = cluster_results['available_features']
        n_clusters = cluster_results['n_clusters']

        # 군집 시각화
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**군집별 동 분포**")
            fig, ax = plt.subplots(figsize=(8, 4))
            cluster_counts = pd.Series(cluster_labels).value_counts().sort_index()
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'][:len(cluster_counts)]
            bars = ax.bar(cluster_counts.index, cluster_counts.values, color=colors)
            ax.set_title('군집별 동 개수')
            ax.set_xlabel('군집')
            ax.set_ylabel('동 개수')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            st.markdown("**군집별 총 매장 수**")
            fig, ax = plt.subplots(figsize=(8, 4))
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'][:len(cluster_store_counts)]
            bars = ax.bar(cluster_store_counts['군집'], cluster_store_counts['총매장수'], color=colors)
            ax.set_title('군집별 총 매장 수')
            ax.set_xlabel('군집')
            ax.set_ylabel('매장 수')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        # 군집별 특성 요약
        st.markdown("#### 📊 군집별 평균 특성")
        cluster_summary = pop_df_clustered.groupby('군집')[available_features].mean().round(1)
        st.dataframe(cluster_summary, use_container_width=True)
        
        # 군집별 동 목록 표시 (추가할 부분)
        st.markdown("#### 🏘️ 군집별 동 구성")
        for cluster_id in sorted(pop_df_clustered['군집'].unique()):
            cluster_dongs = pop_df_clustered[pop_df_clustered['군집'] == cluster_id]['행정기관'].tolist()
            dong_list = ', '.join(cluster_dongs)
            
            # 군집별 색상 매칭
            colors = ['🔴', '🟢', '🔵', '🟠']
            color_icon = colors[cluster_id] if cluster_id < len(colors) else '⚪'
            
            st.info(f"{color_icon} **군집 {cluster_id}** ({len(cluster_dongs)}개 동): {dong_list}")
        
        # 군집별 평균 매장 밀도
        if len(valid_merged) > 0:
            cluster_merged = merged_df.merge(pop_df_clustered[['행정기관', '군집']], 
                                           left_on='dong', right_on='행정기관', how='left')
            cluster_density = cluster_merged.dropna(subset=['총인구수']).groupby('군집').apply(
                lambda x: (x['store_name'].count() / x['총인구수'].sum() * 10000) if x['총인구수'].sum() > 0 else 0
            ).reset_index(name='평균매장밀도')
            
            fig, ax = plt.subplots(figsize=(10, 4))
            bars = ax.bar(cluster_density['군집'], cluster_density['평균매장밀도'], 
                         color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'][:len(cluster_density)])
            ax.set_title('군집별 평균 인구 대비 매장 밀도')
            ax.set_xlabel('군집')
            ax.set_ylabel('1만명당 매장수')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}', ha='center', va='bottom')
            
            plt.tight_layout()
            st.pyplot(fig)
        
    else:
        st.info("군집 분석을 위한 충분한 데이터가 없습니다.")
    
    # 5. 종합 인사이트
    st.markdown("#### 💡 핵심 인사이트 요약")
    
    insights = []
    
    # 인구 대비 매장밀도 1위 동 (유효한 데이터가 있는 경우만)
    if len(valid_merged) > 0 and dong_analysis is not None:
        top_density = dong_analysis.sort_values('인구대비매장밀도', ascending=False).iloc[0]
        insights.append(f"🥇 **매장밀도 1위**: {top_density['dong']} ({top_density['인구대비매장밀도']:.2f}개/만명)")
    
    # 매장 수 1위 동
    if 'dong' in shop_df.columns and len(shop_df) > 0:
        store_counts = shop_df['dong'].value_counts()
        if len(store_counts) > 0:
            top_stores_dong = store_counts.index[0]
            top_stores_count = store_counts.iloc[0]
            insights.append(f"🏪 **매장 수 1위**: {top_stores_dong} ({top_stores_count}개)")
    
    # 인구 1위 동
    if len(pop_df) > 0 and '총인구수' in pop_df.columns:
        pop_sorted = pop_df.sort_values('총인구수', ascending=False)
        if len(pop_sorted) > 0:
            top_pop_dong = pop_sorted.iloc[0]['행정기관']
            top_pop_count = pop_sorted.iloc[0]['총인구수']
            insights.append(f"👥 **인구 수 1위**: {top_pop_dong} ({top_pop_count:,.0f}명)")
    
    # 인구 증가율 상위 동 (데이터가 있는 경우)
    if '전월대비' in pop_df.columns:
        growth_sorted = pop_df.sort_values('전월대비', ascending=False)
        if len(growth_sorted) > 0:
            top_growth_dong = growth_sorted.iloc[0]['행정기관']
            top_growth_rate = growth_sorted.iloc[0]['전월대비']
            insights.append(f"📈 **인구 증가율 1위**: {top_growth_dong} ({top_growth_rate:.2f}%)")
    
    # 인사이트 표시
    if insights:
        for insight in insights:
            st.success(insight)
    else:
        st.info("분석 가능한 데이터가 부족합니다.")
    
    st.markdown("#### 📋 발표/보고서용 핵심 포인트")
    st.info("""
    **📊 주요 발견사항**
    - 성동구는 동별로 인구 대비 매장 밀도 편차가 존재하며, 인구 규모와 가맹점 수가 반드시 비례하지 않음
    - 소규모 동이 더 높은 매장 밀도를 보이는 경우가 존재 (인구 대비 매장 수 비율)
    - 동별 특성에 따른 군집 분류를 통해 맞춤형 정책 수립 가능
    - 인구 증감 추세와 현재 상권 분포 간의 관계 분석 필요
    
    **💼 정책적 시사점**
    - 매장 밀도가 낮은 동에 대한 소상공인 창업 지원 정책 검토
    - 인구 증가 지역의 선제적 상권 인프라 구축 방안 마련
    - 동별 특성을 반영한 차별화된 지역 발전 전략 수립
    - 소비쿠폰 가맹점 확대를 통한 지역 상권 활성화 추진
    """)
    
    # 데이터 다운로드 옵션
    st.markdown("#### 📥 분석 결과 다운로드")
    col1, col2 = st.columns(2)
    
    with col1:
        if len(valid_merged) > 0 and dong_analysis is not None:
            if st.button("📊 동별 분석 결과 CSV 다운로드"):
                csv_data = dong_analysis.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="다운로드 시작",
                    data=csv_data,
                    file_name="seongdong_dong_analysis.csv",
                    mime="text/csv"
                )
        else:
            st.info("다운로드할 동별 분석 데이터가 없습니다.")
    
    with col2:
        if len(pop_df) > 0:
            if st.button("👥 인구 데이터 CSV 다운로드"):
                csv_data = pop_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="다운로드 시작",
                    data=csv_data,
                    file_name="seongdong_population_data.csv",
                    mime="text/csv"
                )
        else:
            st.info("다운로드할 인구 데이터가 없습니다.")