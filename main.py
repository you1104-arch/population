import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 페이지 기본 설정 및 디자인
# ---------------------------------------------------------
st.set_page_config(
    page_title="우리 동네 인구 피라미드",
    page_icon="👥",
    layout="wide"
)

# 따뜻하고 편안한 톤의 스타일 적용
st.title("🏡 우리 동네 인구 피라미드")
st.markdown("""
우리 동네에는 어떤 연령대의 이웃들이 함께 살아가고 있을까요?  
시도, 시군구, 읍·면·동을 차례대로 선택해 **가장 최신 연도 기준의 인구 분포**와 **동네의 주요 인구 지표**를 한눈에 살펴보세요.
""")
st.divider()

# ---------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 (캐싱 활용)
# ---------------------------------------------------------
@st.cache_data(show_spinner="전국 인구 데이터를 불러오는 중입니다. 잠시만 기다려주세요...")
def load_data():
    # GitHub raw 파일 링크로 바로 연결하여 판다스로 읽어옵니다. (zip 압축 파일 자동 해제)
    url = "https://github.com/you1104-arch/population/blob/main/population_ts_yearly_gender.zip?raw=true"
    
    # CSV 데이터 로드
    df = pd.read_csv(url, compression='zip')
    
    # 가장 최신 연도만 선택
    latest_year = df['연도'].max()
    df_latest = df[df['연도'] == latest_year].copy()
    
    return df_latest, latest_year

# 데이터 로드 실행
data, latest_year = load_data()

# ---------------------------------------------------------
# 3. 나이 라벨 리스트 생성 (0세 ~ 100세 이상)
# ---------------------------------------------------------
# 0세부터 99세까지 + 100세 이상 순서 목록
age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

# ---------------------------------------------------------
# 4. 동네 선택 드롭다운 (시도 → 시군구 → 동)
# ---------------------------------------------------------
st.subheader("📍 확인하고 싶은 지역을 골라주세요")

col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(data['시도'].dropna().unique())
    selected_sido = st.selectbox("1. 시·도 선택", sido_list)

with col2:
    # 선택된 시도에 속한 시군구 목록 추출
    sigungu_list = sorted(data[data['시도'] == selected_sido]['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("2. 시·군·구 선택", sigungu_list)

with col3:
    # 선택된 시군구에 속한 읍·면·동 목록 추출
    dong_list = sorted(
        data[(data['시도'] == selected_sido) & (data['시군구'] == selected_sigungu)]['동'].dropna().unique()
    )
    selected_dong = st.selectbox("3. 읍·면·동 선택", dong_list)

# ---------------------------------------------------------
# 5. 선택한 동네의 인구 데이터 추출 및 지표 계산
# ---------------------------------------------------------
row_data = data[
    (data['시도'] == selected_sido) & 
    (data['시군구'] == selected_sigungu) & 
    (data['동'] == selected_dong)
]

if row_data.empty:
    st.warning("선택하신 동네의 인구 데이터가 존재하지 않습니다. 다른 지역을 선택해주세요.")
else:
    target_row = row_data.iloc[0]

    # 각 나이별 남/여 인구수 추출
    # 남자는 왼쪽(음수), 여자는 오른쪽(양수)
    male_pop = []
    female_pop = []
    
    # 주요 인구 통계 계산용 변수
    total_population = 0
    weighted_age_sum = 0
    child_pop = 0     # 유소년 인구 (0 ~ 14세)
    elderly_pop = 0   # 고령 인구 (65세 이상)

    for idx, age in enumerate(age_labels):
        male_val = target_row.get(f"남_{age}", 0)
        female_val = target_row.get(f"여_{age}", 0)
        
        # 결측값(NaN) 처리
        male_val = 0 if pd.isna(male_val) else male_val
        female_val = 0 if pd.isna(female_val) else female_val
        
        # 남성은 음수로 변환하여 왼쪽 방향으로 표시
        male_pop.append(-abs(male_val))
        female_pop.append(abs(female_val))
        
        # 해당 나이 합산 인구
        sum_pop = abs(male_val) + abs(female_val)
        total_population += sum_pop
        
        # 나이 대표값 (100세 이상은 100으로 가중합 계산)
        numeric_age = 100 if idx == 100 else idx
        weighted_age_sum += (numeric_age * sum_pop)
        
        # 연령대별 인구 집계
        if numeric_age <= 14:
            child_pop += sum_pop
        elif numeric_age >= 65:
            elderly_pop += sum_pop

    # 지표 계산 (0으로 나누기 방지)
    avg_age = (weighted_age_sum / total_population) if total_population > 0 else 0
    aging_rate = (elderly_pop / total_population * 100) if total_population > 0 else 0
    child_rate = (child_pop / total_population * 100) if total_population > 0 else 0

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. 상단 지표 카드 3개 나란히 배치
    # ---------------------------------------------------------
    metric_col1, metric_col2, metric_col3 = st.columns(3)

    # 1) 총인구
    with metric_col1:
        st.metric(
            label="👥 총인구",
            value=f"{int(total_population):,}명",
            help=f"{latest_year}년 기준 해당 지역의 전체 거주 인구수입니다."
        )

    # 2) 평균연령
    with metric_col2:
        st.metric(
            label="🎂 평균연령",
            value=f"{avg_age:.1f}세",
            help="해당 지역 주민들의 가중 평균 나이입니다."
        )

    # 3) 고령화율 (65세 이상 비율) + 20% 초과 시 주의 표시
    with metric_col3:
        if aging_rate >= 20.0:
            st.metric(
                label="👵 고령화율 (65세 이상)",
                value=f"{aging_rate:.1f}%",
                delta="⚠️ 초고령사회 주의 (20% 이상)",
                delta_color="inverse",
                help="전체 인구 중 65세 이상 어르신 비율이 20%를 넘어 초고령사회에 해당합니다."
            )
        else:
            st.metric(
                label="👵 고령화율 (65세 이상)",
                value=f"{aging_rate:.1f}%",
                help="전체 인구 중 65세 이상 어르신이 차지하는 비율입니다."
            )

    # ---------------------------------------------------------
    # 7. Plotly 인구 피라미드 가로 막대그래프 생성
    # ---------------------------------------------------------
    fig = go.Figure()

    # 남성 막대 (왼쪽, 음수) - 부드러운 소프트 블루 톤
    fig.add_trace(go.Bar(
        y=age_labels,
        x=male_pop,
        name='남성',
        orientation='h',
        marker=dict(color='#5B84B1'),
        hoverinfo='text',
        hovertext=[f"남성 {age}: {abs(val):,}명" for age, val in zip(age_labels, male_pop)]
    ))

    # 여성 막대 (오른쪽, 양수) - 따뜻한 코랄 로즈 톤
    fig.add_trace(go.Bar(
        y=age_labels,
        x=female_pop,
        name='여성',
        orientation='h',
        marker=dict(color='#FC766A'),
        hoverinfo='text',
        hovertext=[f"여성 {age}: {val:,}명" for age, val in zip(age_labels, female_pop)]
    ))

    # X축(가로축) 대칭 범위 설정
    max_val = max(max(abs(m) for m in male_pop), max(female_pop), 10)
    limit = max_val * 1.1

    # ---------------------------------------------------------
    # 8. 축 및 레이아웃 설정 (세로축 순서 엄격 고정)
    # ---------------------------------------------------------
    fig.update_layout(
        title={
            'text': f"<b>[{selected_sido} {selected_sigungu} {selected_dong}] 연령별 인구 피라미드 ({latest_year}년)</b>",
            'x': 0.5,
            'xanchor': 'center'
        },
        barmode='overlay',
        bargap=0.1,
        height=950,
        plot_bgcolor='rgba(250, 250, 250, 0.9)',
        paper_bgcolor='rgba(0,0,0,0)',
        # [핵심] 세로축: 0세부터 100세 이상 순서 목록 그대로 고정 (아래에서 위로 증가)
        yaxis=dict(
            title="연령",
            type='category',
            categoryorder='array',
            categoryarray=age_labels,
            showgrid=True,
            gridcolor='#EAEAEA',
            tickfont=dict(size=11),
            dtick=5  # 5세 단위로 눈금 라벨 표시
        ),
        # 가로축: 음수로 표시된 남성 쪽 눈금도 양수로 표기
        xaxis=dict(
            title="인구수 (명)",
            range=[-limit, limit],
            showgrid=True,
            gridcolor='#EAEAEA',
            tickvals=[-int(limit*0.75), -int(limit*0.5), -int(limit*0.25), 0, int(limit*0.25), int(limit*0.5), int(limit*0.75)],
            ticktext=[f"{abs(int(v)):,}" for v in [-int(limit*0.75), -int(limit*0.5), -int(limit*0.25), 0, int(limit*0.25), int(limit*0.5), int(limit*0.75)]]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=13)
        ),
        margin=dict(l=60, r=60, t=80, b=50)
    )

    # 그래프 렌더링
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # 9. 피라미드 아래 한 줄 설명 (아이 vs 어르신 비율 분석)
    # ---------------------------------------------------------
    st.markdown("#### 💬 이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?")
    
    # 유소년(0~14세)과 고령자(65세 이상) 비율 비교
    if child_rate > elderly_pop and child_pop > 0:
        desc_text = f"🧒 **{selected_dong}**은(는) 유소년(0~14세, **{child_rate:.1f}%**) 비율이 65세 이상 어르신(**{aging_rate:.1f}%**)보다 높아, **어린이와 청소년의 활기가 넘치는 젊은 동네**입니다."
    elif elderly_pop > child_pop and abs(elderly_pop - child_pop) / total_population > 0.05:
        desc_text = f"🧓 **{selected_dong}**은(는) 65세 이상 어르신 비율(**{aging_rate:.1f}%**)이 유소년(0~14세, **{child_rate:.1f}%**)보다 확연히 높아, **어르신 맞춤형 돌봄과 복지 인프라가 중요한 동네**입니다."
    else:
        desc_text = f"⚖️ **{selected_dong}**은(는) 유소년(**{child_rate:.1f}%**)과 어르신(**{aging_rate:.1f}%**)의 비중이 비교적 조화를 이루고 있는 동네입니다."

    st.info(desc_text)
    st.caption("💡 팁: 그래프의 막대에 마우스 커서를 올리면 해당 연령의 정확한 인구수를 확인할 수 있습니다.")
