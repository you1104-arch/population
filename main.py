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
    # GeoJSON properties 내 코드를 문자열 및 5자리로 정규화
    for f in data.get("features", []):
        if "properties" in f and "코드" in f["properties"]:
            f["properties"]["코드"] = str(f["properties"]["코드"]).strip()[:5]
    return data

# 2. 인구 데이터 로드 (인코딩 자동 예외 처리 및 연도 타입 정규화)
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")
        
    # 열 이름 및 값 양끝 공백 제거
    df.columns = df.columns.str.strip()
    
    # 연도 컬럼을 문자열로 통일해 '2026' 필터링 (연도 컬럼에 '년' 등이 붙은 경우 대비)
    if "연도" in df.columns:
        df["연도_정리"] = df["연도"].astype(str).str.extract(r"(\d{
