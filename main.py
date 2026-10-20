import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 서울 행정동 고령화 단계구분도", layout="wide")
st.title("2026년 서울특별시 행정동별 고령화율 분석")

# 1. 서울 행정동 GeoJSON 로드 (코드, 구, 동 속성 포함)
GEOJSON_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/seoul_dong.geojson"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    data = res.json()
    
    # GeoJSON properties 내 코드 정규화
    for f in data.get("features", []):
        props = f.get("properties", {})
        code_val = props.get("코드") or props.get("adm_cd") or props.get("adm_cd8") or ""
        props["코드"] = str(code_val).strip()
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
    
    # 전체 인구: '계_'로 시작하는 열 (남_, 여_ 제외)
    total_cols = [c for c in df_seoul.columns if c.startswith("계_")]
    
    # 65세 이상 열 선별 ('계_65세' ~ '계_100세 이상')
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
        df_seoul[c] = pd.to_numeric(
            df_seoul[c].astype(str).str.replace(",", "").str.strip(), 
            errors="coerce"
        ).fillna(0)
        
    # 코드별 합산
    agg_df = df_seoul.groupby("원래코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg_df["고령인구"] = agg_df[elderly_cols].sum(axis=1)
    
    # 고령화율(%) 계산
    agg_df["고령화율"] = (agg_df["고령인구"] / agg_df["총인구"].replace(0, float("nan"))) * 100
    agg_df["고령화율"] = agg_df["고령화율"].round(2)
    
    return agg_df

with st.spinner("서울시 행정동 데이터를 로딩 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_and_process_data()

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
