import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="2026 전국 고령화 단계구분도", layout="wide")
st.title("2026년 전국 시군구별 고령화율(65세 이상 비율) 단계구분도")

# 1. GeoJSON 로드 (GitHub raw URL)
GEOJSON_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/sigungu_kr.geojson.txt"


@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    return res.json()


# 2. 인구 데이터 로드 및 65세 이상 고령화율 계산
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"


@st.cache_data
def load_and_process_data():
    # 판다스로 압축 zip 내 CSV 직접 로드
    df = pd.read_csv(POP_URL, dtype={"코드": str})

    # 2026년 데이터 필터링
    df = df[df["연도"] == 2026].copy()

    # 읍면동 코드를 앞 5자리(시군구 코드)로 추출
    df["시군구코드"] = df["코드"].astype(str).str[:5]

    # 전체 인구: '계_'로 시작하는 모든 열의 합
    total_cols = [c for c in df.columns if c.startswith("계_")]

    # 65세 이상 열: '계_65세' ~ '계_99세' 및 '계_100세 이상'
    elderly_cols = []
    for c in total_cols:
        age_str = c.replace("계_", "").replace("세", "")
        if "이상" in age_str:
            elderly_cols.append(c)
        else:
            try:
                age_val = int(age_str)
                if age_val >= 65:
                    elderly_cols.append(c)
            except ValueError:
                pass

    # 시군구 단위 인구 합산
    agg_df = df.groupby("시군구코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg_df["고령인구"] = agg_df[elderly_cols].sum(axis=1)

    # 고령화율(%) 계산 (0으로 나누기 방지)
    agg_df["고령화율"] = (
        agg_df["고령인구"] / agg_df["총인구"].replace(0, float("nan"))
    ) * 100
    agg_df["고령화율"] = agg_df["고령화율"].round(2)

    return agg_df


with st.spinner("데이터를 불러오는 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_and_process_data()

# GeoJSON 정보 추출하여 행정구역 이름 매핑 (시도, 시군구)
geo_properties = []
for feature in geojson_data["features"]:
    props = feature["properties"]
    geo_properties.append(
        {
            "시군구코드": str(props.get("코드", "")),
            "시도명": props.get("시도", ""),
            "시군구명": props.get("시군구", ""),
        }
    )
geo_df = pd.DataFrame(geo_properties).drop_duplicates(subset=["시군구코드"])

# 데이터 프레임 병합
full_df = pd.merge(pop_df, geo_df, on="시군구코드", how="left")
full_df["시도명"] = full_df["시도명"].fillna("미분류")
full_df["시군구명"] = full_df["시군구명"].fillna("")
full_df["지역명"] = (full_df["시도명"] + " " + full_df["시군구명"]).str.strip()

# --- [전국 순위 계산] ---
full_df["전국순위"] = (
    full_df["고령화율"].rank(ascending=False, method="min").astype(int)
)
total_regions = len(full_df)

# --- [기능 추가] 우리 동네 검색 및 현실 비유 카드 ---
st.markdown("---")
st.subheader("🏫 우리 동네 고령화 체감 체커")

# 시도 및 시군구 선택 드롭다운
search_col1, search_col2 = st.columns(2)

with search_col1:
    sido_options = sorted(
        [s for s in full_df["시도명"].unique() if s != "미분류"]
    )
    selected_search_sido = st.selectbox(
        "📍 시/도 선택", sido_options, key="search_sido"
    )

with search_col2:
    sigungu_options = sorted(
        full_df[full_df["시도명"] == selected_search_sido][
            "시군구명"
        ].unique()
    )
    selected_search_sigungu = st.selectbox("🏘️ 시/군/구 선택", sigungu_options)

# 선택 지역 데이터 추출
target_row = full_df[
    (full_df["시도명"] == selected_search_sido)
    & (full_df["시군구명"] == selected_search_sigungu)
].iloc[0]

target_name = target_row["지역명"]
target_rate = target_row["고령화율"]
target_rank = target_row["전국순위"]
target_total_pop = target_row["총인구"]

# 30명 학급 기준 어르신 수 계산
class_elderly = round(target_rate * 0.3, 1)

# 메트릭 카드로 주요 정보 표시
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("📍 선택 지역", target_name)
m_col2.metric("👵 고령화율", f"{target_rate:.2f}%")
m_col3.metric("🏆 전국 순위", f"{target_rank}위 / {total_regions}개")
m_col4.metric("👥 총인구수", f"{target_total_pop:,}명")

# 고령화 단계 구분 및 학생 비유 메시지 상자
if target_rate >= 20.0:
    st.error(
        f"🚨 **[{target_name}]은(는) '초고령사회' 단계입니다!**\n\n"
        f"🏫 **학급으로 비유하자면:** 우리 반 학생이 30명이라면, 그중 **약 {class_elderly}명**이 65세 이상 어르신에 해당합니다. "
        f"지역 내 어르신 비중이 매우 높아 돌봄 서비스와 시니어 복지 시설이 중요하게 필요한 지역입니다."
    )
elif target_rate >= 14.0:
    st.warning(
        f"⚠️ **[{target_name}]은(는) '고령사회' 단계입니다.**\n\n"
        f"🏫 **학급으로 비유하자면:** 우리 반 학생이 30명이라면, 그중 **약 {class_elderly}명**이 65세 이상 어르신에 해당합니다. "
        f"초고령사회 진입을 앞두고 있어 젊은 세대와 어르신이 함께 공존하는 정책 준비가 활발한 지역입니다."
    )
else:
    st.info(
        f"ℹ️ **[{target_name}]은(는) '고령화사회/일반' 단계입니다.**\n\n"
        f"🏫 **학급으로 비유하자면:** 우리 반 학생이 30명이라면, 그중 **약 {class_elderly}명**이 65세 이상 어르신에 해당합니다. "
        f"상대적으로 청장년층 인구 비중이 높은 편이지만, 향후 고령화 속도에 맞춘 지속적인 관심이 필요합니다."
    )

st.markdown("---")

# --- [기능 1] 사이드바 시/도 필터링 ---
st.sidebar.header("🔍 지도 필터링")
sido_list = ["전국"] + sorted(
    [s for s in full_df["시도명"].unique() if s != "미분류"]
)
selected_sido = st.sidebar.selectbox("시/도 선택", sido_list)

if selected_sido != "전국":
    filtered_df = full_df[full_df["시도명"] == selected_sido].copy()
else:
    filtered_df = full_df.copy()

# 3. 단계구분도 시각화
fig = px.choropleth(
    filtered_df,
    geojson=geojson_data,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    hover_name="지역명",
    hover_data={
        "시군구코드": True,
        "총인구": ":,",
        "고령인구": ":,",
        "고령화율": ":.2f",
        "전국순위": True,
    },
    labels={
        "고령화율": "고령화율(%)",
        "시군구코드": "행정코드",
        "총인구": "총 인구 수",
        "고령인구": "65세 이상 인구",
        "전국순위": "전국 순위",
    },
)

# 배경 타일 및 투영 영역 설정
fig.update_geos(fitbounds="locations", visible=False)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    coloraxis_colorbar=dict(title="고령화율(%)", ticksuffix="%"),
)

st.plotly_chart(fig, use_container_width=True)

# --- [기능 2] Top 5 및 Bottom 5 시군구 막대그래프 ---
st.markdown("---")
st.subheader(f"📊 {selected_sido} 기준 고령화율 상위/하위 시군구")

col1, col2 = st.columns(2)

# Top 5 시군구 (고령화율 높은 순)
with col1:
    st.markdown("##### 🔴 고령화율 상위 Top 5")
    top5_df = filtered_df.sort_values(by="고령화율", ascending=False).head(5)

    fig_top = px.bar(
        top5_df,
        x="고령화율",
        y="지역명",
        orientation="h",
        text="고령화율",
        color="고령화율",
        color_continuous_scale="Reds",
        labels={"고령화율": "고령화율(%)", "지역명": "지역"},
    )
    fig_top.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig_top.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
        height=300,
        margin={"r": 30, "t": 20, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_top, use_container_width=True)

# Bottom 5 시군구 (고령화율 낮은 순)
with col2:
    st.markdown("##### 🔵 고령화율 하위 Bottom 5")
    bottom5_df = filtered_df.sort_values(by="고령화율", ascending=True).head(5)

    fig_bottom = px.bar(
        bottom5_df,
        x="고령화율",
        y="지역명",
        orientation="h",
        text="고령화율",
        color="고령화율",
        color_continuous_scale="Blues_r",
        labels={"고령화율": "고령화율(%)", "지역명": "지역"},
    )
    fig_bottom.update_traces(
        texttemplate="%{text:.2f}%", textposition="outside"
    )
    fig_bottom.update_layout(
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
        height=300,
        margin={"r": 30, "t": 20, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_bottom, use_container_width=True)
