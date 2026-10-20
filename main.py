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
    # GeoJSON properties 내 코드를 10자리 문자열로 정규화
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

    # 서울특별시 필터링 (시도 열에 '서울' 포함)
    if "시도" in df_seoul.columns:
        df_seoul = df_seoul[df_seoul["시도"].astype(str).str.contains("서울")].copy()
    else:
        st.error(f"'시도' 열을 찾을 수 없습니다. 열 목록: {list(df.columns[:10])}")
        return pd.DataFrame()

    if df_seoul.empty:
        st.error("2026년 서울 인구 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    # 10자리 동 코드 정규화 (문자열)
    df_seoul["동코드"] = df_seoul["코드"].astype(str).str.strip().str[:10]
    
    # 전체 인구 열: '계_'로 시작하는 열
    total_cols = [c for c in df_seoul.columns if c.startswith("계_")]
    
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
                
    # 숫자형 변환
    for c
