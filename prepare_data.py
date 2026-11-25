"""
원본 공공데이터 → data/stations.csv 전처리 스크립트

원본: 국가철도공단 「전국도시철도역사정보표준데이터」
      (공공데이터포털 https://www.data.go.kr/data/15013205/standard.do,
       다운로드 https://data.kric.go.kr/rips/M_01_01/detail.do?id=32)
파일: data/raw/전체_도시철도역사정보_20260630.xlsx  (git에는 올리지 않음)

결과: data/stations.csv  — 열: name(역 이름), lines(노선), lat(위도), lon(경도)

처리 순서
  1. 필요한 열(역 이름, 노선, 위도, 경도)만 남긴다.
  2. 수도권 역만 남긴다. (부산·대구·대전·광주 등 제외)
  3. 역 이름을 정리한다.   예) "신도림역" → "신도림", "양재(서초구청)" → "양재"
  4. 노선 이름을 정리한다. 예) "서울 도시철도 9호선" → "9호선", "경부선" → "1호선"
     (경원선 용산~왕십리 구간은 실제 운행 노선인 경의중앙선으로 바꾼다)
  5. 원본의 좌표 오류를 고친다.
  6. 이름은 같은데 멀리 떨어진 역은 다른 역으로 구분한다. 예) 5호선 양평 vs 경의중앙선 양평
  7. 환승역(같은 역이 노선마다 한 줄씩 있음)을 한 줄로 합친다.

실행 (프로젝트 폴더에서, 가상환경 켠 상태):
    python prepare_data.py
※ 엑셀 파일을 읽으려면 openpyxl 패키지가 필요하다. (requirements.txt에 포함)
"""

import pandas as pd

from utils.candidates import haversine_km

RAW_PATH = "data/raw/전체_도시철도역사정보_20260630.xlsx"
OUT_PATH = "data/stations.csv"

# 수도권 범위: 위도 36.6 이상(천안·아산 포함, 대전 제외), 경도 128.0 이하(동해안 제외)
MIN_LAT = 36.6
MAX_LON = 128.0

# 이름이 같아도 이 거리(km)보다 멀면 서로 다른 역으로 본다
SAME_STATION_KM = 1.0

# 원본 노선 이름 → 사람들이 흔히 부르는 이름
# (1호선은 실제로 경부선·경원선·경인선·장항선 위를 달린다)
LINE_NAMES = {
    "경부선": "1호선",
    "경원선": "1호선",
    "경인선": "1호선",
    "장항선": "1호선",
    "일산선": "3호선",
    "안산과천선": "4호선",
    "진접선": "4호선",
    "도시철도 7호선": "7호선",
    "수도권 광역철도 8호선": "8호선",
    "서울 도시철도 9호선": "9호선",
    "수도권  도시철도 9호선": "9호선",  # 원본에 띄어쓰기가 두 칸
    "분당선": "수인분당선",
    "수인선": "수인분당선",
    "인천지하철 1호선": "인천1호선",
    "인천지하철 2호선": "인천2호선",
    "인천국제공항선": "공항철도",
    "수도권 경량도시철도 신림선": "신림선",
    "의정부": "의정부경전철",
    "김포도시철도": "김포골드라인",
    "자기부상철도": "인천공항자기부상",
}

# 같은 역인데 노선마다 이름이 다른 경우 → 하나로 통일
NAME_ALIASES = {
    "이수": "총신대입구",  # 4호선 '총신대입구(이수)' = 7호선 '이수'
}

# 원본 좌표 오류 수정: (역 이름, 노선) → (위도, 경도)
# 원본에서 마곡은 발산의 좌표, 이촌은 신용산의 좌표가 잘못 들어가 있었다.
# 올바른 좌표는 한국어 위키백과 문서의 좌표를 사용했다.
FIX_COORDS = {
    ("마곡", "5호선"): (37.560278, 126.825556),
    ("이촌", "4호선"): (37.522278, 126.974722),
}


def load_raw(path):
    """원본 엑셀에서 필요한 열만 읽어 영어 열 이름으로 바꾼다."""
    df = pd.read_excel(path)
    df = df[["역번호", "역사명", "노선명", "역위도", "역경도"]]
    df.columns = ["code", "name", "line", "lat", "lon"]
    return df


def fix_gyeongwon_line(df):
    """경원선 용산~왕십리 구간을 '경의중앙선'으로 바꾼다.

    원본은 노선을 '선로' 기준으로 적어서, 용산~왕십리(역번호 1003~1013)가 경원선으로 되어 있다.
    하지만 이 구간에는 실제로 1호선이 아니라 경의중앙선 전철이 다닌다.
    (LINE_NAMES에서 경원선을 1호선으로 바꾸기 전에 먼저 처리해야 한다.)
    """
    code = pd.to_numeric(df["code"], errors="coerce")  # 'D004' 같은 글자 번호는 NaN
    target = (df["line"] == "경원선") & (code >= 1003) & (code <= 1013)
    df.loc[target, "line"] = "경의중앙선"
    return df


def keep_capital_area(df):
    """수도권 범위 안의 역만 남긴다."""
    in_area = (df["lat"] >= MIN_LAT) & (df["lon"] <= MAX_LON)
    return df[in_area].copy()


def clean_name(name):
    """역 이름을 정리한다.

    - 괄호 부분 제거: "양재(서초구청)" → "양재"
    - 끝의 '역' 제거: "신도림역" → "신도림" (한국철도공사 노선은 이름 뒤에 '역'이 붙어 있음)
    - 별칭 통일: "이수" → "총신대입구"
    """
    if "(" in name:
        name = name[: name.index("(")]
    name = name.strip()
    if name.endswith("역") and len(name) > 2:
        name = name[:-1]
    return NAME_ALIASES.get(name, name)


def fix_coords(df):
    """FIX_COORDS에 적어 둔 역의 좌표를 고친다."""
    for (name, line), (lat, lon) in FIX_COORDS.items():
        target = (df["name"] == name) & (df["line"] == line)
        df.loc[target, "lat"] = lat
        df.loc[target, "lon"] = lon
    return df


def split_far_same_name(df):
    """이름이 같지만 1km 넘게 떨어진 역은 이름 뒤에 (노선)을 붙여 구분한다.

    예) 5호선 양평(서울 영등포구)과 경의중앙선 양평(경기 양평군)은 약 40km 떨어진 다른 역이다.
    이름별로 첫 번째 행을 기준점으로 삼고, 기준점에서 먼 행만 이름을 바꾼다.
    """
    for name, group in df.groupby("name"):
        first = group.iloc[0]
        for idx, row in group.iterrows():
            dist = haversine_km(first["lat"], first["lon"], row["lat"], row["lon"])
            if dist > SAME_STATION_KM:
                new_name = f"{name}({row['line']})"
                print(f"  이름 구분: {name} → {new_name} (기준점과 {dist:.1f}km 떨어짐)")
                df.loc[idx, "name"] = new_name
    return df


def merge_transfer_stations(df):
    """같은 이름의 행(=환승역)을 한 줄로 합친다.

    좌표는 노선별 좌표의 평균, 노선은 "2호선, 신분당선"처럼 쉼표로 이어 붙인다.
    """
    merged = df.groupby("name").agg(
        lines=("line", lambda s: ", ".join(sorted(set(s)))),
        lat=("lat", "mean"),
        lon=("lon", "mean"),
    )
    merged = merged.reset_index()
    merged["lat"] = merged["lat"].round(6)
    merged["lon"] = merged["lon"].round(6)
    return merged


def main():
    df = load_raw(RAW_PATH)
    print(f"원본: {len(df)}행")

    df = keep_capital_area(df)
    print(f"수도권만: {len(df)}행")

    df["name"] = df["name"].apply(clean_name)
    df = fix_gyeongwon_line(df)
    df["line"] = df["line"].replace(LINE_NAMES)
    df = fix_coords(df)
    df = split_far_same_name(df)

    stations = merge_transfer_stations(df)
    print(f"환승역 합친 뒤: {len(stations)}개 역")

    # 엑셀에서 열어도 한글이 깨지지 않도록 utf-8-sig로 저장
    stations.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
