"""
후보역 관련 계산 (API 호출 없음)

- haversine_km: 두 지점 사이 직선거리
- load_stations: data/stations.csv 불러오기
- search_stations: 역 이름으로 검색 (카카오 검색 대신 쓰는 예비 수단)
- find_candidates: 참여자 위치로 후보역 k개 추리기 (2단계 탐색의 1단계)
- centroid: 참여자들의 지도상 중간점
- nearest_station: 어떤 지점에서 가장 가까운 역

참여자(people)는 아래 모양의 dict 목록으로 통일한다.
    [{"name": "민수", "place": "서울대입구역 2호선", "lat": 37.48, "lon": 126.95}, ...]
"""

import math

import pandas as pd
import streamlit as st

EARTH_RADIUS_KM = 6371  # 지구 반지름 (km)
STATIONS_PATH = "data/stations.csv"


def haversine_km(lat1, lon1, lat2, lon2):
    """두 지점(위도, 경도) 사이의 직선거리를 km로 구한다.

    지구를 구(球)로 보고 표면을 따라 잰 최단 거리(대원 거리)를 계산하는
    하버사인(haversine) 공식을 쓴다.
    """
    # 각도(도) → 라디안
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@st.cache_data  # 공공데이터 파일이라 캐시해도 된다 (카카오 응답은 캐시 금지)
def load_stations(path=STATIONS_PATH):
    """역 목록(name, lines, lat, lon)을 DataFrame으로 불러온다."""
    return pd.read_csv(path)


def search_stations(stations, query, size=5):
    """역 이름에 검색어가 들어간 역을 찾는다. (데모 모드·카카오 검색 실패 시 대신 사용)

    반환: 장소 목록 — kakao_api.search_places와 같은 모양 {"name", "address", "lat", "lon"}
    """
    word = query.strip()
    if word.endswith("역") and len(word) > 1:
        word = word[:-1]  # "강남역" → "강남"
    if word == "":
        return []

    # 이름이 정확히 같은 역을 맨 앞에, 그다음 이름에 검색어가 들어간 역
    exact = stations[stations["name"] == word]
    partial = stations[stations["name"].str.contains(word, regex=False) & (stations["name"] != word)]
    found = pd.concat([exact, partial]).head(size)

    places = []
    for _, row in found.iterrows():
        places.append({
            "name": f"{row['name']}역",
            "address": row["lines"],
            "lat": row["lat"],
            "lon": row["lon"],
        })
    return places


def find_candidates(stations, people, k=10):
    """참여자 모두에게서 가까운 후보역 k개를 고른다.

    각 역마다 참여자별 직선거리를 구하고,
      1순위: 가장 먼 사람까지의 거리(max_km)가 짧은 순
      2순위: 거리 총합(total_km)이 짧은 순
    으로 정렬해 위에서 k개를 고른다.
    반환: stations 열 + max_km, total_km 열이 붙은 DataFrame (k행)
    """
    max_list = []
    total_list = []
    for _, station in stations.iterrows():
        dists = []
        for person in people:
            d = haversine_km(person["lat"], person["lon"], station["lat"], station["lon"])
            dists.append(d)
        max_list.append(max(dists))
        total_list.append(sum(dists))

    result = stations.copy()
    result["max_km"] = max_list
    result["total_km"] = total_list
    result = result.sort_values(["max_km", "total_km"]).head(k)
    return result.reset_index(drop=True)


def centroid(people):
    """참여자 위치의 평균 = 지도상 중간점. (위도, 경도)를 돌려준다."""
    lat = sum(p["lat"] for p in people) / len(people)
    lon = sum(p["lon"] for p in people) / len(people)
    return lat, lon


def nearest_station(stations, lat, lon):
    """주어진 지점에서 직선거리가 가장 가까운 역의 행(Series)을 돌려준다."""
    best_row = None
    best_dist = None
    for _, station in stations.iterrows():
        d = haversine_km(lat, lon, station["lat"], station["lon"])
        if best_dist is None or d < best_dist:
            best_dist = d
            best_row = station
    return best_row


# ---------------- 동작 확인: python -m utils.candidates ----------------
if __name__ == "__main__":
    # 서울역 ~ 강남역: 남북 약 6.3km, 동서 약 5.0km → 직선거리 약 8.1km
    d = haversine_km(37.5547, 126.9707, 37.4979, 127.0276)
    print(f"서울역-강남역 직선거리: {d:.2f} km")
    assert 7.9 < d < 8.3

    stations = pd.read_csv(STATIONS_PATH)  # 캐시 없이 직접 읽기 (streamlit 밖에서 실행하므로)
    people = [
        {"name": "A", "lat": 37.4813, "lon": 126.9527},  # 서울대입구
        {"name": "B", "lat": 37.6541, "lon": 127.0612},  # 노원
        {"name": "C", "lat": 37.5385, "lon": 127.1238},  # 천호
    ]
    cands = find_candidates(stations, people, k=10)
    print("\n후보역 10개:")
    print(cands[["name", "lines", "max_km", "total_km"]].round(2).to_string())
    assert len(cands) == 10
    assert cands["max_km"].is_monotonic_increasing

    lat, lon = centroid(people)
    near = nearest_station(cands, lat, lon)
    print(f"\n중간점 ({lat:.4f}, {lon:.4f})에서 가장 가까운 후보역: {near['name']}")

    found = search_stations(stations, "강남역")
    print("\n'강남역' 역 이름 검색:", [p["name"] for p in found])
    assert found[0]["name"] == "강남역"  # 정확히 같은 이름이 맨 앞
    assert search_stations(stations, "   ") == []
    print("\ncandidates.py 확인 완료")
