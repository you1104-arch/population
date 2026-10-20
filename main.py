import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 전국 고령화 단계구분도", layout="wide")
st.title("2026년 전국 시군구별 고령화율 기준선 분석")

# 1. GeoJSON 로드 (raw URL)
GEOJSON_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/sigungu_kr.geojson.txt"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    data = res.json()
    # GeoJSON properties 내 코드를 문자열 5자리로 정규화
    for f in data.get("features", []):
        if "properties" in f and "코드" in f["properties"]:
            f["properties"]["코드"] = str(f["properties"]["코드"]).strip()[:5]
    return data

# 2. 인구 데이터 로드 및 전처리
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")
        
    df.columns = df.columns.str.strip()
    
    if "연도" not in df.columns:
        st.error(f"'연도' 열을 찾을 수 없습니다. 컬럼 목록: {list(df.columns[:10])}")
        return pd.DataFrame()

    # 연도 컬럼의 공백 제거 및 2026년 필터링 (숫자형 또는 문자열 모두 안전하게 처리)
    df["연도_정리"] = df["연도"].astype(str).str.strip().str[:4]
    df_2026 = df[df["연도_정리"] == "2026"].copy()

    if df_2026.empty:
        years_found = df["연도_정리"].unique().tolist()
        st.error(f"2026년 데이터를 찾을 수 없습니다. (발견된 연도 목록: {years_found})")
        return pd.DataFrame()

    # 읍면동 코드 앞 5자리 추출 (시군구 단위)
    df_2026["시군구코드"] = df_2026["코드"].astype(str).str.strip().str[:5]
    
    # 전체 인구: '계_'로 시작하는 열
    total_cols = [c for c in df_2026.columns if c.startswith("계_")]
    
    # 65세 이상 열 식별
    elderly_cols = []
    for c in total_cols:
        cleaned = c.replace("계_", "").replace("세", "").strip()
        if "이상" in cleaned:
            elderly_cols.append(c)
        else:
            try:
                if int(cleaned) >= 65:
                    elderly_cols.append(c)
            except ValueError:
                pass
                
    # 인구 수치 숫자형 변환 (쉼표 및 공백 제거)
    for c in total_cols:
        df_2026[c] = pd.to_numeric(
            df_2026[c].astype(str).str.replace(",", "").str.strip(), 
            errors="coerce"
        ).fillna(0)
        
    # 시군구 단위 합산
    agg_df = df_2026.groupby("시군구코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg_df["고령인구"] = agg_df[elderly_cols].sum(axis=1)
    
    # 고령화율(%) 계산
    agg_df["고령화율"] = (agg_df["고령인구"] / agg_df["총인구"].replace(0, float("nan"))) * 100
    agg_df["고령화율"] = agg_df["고령화율"].round(2)
    
    return agg_df

with st.spinner("데이터를 로딩하고 분석 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_and_process_data()

if pop_df.empty:
    st.stop()

# GeoJSON 속성(시도, 시군구)을 테이블에 매핑
geo_names = [
    {
        "시군구코드": str(f["properties"].get("코드", "")).strip()[:5],
        "시도": f["properties"].get("시도", ""),
        "시군구": f["properties"].get("시군구", "")
    }
    for f in geojson_data.get("features", [])
]
name_df = pd.DataFrame(geo_names).drop_duplicates(subset=["시군구코드"])

merged_df = pd.merge(pop_df, name_df, on="시군구코드", how="left")
merged_df["지역명"] = (merged_df["시도"].fillna("") + " " + merged_df["시군구"].fillna("")).str.strip()
merged_df["지역명"] = merged_df["지역명"].replace("", float("nan")).fillna(merged_df["시군구코드"])

# 기준선 슬라이더 설정
valid_rates = merged_df["고령화율"].dropna()
min_val = float(valid_rates.min()) if not valid_rates.empty else 0.0
max_val = float(valid_rates.max()) if not valid_rates.empty else 50.0

default_slider_val = float(min(max(20.0, min_val), max_val))

threshold = st.slider(
    "고령화율 기준선(%)을 설정하세요",
    min_value=float(round(min_val, 1)),
    max_value=float(round(max_val, 1)),
    value=round(default_slider_val, 1),
    step=0.5
)

label_over = f"{threshold}% 이상"
label_under = f"{threshold}% 미만"

merged_df["구분"] = merged_df["고령화율"].apply(
    lambda x: label_over if x >= threshold else label_under
)

# 화면 레이아웃 (지도 3 : TOP 5 표 1)
col_map, col_table = st.columns([3, 1])

with col_map:
    fig = px.choropleth(
        merged_df,
        geojson=geojson_data,
        locations="시군구코드",
        featureidkey="properties.코드",
        color="구분",
        category_orders={"구분": [label_over, label_under]},
        color_discrete_map={
            label_over: "#b30000",
            label_under: "#e0e0e0"
        },
        hover_name="지역명",
        hover_data={
            "시군구코드": True,
            "구분": False,
            "고령화율": ":.2f%"
        }
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
        legend=dict(
            title_text="고령화율 기준",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.02,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
    )
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("고령화율 TOP 5")
    top5_df = (
        merged_df[["지역명", "고령화율"]]
        .dropna(subset=["고령화율"])
        .sort_values(by="고령화율", ascending=False)
        .head(5)
        .reset_index(drop=True)
    )
    top5_df.index = top5_df.index + 1
    top5_df.columns = ["지역", "고령화율(%)"]
    
    st.dataframe(
        top5_df.style.format({"고령화율(%)": "{:.2f}%"}),
        use_container_width=True
    )
    
    over_count = (merged_df["구분"] == label_over).sum()
    st.caption(f"전체 {len(merged_df)}개 시군구 중 **{label_over}** 지역: **{over_count}곳**")
