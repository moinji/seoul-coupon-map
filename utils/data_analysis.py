import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import entropy
import os
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'NanumGothic', 'AppleGothic']
plt.rcParams['axes.unicode_minus'] = False

def load_data(csv_path='shops.csv'):
    """
    EUC-KR 인코딩의 shops.csv 파일을 로드하고 전처리
    
    Args:
        csv_path (str): CSV 파일 경로
        
    Returns:
        pd.DataFrame: 전처리된 데이터프레임
    """
    if not os.path.exists(csv_path):
        st.error(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return pd.DataFrame()
    
    try:
        # 다양한 인코딩으로 시도
        encodings = ['euc-kr', 'cp949', 'utf-8', 'utf-8-sig']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding, skipinitialspace=True)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        if df is None:
            st.error("지원되는 인코딩으로 파일을 읽을 수 없습니다.")
            return pd.DataFrame()
        
        # 컬럼명 정리
        df.columns = df.columns.str.strip()
        
        # 컬럼명 변경
        column_mapping = {
            '이름': 'store_name',
            '서울페이업종코드': 'industry_code',
            '주소': 'address',
            '상세주소': 'detail_address',
            '위도': 'latitude',
            '경도': 'longitude',
        }
        
        df = df.rename(columns=column_mapping)
        
        # 전체주소 생성
        df['full_address'] = df['address'].astype(str) + ' ' + df['detail_address'].fillna('').astype(str)
        df['full_address'] = df['full_address'].str.strip()
        
        # 위도/경도 숫자 변환
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        # 유효하지 않은 위치 데이터 제거
        df = df.dropna(subset=['latitude', 'longitude'])
        
        # 서울 25개 구 추출
        seoul_districts = [
            '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구',
            '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구',
            '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'
        ]
        
        def extract_district(address):
            if not isinstance(address, str):
                return '기타'
            for district in seoul_districts:
                if district in address:
                    return district
            return '기타'
        
        df['district'] = df['address'].apply(extract_district)
        
        return df
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

def get_industry_name(code):
    """업종코드를 업종명으로 변환"""
    industry_mapping = {
        'A01': '음식점/식음료업',
        'A02': '예술교육',
        'A03': '보건/복지',
        'A04': '의류/잡화',
        'A05': '생활/리빙',
        'A06': '입시/교습학원',
        'A07': '외국어/언어',
        'A08': '기술/기능교육',
        'A09': '식자재/유통',
        'A10': '문화/체육',
        'A11': '자동차/주유',
        'A12': '가전/통신',
        'A13': '건축/철물',
        'A14': '여행/숙박',
        'A15': '디자인/인쇄',
    }
    return industry_mapping.get(code, code)

def is_medical_industry(industry_code, store_name):
    """의료/복지 업종 분류"""
    medical_keywords = ['의료', '복지', '병원', '약국', '한의', '치과', '내과', '정형외과', '산부인과', '소아과', '피부과']
    medical_codes = ['A03']  # 보건/복지 코드
    
    # 업종코드로 분류
    if industry_code in medical_codes:
        return True
    
    # 상호명에 의료 키워드 포함 여부 확인
    if isinstance(store_name, str):
        for keyword in medical_keywords:
            if keyword in store_name:
                return True
    
    return False

def calculate_diversity_index(series):
    """엔트로피를 이용한 다양성 지수 계산"""
    counts = series.value_counts()
    probabilities = counts / counts.sum()
    return entropy(probabilities, base=2)

def generate_analysis(df):
    """
    주요 분석 함수 - Streamlit UI에 통계 분석 결과를 출력
    
    Args:
        df (pd.DataFrame): 분석할 데이터프레임
    """
    if df.empty:
        st.warning("⚠️ 분석할 데이터가 없습니다.")
        return
    
    st.header("📊 민생회복 소비쿠폰 사용처 통계 분석")
    st.markdown("---")
    
    # 전체 요약 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📍 전체 매장 수", f"{len(df):,}개")
    with col2:
        st.metric("🏢 자치구 수", f"{df['district'].nunique()}개")
    with col3:
        st.metric("🏷️ 업종 수", f"{df['industry_code'].nunique()}개")
   
    # 1. 업종별 가맹점 수 시각화
    with st.expander("🏷️ 업종별 가맹점 수 분석", expanded=True):
        st.subheader("업종별 가맹점 분포")
        
        industry_counts = df['industry_code'].value_counts().head(15)
        industry_names = [get_industry_name(code) for code in industry_counts.index]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.barh(range(len(industry_counts)), industry_counts.values, 
                      color=plt.cm.Set3(np.linspace(0, 1, len(industry_counts))))
        ax.set_yticks(range(len(industry_counts)))
        ax.set_yticklabels([f"{name}\n({code})" for name, code in zip(industry_names, industry_counts.index)])
        ax.set_xlabel('가맹점 수')
        ax.set_title('업종별 가맹점 수 TOP 15', fontsize=16, fontweight='bold')
        
        # 값 표시
        for i, (bar, count) in enumerate(zip(bars, industry_counts.values)):
            ax.text(bar.get_width() + max(industry_counts.values) * 0.01, 
                   bar.get_y() + bar.get_height()/2, 
                   f'{count:,}개', va='center', fontweight='bold')
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # 상위 5개 업종 요약
        st.markdown("**📈 상위 5개 업종**")
        for i, (code, count) in enumerate(industry_counts.head(5).items(), 1):
            percentage = count / len(df) * 100
            st.write(f"{i}. **{get_industry_name(code)}** ({code}): {count:,}개 ({percentage:.1f}%)")
    
    # 2. 자치구별 업종 분포 히트맵
    with st.expander("🗺️ 자치구별 업종 분포 히트맵", expanded=True):
        st.subheader("자치구별 업종 분포 히트맵")
        
        # 피벗 테이블 생성 (상위 10개 업종만)
        top_industries = df['industry_code'].value_counts().head(10).index
        heatmap_data = df[df['industry_code'].isin(top_industries)].pivot_table(
            index='district', columns='industry_code', aggfunc='size', fill_value=0
        )
        
        # 자치구 이름에서 '기타' 제외
        heatmap_data = heatmap_data[heatmap_data.index != '기타']
        
        if not heatmap_data.empty:
            fig, ax = plt.subplots(figsize=(14, 10))
            sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlOrRd', 
                       ax=ax, cbar_kws={'label': '가맹점 수'})
            ax.set_title('자치구별 업종 분포 히트맵 (상위 10개 업종)', fontsize=16, fontweight='bold')
            ax.set_xlabel('업종코드')
            ax.set_ylabel('자치구')
            plt.xticks(rotation=45)
            plt.yticks(rotation=0)
            plt.tight_layout()
            st.pyplot(fig)
            
            # 업종코드 설명
            st.markdown("**📋 업종코드 설명**")
            for code in top_industries:
                st.write(f"• **{code}**: {get_industry_name(code)}")
    
    # 3. 자치구별 업종 다양성 지수 (Entropy)
    with st.expander("🔍 자치구별 업종 다양성 지수", expanded=True):
        st.subheader("자치구별 업종 다양성 지수 (엔트로피)")
        st.markdown("💡 **다양성 지수가 높을수록 업종이 고르게 분포되어 있음을 의미합니다.**")
        
        diversity_scores = df[df['district'] != '기타'].groupby('district')['industry_code'].apply(calculate_diversity_index).sort_values(ascending=False)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.bar(range(len(diversity_scores)), diversity_scores.values, 
                     color=plt.cm.viridis(np.linspace(0, 1, len(diversity_scores))))
        ax.set_xticks(range(len(diversity_scores)))
        ax.set_xticklabels(diversity_scores.index, rotation=45, ha='right')
        ax.set_ylabel('다양성 지수 (엔트로피)')
        ax.set_title('자치구별 업종 다양성 지수', fontsize=16, fontweight='bold')
        
        # 값 표시
        for bar, score in zip(bars, diversity_scores.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                   f'{score:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # 상위/하위 3개 구 요약
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🏆 다양성 상위 3개 구**")
            for i, (district, score) in enumerate(diversity_scores.head(3).items(), 1):
                st.write(f"{i}. **{district}**: {score:.2f}")
        
        with col2:
            st.markdown("**🎯 특화도 상위 3개 구** (다양성 하위)")
            for i, (district, score) in enumerate(diversity_scores.tail(3).items(), 1):
                st.write(f"{i}. **{district}**: {score:.2f}")
    
    # 4. 자치구별 전체 가맹점 수 비교
    with st.expander("📊 자치구별 전체 가맹점 수", expanded=True):
        st.subheader("자치구별 전체 가맹점 수 비교")
        
        district_counts = df[df['district'] != '기타']['district'].value_counts()
        
        fig, ax = plt.subplots(figsize=(14, 8))
        bars = ax.bar(range(len(district_counts)), district_counts.values, 
                     color=plt.cm.tab20(np.linspace(0, 1, len(district_counts))))
        ax.set_xticks(range(len(district_counts)))
        ax.set_xticklabels(district_counts.index, rotation=45, ha='right')
        ax.set_ylabel('가맹점 수')
        ax.set_title('자치구별 전체 가맹점 수', fontsize=16, fontweight='bold')
        
        # 값 표시
        for bar, count in zip(bars, district_counts.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(district_counts.values) * 0.01,
                   f'{count:,}', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # 통계 요약
        st.markdown("**📈 가맹점 수 통계**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🥇 최다 가맹점 구", f"{district_counts.index[0]}", f"{district_counts.iloc[0]:,}개")
        with col2:
            st.metric("📊 평균 가맹점 수", f"{district_counts.mean():.0f}개")
        with col3:
            total_shops = district_counts.sum()
            st.metric("🏪 서울시 총 가맹점", f"{total_shops:,}개")
    
    # 5. 특정 업종(음식점/식음료업)의 자치구별 집중도
    with st.expander("🍽️ 음식점/식음료업 자치구별 집중도", expanded=True):
        st.subheader("음식점/식음료업(A01) 자치구별 분포")
        
        restaurant_data = df[df['industry_code'] == 'A01']
        if not restaurant_data.empty:
            restaurant_by_district = restaurant_data[restaurant_data['district'] != '기타']['district'].value_counts()
            total_by_district = df[df['district'] != '기타']['district'].value_counts()
            
            # 비율 계산
            restaurant_ratio = (restaurant_by_district / total_by_district * 100).fillna(0).sort_values(ascending=False)
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 절대 수량
            bars1 = ax1.bar(range(len(restaurant_by_district)), restaurant_by_district.values, 
                           color=plt.cm.Reds(np.linspace(0.3, 1, len(restaurant_by_district))))
            ax1.set_xticks(range(len(restaurant_by_district)))
            ax1.set_xticklabels(restaurant_by_district.index, rotation=45, ha='right')
            ax1.set_ylabel('음식점 수')
            ax1.set_title('자치구별 음식점 수 (절대값)', fontweight='bold')
            
            for bar, count in zip(bars1, restaurant_by_district.values):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(restaurant_by_district.values) * 0.01,
                        f'{count}', ha='center', va='bottom', fontsize=9)
            
            # 비율
            bars2 = ax2.bar(range(len(restaurant_ratio)), restaurant_ratio.values, 
                           color=plt.cm.Oranges(np.linspace(0.3, 1, len(restaurant_ratio))))
            ax2.set_xticks(range(len(restaurant_ratio)))
            ax2.set_xticklabels(restaurant_ratio.index, rotation=45, ha='right')
            ax2.set_ylabel('음식점 비율 (%)')
            ax2.set_title('자치구별 음식점 비율 (%)', fontweight='bold')
            
            for bar, ratio in zip(bars2, restaurant_ratio.values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(restaurant_ratio.values) * 0.01,
                        f'{ratio:.1f}%', ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            st.pyplot(fig)
            
            # 상위 5개 구 요약
            st.markdown("**🍽️ 음식점 집중도 상위 5개 구**")
            for i, (district, ratio) in enumerate(restaurant_ratio.head(5).items(), 1):
                absolute_count = restaurant_by_district.get(district, 0)
                st.write(f"{i}. **{district}**: {ratio:.1f}% ({absolute_count}개)")
        else:
            st.warning("음식점/식음료업 데이터가 없습니다.")
    
    # 6. 자치구별 의료 vs 비의료 업종 비율 분석
    with st.expander("🏥 자치구별 의료 vs 비의료 업종 비율", expanded=True):
        st.subheader("자치구별 의료/복지 업종 vs 기타 업종 비율")
        st.markdown("💡 **의료/복지 분류 기준**: 업종코드 A03 또는 상호명에 '의료', '복지', '병원', '약국' 등 키워드 포함")
        
        # 의료/비의료 분류
        df['is_medical'] = df.apply(lambda row: is_medical_industry(row['industry_code'], row['store_name']), axis=1)
        
        # 자치구별 의료/비의료 집계
        medical_analysis = df[df['district'] != '기타'].groupby('district')['is_medical'].agg(['count', 'sum']).reset_index()
        medical_analysis['medical_ratio'] = medical_analysis['sum'] / medical_analysis['count'] * 100
        medical_analysis['non_medical'] = medical_analysis['count'] - medical_analysis['sum']
        medical_analysis = medical_analysis.sort_values('medical_ratio', ascending=False)
        
        if not medical_analysis.empty:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 스택 바 차트
            districts = medical_analysis['district']
            medical_counts = medical_analysis['sum']
            non_medical_counts = medical_analysis['non_medical']
            
            bars1 = ax1.bar(districts, medical_counts, label='의료/복지', color='lightcoral')
            bars2 = ax1.bar(districts, non_medical_counts, bottom=medical_counts, label='기타 업종', color='lightblue')
            
            ax1.set_ylabel('가맹점 수')
            ax1.set_title('자치구별 의료/복지 vs 기타 업종 분포', fontweight='bold')
            ax1.legend()
            ax1.tick_params(axis='x', rotation=45)
            
            # 비율 차트
            bars3 = ax2.bar(districts, medical_analysis['medical_ratio'], 
                           color=plt.cm.RdYlBu_r(np.linspace(0, 1, len(districts))))
            ax2.set_ylabel('의료/복지 업종 비율 (%)')
            ax2.set_title('자치구별 의료/복지 업종 비율', fontweight='bold')
            ax2.tick_params(axis='x', rotation=45)
            
            # 비율 값 표시
            for bar, ratio in zip(bars3, medical_analysis['medical_ratio']):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{ratio:.1f}%', ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            st.pyplot(fig)
            
            # 통계 요약
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🏥 의료/복지 비율 상위 5개 구**")
                for i, row in medical_analysis.head(5).iterrows():
                    st.write(f"{i+1}. **{row['district']}**: {row['medical_ratio']:.1f}% ({int(row['sum'])}개)")
            
            with col2:
                total_medical = medical_analysis['sum'].sum()
                total_all = medical_analysis['count'].sum()
                overall_ratio = total_medical / total_all * 100
                st.markdown("**📊 전체 통계**")
                st.write(f"• 전체 의료/복지 업종: {total_medical:,}개")
                st.write(f"• 전체 기타 업종: {total_all - total_medical:,}개")
                st.write(f"• 서울시 평균 의료/복지 비율: {overall_ratio:.1f}%")
        else:
            st.warning("의료/복지 업종 분석 데이터가 없습니다.")
    
    # 분석 완료 메시지
    st.success("✅ 모든 통계 분석이 완료되었습니다!")
    st.markdown("---")
    st.markdown("📈 **분석 요약**: 서울시 민생회복 소비쿠폰 사용처 데이터를 통해 업종별, 지역별 분포 현황을 다각도로 분석했습니다.")