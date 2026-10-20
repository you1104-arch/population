import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="2026 서울 행정동 고령화 단계구분도", layout="wide")
st.title("2026년 서울특별시 행정동별 고령화율 기준선 분석")

# 1. 서울 행정동 GeoJSON 로드
GEOJSON_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/seoul_dong.geojson"

@st.cache_data
def load_geojson():
    res = requests.get(GEOJSON_URL)
    res.raise_for_status()
    data = res.json()
    # GeoJSON properties 내 코드를 문자열로 정리
    for f in data.get("features", []):
        props = f.get("properties", {})
        # '코드' 속성이 없을 경우 adm_cd 등 대체 키 확인
        code_val = props.get("코드") or props.get("adm_cd") or props.get("EMD_CD") or ""
        props["코드"] = str(code_val).strip()
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
    
    # 연도 필터링 (2026년)
    if "연도" in df.columns:
        df["연도_clean"] = df["연도"].astype(str).str.replace("년", "").str.strip()
        df_year = df[df["연도_clean"] == "2026"].copy()
    else:
        st.error(f"'연도' 열을 찾을 수 없습니다. (현재 열: {list(df.columns[:5])})")
        return pd.DataFrame()

    if df_year.empty:
        years = df["연도"].unique() if "연도" in df.columns else []
        st.error(f"2026년 데이터가 없습니다. (존재하는 연도: {years})")
        return pd.DataFrame()

    # 서울 필터링 (시도명에 '서울' 포함 또는 코드가 '11'로 시작)
    is_seoul = pd.Series(False, index=df_year.index)
    if "시도" in df_year.columns:
        is_seoul = is_seoul | df_year["시도"].astype(str).str.contains("서울")
    if "코드" in df_year.columns:
        is_seoul = is_seoul | df_year["코드"].astype(str).str.strip().str.startswith("11")

    df_seoul = df_year[is_seoul].copy()
    if df_seoul.empty:
        st.error("서울 데이터 필터링 결과가 0건입니다.")
        return pd.DataFrame()

    # 코드 정리 (양끝 공백 제거)
    df_seoul["코드"] = df_seoul["코드"].astype(str).str.strip()
    
    # 전체 인구 및 65세 이상 컬럼 선별
    total_cols = [c for c in df_seoul.columns if c.startswith("계_")]
    elderly_cols = []
    for c in total_cols:
        age_str = c.replace("계_", "").replace("세", "").strip()
        if "이상" in age_str:
            elderly_cols.append(c)
        else:
            try:
                if int(age_str) >= 65:
                    elderly_cols.append(c)
            except ValueError:
                pass
                
    # 숫자형 변환
    for c in total_cols:
        df_seoul[c] = pd.to_numeric(
            df_seoul[c].astype(str).str.replace(",", "").str.strip(), 
            errors="coerce"
        ).fillna(0)
        
    # 코드별 합산
    agg_df = df_seoul.groupby("코드")[total_cols].sum().reset_index()
    agg_df["총인구"] = agg_df[total_cols].sum(axis=1)
    agg_df["고령인구"] = agg_df[elderly_cols].sum(axis=1)
    
    # 고령화율(%) 계산
    agg_df["고령화율"] = (agg_df["고령인구"] / agg_df["총인구"].replace(0, float("nan"))) * 100
    agg_df["고령화율"] = agg_df["고령화율"].round(2)
    
    # 동/구 이름이 있으면 보존
    meta_cols = [c for c in ["동", "시군구", "구"] if c in df_seoul.columns]
    if meta_cols:
        names = df_seoul.drop_duplicates(subset=["코드"])[["코드"] + meta_cols]
        agg_df = pd.merge(agg_df, names, on="코드", how="left")
        
    return agg_df

with st.spinner("데이터를 불러오는 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_and_process_data()

if pop_df.empty:
    st.stop()

# GeoJSON 속성에서 코드 추출 및 자릿수 맞춤 검사
geo_features = geojson_data.get("features", [])
geo_codes = [str(f.get("properties", {}).get("코드", "")).strip() for f in geo_features]
geo_len = len(geo_codes[0]) if geo_codes else 0
pop_len = len(str(pop_df["코드"].iloc[0])) if not pop_df.empty else 0

# 자릿수가 다를 경우(예: 한쪽은 8자리, 다른 쪽은 10자리) 일치 조정
if geo_len != pop_len and min(geo_len, pop_len) >= 8:
    match_len = min(geo_len, pop_len)
    pop_df["매칭코드"] = pop_df["코드"].str[:match_len]
    for f in geo_features:
        f["properties"]["코드"] = str(f["properties"].get("코드", ""))[:match_len]
else:
    pop_df["매칭코드"] = pop_df["코드"]

# GeoJSON의 구, 동 이름 매핑 테이블 생성
geo_info = []
for f in geo_features:
    p = f.get("properties", {})
    geo_info.append({
        "매칭코드": str(p.get("코드", "")),
        "구": p.get("구", ""),
        "동": p.get("동", "")
    })
name_df = pd.DataFrame(geo_info).drop_duplicates(subset=["매칭코드"])

merged_df = pd.merge(pop_df, name_df, on="매칭코드", how="left")
