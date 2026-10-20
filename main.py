import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 전국 고령화 단계구분도", layout="wide")
st.title("2026년 전국 시군구별 고령화율 기준선 분석")

# 1. GeoJSON 로드
GEOJSON_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/sigungu_kr.geojson.txt"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    return res.json()

# 2. 인구 데이터 로드 및 전처리
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    df = pd.read_csv(POP_URL, dtype={"코드": str})
    
    # 2026년 데이터 필터링
    df = df[df["연도"] == 2026].copy()
    
    # 5자리 시군구 코드 추출
    df["시군구코드"] = df["코드"].astype(str).str[:5]
    
    # 전체 인구: '계_'로 시작하는 열의 합
    total_cols = [c for c in df.columns if c.startswith("계_")]
    
    # 65세 이상 열 추출
    elderly_cols = []
    for c in total_cols:
        age_str = c.replace("계_", "").replace("세", "")
        if "이상" in age_str:
            elderly_cols.append(c)
        else:
            try:
                if int(age_str) >= 65:
                    elderly_cols.append(c)
            except ValueError:
                pass
                
    # 시군구별 인구 합산
    agg_df = df.groupby("시군구코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg
