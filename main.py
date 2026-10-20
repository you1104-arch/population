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
    # GeoJSON properties 내 코드를 문자열 및 앞 5자리로 정규화
    for f in data.get("features", []):
        if "properties" in f and "코드" in f["properties"]:
            f["properties"]["코드"] = str(f["properties"]["코드"]).strip()[:5]
    return data

# 2. 인구 데이터 로드 및 65세 이상 고령화율 계산
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")
        
    # 열 이름 양끝 공백 제거
    df.columns = df.columns.str.strip()
    
    # 연도 컬럼에서 2026 추출 (문자열 또는 숫자 모두 대응)
    if "연도" in df.columns:
        # '2026년', 2026, '2026' 등 모두 처리
        df["연도_clean"] = df["연도"].astype(str).str.replace("년", "").str.strip()
        df_2026 = df[df["연도_clean"] == "2026"].copy()
    else:
        st.error(f"'연도' 열을 찾을 수 없습니다. 현재 열 목록: {list(df.columns[:10])}")
        return pd.DataFrame()

    if df_2026.empty:
        sample_years = df["연도"].unique() if "연도" in df.columns else []
        st.error(f"2026년 데이터를 찾을 수 없습니다. 데이터 내 존재하는 연도 목록: {sample_years}")
        return pd.DataFrame()

    # 읍면동 코드 앞 5자리 추출 (시군구 코드)
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
                
    # 숫자형 변환 (쉼표 및 공백 제거)
    for c in total_cols:
        df_2026[c] = pd.to_numeric(df_2026[c].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)
        
    # 시군구 단위 합산
    agg_df = df_2026.groupby("시군구코드")[total_cols].sum().reset_
