import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import warnings
import platform

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