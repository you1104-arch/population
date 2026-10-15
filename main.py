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
시도, 시군구, 읍·면·동을 차례대로 선택해 **가장 최신 연도 기준의 인구 분포**를 한눈에 살펴보세요.
""")
st.divider()

# ---------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 (캐싱 활용)
# ---------------------------------------------------------
@st.cache_data(show_spinner="전국 인구 데이터를 불러오는 중입니다. 잠시만 기다려주세요...")
def load_data():
    # GitHub raw 파일 링크로 바로 연결하여 판다스로 읽어옵니다. (zip 압축 파일 자동 해제)
    # ?raw=true를 붙여 웹 브라우저 뷰어가 아닌 순수 파일 바이너리로 전달합니다.
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
# 5. 선택한 동네의 인구 데이터 추출
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

    for age in age_labels:
        male_val = target_row.get(f"남_{age}", 0)
        female_val = target_row.get(f"여_{age}", 0)
        
        # 결측값(NaN) 처리
        male_val = 0 if pd.isna(male_val) else male_val
        female_val = 0 if pd.isna(female_val) else female_val
        
        # 남성은 음수값으로 변환하여 왼쪽 방향으로 표시
        male_pop.append(-abs(male_val))
        female_pop.append(abs(female_val))

    total_pop = sum(abs(m) for m in male_pop) + sum(female_pop)

    # 상단 요약 배너 표시
    st.markdown("---")
    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("기준 연도", f"{latest_year}년")
    info_col2.metric("선택 지역", f"{selected_sido} {selected_sigungu} {selected_dong}")
    info_col3.metric("총 인구수", f"{int(total_pop):,}명")

    # ---------------------------------------------------------
    # 6. Plotly 인구 피라미드 가로 막대그래프 생성
    # ---------------------------------------------------------
    fig = go.Figure()

    # 남성 막대 (왼쪽, 음수) - 따뜻하고 차분한 소프트 블루 톤
    fig.add_trace(go.Bar(
        y=age_labels,
        x=male_pop,
        name='남성',
        orientation='h',
        marker=dict(color='#5B84B1'),
        hoverinfo='text',
        # 마우스 오버 시 표시할 텍스트 (양수 형태와 명 단위 표기)
        hovertext=[f"남성 {age}: {abs(val):,}명" for age, val in zip(age_labels, male_pop)]
    ))

    # 여성 막대 (오른쪽, 양수) - 따뜻하고 포근한 코랄 로즈 톤
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
    # 여유 간격을 두어 시각적 여백 확보
    limit = max_val * 1.1

    # ---------------------------------------------------------
    # 7. 축 및 레이아웃 설정 (세로축 순서 엄격 고정)
    # ---------------------------------------------------------
    fig.update_layout(
        title={
            'text': f"<b>[{selected_dong}] 연령별 인구 피라미드 ({latest_year}년 기준)</b>",
            'x': 0.5,
            'xanchor': 'center'
        },
        barmode='overlay',
        bargap=0.1,
        height=950,
        plot_bgcolor='rgba(250, 250, 250, 0.9)',
        paper_bgcolor='rgba(0,0,0,0)',
        # [핵심] 세로축: 뒤집기나 크기순 정렬 없이, 0세부터 100세 이상 순서 목록 그대로 고정
        yaxis=dict(
            title="연령",
            type='category',
            categoryorder='array',
            categoryarray=age_labels,  # 맨 아래가 0세, 맨 위가 100세 이상으로 고정 배치
            showgrid=True,
            gridcolor='#EAEAEA',
            tickfont=dict(size=11),
            dtick=5  # 5세 단위로 눈금 라벨 표시 (가독성 향상)
        ),
        # 가로축: 음수로 표시된 남성 쪽 눈금도 양수로 보이도록 설정
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

    st.caption("💡 팁: 그래프의 막대에 마우스 커서를 올리면 해당 연령의 정확한 인구수를 확인할 수 있습니다.")
