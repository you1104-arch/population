import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 서울 행정동 고령화 단계구분도", layout="wide")
st.title("2026년 서울특별시 행정동별 고령화율 기준선 분석")

# 1. 서울 행정동 GeoJSON 로드 (코드 10자리)
GEOJSON_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/seoul_dong.geojson"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    data = res.json()
    for f in data.get("features", []):
        if "properties" in f and "코드" in f["properties"]:
            f["properties"]["코드"] = str(f["properties"]["코드"]).strip()[:10]
    return data

# 2. 인구 데이터 로드 및 서울 행정동별 고령화율 계산
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")
        
    df.columns = df.columns.str.strip()
    
    # 2026년 필터링
    if "연도" in df.columns:
        df["연도_clean"] = df["연도"].astype(str).str.replace("년", "").str.strip()
        df_seoul = df[df["연도_clean"] == "2026"].copy()
    else:
        st.error(f"'연도' 열을 찾을 수 없습니다. 열 목록: {list(df.columns[:10])}")
        return pd.DataFrame()

    # 서울특별시 필터링
    if "시도" in df_seoul.columns:
        df_seoul = df_seoul[df_seoul["시도"].astype(str).str.contains("서울")].copy()
    else:
        st.error(f"'시도' 열을 찾을 수 없습니다. 열 목록: {list(df.columns[:10])}")
        return pd.DataFrame()

    if df_seoul.empty:
        st.error("2026년 서울 인구 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    # 10자리 동 코드 정규화
    df_seoul["동코드"] = df_se
