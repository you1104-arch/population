import requests
import plotly.express as px

st.set_page_config(page_title="2026 전국 고령화 단계구분도", layout="wide")
st.title("2026년 전국 시군구별 고령화율(65세 이상 비율) 단계구분도")
st.set_page_config(page_title="2026 서울 행정동 고령화 단계구분도", layout="wide")
st.title("2026년 서울특별시 행정동별 고령화율 분석")

# 1. GeoJSON 로드 (GitHub raw URL)
GEOJSON_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/sigungu_kr.geojson.txt"
# 1. 서울 행정동 GeoJSON 로드 (코드, 구, 동 속성 포함)
GEOJSON_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/seoul_dong.geojson"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    return res.json()
    data = res.json()

    # GeoJSON properties 내 코드 정규화
    for f in data.get("features", []):
        props = f.get("properties", {})
        code_val = props.get("코드") or props.get("adm_cd") or props.get("adm_cd8") or ""
        props["코드"] = str(code_val).strip()
    return data

# 2. 인구 데이터 로드 및 65세 이상 고령화율 계산
# 2. 인구 데이터 로드 및 서울 행정동별 65세 이상 비율 계산
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    # 판다스로 압축 zip 내 CSV 직접 로드
    df = pd.read_csv(POP_URL, dtype={"코드": str})
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")

    df.columns = df.columns.str.strip()

    # 2026년 데이터 필터링
    df = df[df["연도"] == 2026].copy()

    # 읍면동 코드를 앞 5자리(시군구 코드)로 추출
    df["시군구코드"] = df["코드"].astype(str).str[:5]
    if "연도" in df.columns:
        df["연도_clean"] = df["연도"].astype(str).str.replace("년", "").str.strip()
        df_year = df[df["연도_clean"] == "2026"].copy()
    else:
        st.error("'연도' 열을 찾을 수 없습니다.")
        return pd.DataFrame()

    if df_year.empty:
        st.error("2026년 인구 데이터가 없습니다.")
        return pd.DataFrame()

    # 서울(시도) 필터링
    if "시도" in df_year.columns:
        df_seoul = df_year[df_year["시도"].astype(str).str.contains("서울")].copy()
    else:
        st.error("'시도' 열을 찾을 수 없습니다.")
        return pd.DataFrame()

    if df_seoul.empty:
        st.error("2026년 서울 데이터가 없습니다.")
        return pd.DataFrame()

    # 코드 정리
    df_seoul["원래코드"] = df_seoul["코드"].astype(str).str.strip()

    # 전체 인구: '계_'로 시작하는 모든 열의 합
    total_cols = [c for c in df.columns if c.startswith("계_")]
    # 전체 인구: '계_'로 시작하는 열 (남_, 여_ 제외)
    total_cols = [c for c in df_seoul.columns if c.startswith("계_")]

    # 65세 이상 열: '계_65세' ~ '계_99세' 및 '계_100세 이상'
    # 65세 이상 열 선별 ('계_65세' ~ '계_100세 이상')
    elderly_cols = []
    for c in total_cols:
        age_str = c.replace("계_", "").replace("세", "")
        if "이상" in age_str:
        cleaned = c.replace("계_", "").replace("세", "").strip()
        if "이상" in cleaned:
            elderly_cols.append(c)
        else:
            try:
                age_val = int(age_str)
                if age_val >= 65:
                if int(cleaned) >= 65:
                    elderly_cols.append(c)
            except ValueError:
                pass

    # 시군구 단위 인구 합산
    agg_df = df.groupby("시군구코드")[total_cols].sum().reset_index()
    # 숫자형 변환 (쉼표 및 공백 제거)
    for c in total_cols:
        df_seoul[c] = pd.to_numeric(
            df_seoul[c].astype(str).str.replace(",", "").str.strip(), 
            errors="coerce"
        ).fillna(0)

    # 코드별 합산
    agg_df = df_seoul.groupby("원래코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg_df["고령인구"] = agg_df[elderly_cols].sum(axis=1)

    # 고령화율(%) 계산 (0으로 나누기 방지)
    # 고령화율(%) 계산
    agg_df["고령화율"] = (agg_df["고령인구"] / agg_df["총인구"].replace(0, float("nan"))) * 100
    agg_df["고령화율"] = agg_df["고령화율"].round(2)

    return agg_df

with st.spinner("데이터를 불러오는 중입니다..."):
with st.spinner("서울시 행정동 데이터를 로딩 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_and_process_data()

# 3. 단계구분도 시각화 (배경 지도 타일 없이 경계선만 표시)
fig = px.choropleth(
    pop_df,
    geojson=geojson_data,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    hover_name=pop_df["시군구코드"],
    labels={"고령화율": "고령화율(%)", "시군구코드": "코드"}
)

# GeoJSON의 properties.시군구 속성을 마우스 오버 텍스트에 매핑
fig.update_traces(
    customdata=pop_df[["고령화율"]],
    hovertemplate="<b>%{properties.시도} %{properties.시군구}</b><br>코드: %{properties.코드}<br>고령화율: %{z:.2f}%<extra></extra>"
)

# 배경 타일 및 투영 영역 설정 (한반도 중심)
fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    coloraxis_colorbar=dict(
        title="고령화율(%)",
        ticksuffix="%"
    )
)

st.plotly_chart(fig, use_container_width=True)
if pop_df.empty:
    st.stop()

# 3. GeoJSON 코드와 인구 데이터 코드 매칭 정규화 (8자리 vs 10자리 자동 일치)
geo_features = geojson_data.get("features", [])
geo_codes = [str(f.get("properties", {}).get("코드", "")).strip() for f in geo_features if f.get("properties", {}).get("코드")]
sample_geo_len = len(geo_codes[0]) if geo_codes else 10
sample_pop_len = len(str(pop_df["원래코드"].iloc[0])) if not pop_df.empty else 10

# 짧은 자릿수(통상 8자리 또는 10자리)에 맞춰 조율
match_len = min(sample_geo_len, sample_pop_len)
if match_len < 8:
    match_len = 8

pop_df["매칭코드"] = pop_df["원래코드"].str[:match_len]

for f in geo_features:
    props = f.get("properties", {})
    props["매칭코드"] = str(props.get("코드", "")).strip()[:match_len]

# GeoJSON의 구, 동 이름
Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
