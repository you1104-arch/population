import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 서울 행정동 고령화 단계구분도", layout="wide")
st.title("2026년 서울특별시 행정동별 고령화율 분석")

# 1. 서울 행정동 GeoJSON 로드 (GitHub raw URL, 코드 10자리)
GEOJSON_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/sigungu_kr.geojson.txt"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    data = res.json()
    # GeoJSON properties 내 코드를 10자리 문자열로 정규화
    for f in data.get("features", []):
        props = f.get("properties", {})
        if "코드" in props:
            props["코드"] = str(props["코드"]).strip()[:10]
    return data

# 2. 인구 데이터 로드 및 서울 행정동별 65세 이상 비율 계산
POP_URL = "https://raw.githubusercontent.com/you1104-arch/population/main/population_ts_yearly_gender.zip"

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv(POP_URL, dtype=str)
    except Exception:
        df = pd.read_csv(POP_URL, dtype=str, encoding="cp949")
        
    df.columns = df.columns.str.strip()
    
    # 2026년 데이터 필터링
    if "연도" in df.columns:
        df["연도_clean"] = df["연도"].astype(str).str.replace("년", "").str.strip()
        df_year = df[df["연도_clean"] == "2026"].copy()
    else:
        st.error(f"'연도' 열을 찾을 수 없습니다.")
        return pd.DataFrame()

    if df_year.empty:
        st.error("2026년 인구 데이터가 없습니다.")
        return pd.DataFrame()

    # 서울(시도) 필터링 (시도에 '서울' 포함)
    if "시도" in df_year.columns:
        df_seoul = df_year[df_year["시도"].astype(str).str.contains("서울")].copy()
    else:
        st.error(f"'시도' 열을 찾을 수 없습니다.")
        return pd.DataFrame()

    if df_seoul.empty:
        st.error("2026년 서울 데이터가 없습니다.")
        return pd.DataFrame()

    # 동 코드 10자리 문자열 처리
    df_seoul["동코드"] = df_seoul["코드"].astype(str).str.strip().str[:10]
    
    # 전체 인구: '계_'로 시작하는 열의 합 (남_ / 여_ 제외)
    total_cols = [c for c in df_seoul.columns if c.startswith("계_")]
    
    # 65세 이상 열 식별 ('계_65세' ~ '계_100세 이상')
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
