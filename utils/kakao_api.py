"""
카카오 API 호출 모음 + 소요시간 표 만들기

- search_places: 키워드로 장소 검색 (출발지 입력용)
- get_transit_minutes: 대중교통 최소 소요시간(분)
- estimate_minutes: API 실패·데모 모드일 때 쓰는 추정 소요시간(분)
- search_nearby: 역 주변 카페·음식점 검색 (가까운 45곳 + 원을 3×3 칸으로 나눠 최대 450곳, 메뉴 키워드 검색 가능)
- build_time_table: 후보역 × 참여자 소요시간 표 (2단계 탐색의 2단계)

규칙
- 카카오 응답은 파일·DB에 저장하지 않고, st.cache_data로 캐시하지도 않는다. (카카오 정책)
- 모든 함수는 실패해도 예외를 던지지 않고 (결과, 오류 문구)를 돌려준다.
- 카카오의 x = 경도(lon), y = 위도(lat). 이 변환은 이 파일 안에서만 한다.
"""

import math

import pandas as pd
import requests
import streamlit as st

from utils.candidates import haversine_km

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"
TRANSIT_URL = "https://dapi.kakao.com/v2/routing/publictraffic"
TIMEOUT = 10  # 초

# API 실패 시 추정: 평균 시속 20km + 대기·도보 10분
AVG_SPEED_KMH = 20
EXTRA_MINUTES = 10

# 카테고리 코드
CATEGORY_CODES = {"카페": "CE7", "음식점": "FD6"}
MAX_PAGES = 3  # 카카오는 한 조건에 15곳 × 3페이지 = 최대 45곳만 알려 준다
GRID = 3       # 주변 장소: 가장 가까운 45곳 + 원을 3×3 칸으로 나눠 칸마다 45곳 (최대 450곳)
MAX_MESSAGE = 200  # 화면에 보여줄 오류 문구 최대 길이

# 응답 모양이 예상과 다를 때(필요한 칸이 없거나, 숫자가 아니거나) 나는 오류들
PARSE_ERRORS = (KeyError, TypeError, ValueError, AttributeError)
PARSE_ERROR_MESSAGE = "카카오 응답 형식이 예상과 달라 결과를 읽지 못했습니다."


def safe_link(url):
    """카카오맵 링크가 웹 주소일 때만 쓴다. http는 https로 바꾸고, 그 밖의 형식(javascript: 등)은 버린다."""
    url = str(url or "")
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        return ""
    return url


def get_api_key():
    """secrets.toml에서 카카오 REST API 키를 읽는다. 없으면 None."""
    try:
        return st.secrets["KAKAO_REST_KEY"]
    except Exception:
        return None


def call_kakao(url, params):
    """카카오 API를 GET으로 호출한다.

    반환: (응답 JSON, None) 또는 실패 시 (None, 오류 문구)
    """
    api_key = get_api_key()
    if api_key is None:
        return None, "API 키가 없습니다. (.streamlit/secrets.toml 확인)"

    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return None, f"응답 시간이 {TIMEOUT}초를 넘었습니다."
    except requests.exceptions.RequestException:
        return None, "네트워크 오류로 카카오 서버에 연결하지 못했습니다."

    if response.status_code != 200:
        # 카카오 오류 응답 예: {"code": -10, "msg": "API limit has been exceeded."}
        try:
            body = response.json()
            message = body.get("msg") or body.get("message") or response.text
        except ValueError:
            message = response.text
        # 서버가 긴 HTML 오류 페이지를 돌려줄 수도 있으므로 앞 200자만 보여준다
        message = str(message)[:MAX_MESSAGE]
        return None, f"카카오 API 오류 (HTTP {response.status_code}): {message}"

    try:
        return response.json(), None
    except ValueError:
        return None, "카카오 응답을 읽지 못했습니다."


def search_places(query, size=5):
    """키워드로 장소를 검색한다.

    반환: (장소 목록, 오류 문구)
      장소: {"name", "address", "lat", "lon"}
    """
    if query.strip() == "":
        return [], "검색어를 입력하세요."

    data, error = call_kakao(KEYWORD_URL, {"query": query, "size": size})
    if error:
        return [], error

    places = []
    try:
        for doc in data.get("documents", []):
            places.append({
                "name": doc["place_name"],
                "address": doc.get("road_address_name") or doc.get("address_name", ""),
                "lat": float(doc["y"]),  # y = 위도
                "lon": float(doc["x"]),  # x = 경도
            })
    except PARSE_ERRORS:
        return [], PARSE_ERROR_MESSAGE
    if len(places) == 0:
        return [], f"'{query}' 검색 결과가 없습니다."
    return places, None


def get_transit_minutes(start, end):
    """대중교통 최소 소요시간(분)을 구한다.

    start, end: {"lat", "lon"}가 들어 있는 dict
    반환: (분, None) 또는 실패 시 (None, 오류 문구)
    """
    params = {
        "start_x": start["lon"],
        "start_y": start["lat"],
        "end_x": end["lon"],
        "end_y": end["lat"],
    }
    data, error = call_kakao(TRANSIT_URL, params)
    if error:
        return None, error

    try:
        status = data.get("status")
        if status == "EQUAL_POINTS":  # 출발지 = 도착지
            return 0, None
        if status != "OK":
            return None, f"대중교통 경로를 찾지 못했습니다. (status = {status})"

        routes = data.get("routes", [])
        if len(routes) == 0:
            return None, "대중교통 경로가 비어 있습니다."

        # 여러 경로 중 가장 짧은 totalTime(초)
        shortest = min(float(route["properties"]["totalTime"]) for route in routes)
        return round(shortest / 60), None
    except PARSE_ERRORS:
        return None, PARSE_ERROR_MESSAGE


def estimate_minutes(start, end):
    """직선거리로 소요시간(분)을 추정한다: 거리 / 시속 20km × 60 + 10분."""
    km = haversine_km(start["lat"], start["lon"], end["lat"], end["lon"])
    return round(km / AVG_SPEED_KMH * 60 + EXTRA_MINUTES)


def split_into_cells(lat, lon, radius, n=GRID):
    """역을 가운데 두고, 한 변이 반경의 2배인 정사각형을 n×n 칸으로 나눈다.

    카카오 장소 검색은 한 조건에 최대 45곳만 알려 준다. 넓은 원을 한 번에 가까운 순으로 검색하면
    역 바로 앞 45곳만 나와서 반경을 넓혀도 결과가 같다. 칸을 나눠 칸마다 검색하면 원 전체에서 고르게 찾는다.
    반환: 카카오 rect 파라미터 문자열 목록 ("왼쪽 경도,아래 위도,오른쪽 경도,위 위도")
    """
    # 미터 → 도 단위: 위도 1도 ≈ 111km, 경도 1도 ≈ 111km × cos(위도)
    half_lat = radius / 111000
    half_lon = radius / (111000 * math.cos(math.radians(lat)))
    step_lat = 2 * half_lat / n
    step_lon = 2 * half_lon / n

    cells = []
    for row in range(n):
        for col in range(n):
            south = lat - half_lat + row * step_lat
            west = lon - half_lon + col * step_lon
            # 카카오 rect는 x(경도), y(위도) 순서
            cells.append(f"{west},{south},{west + step_lon},{south + step_lat}")
    return cells


def fetch_pages(url, params):
    """같은 조건으로 최대 MAX_PAGES 페이지(15곳 × 3 = 45곳)까지 이어서 받는다.

    반환: (카카오 documents 목록, 오류 문구). 2페이지부터 실패하면 이미 받은 것만 돌려준다.
    """
    docs = []
    for page in range(1, MAX_PAGES + 1):
        params["page"] = page
        data, error = call_kakao(url, params)
        if error:
            if len(docs) == 0:
                return [], error
            break
        try:
            docs += list(data.get("documents", []))
            is_end = data.get("meta", {}).get("is_end", True)
        except PARSE_ERRORS:
            if len(docs) == 0:
                return [], PARSE_ERROR_MESSAGE
            break
        if is_end:  # 마지막 페이지면 그만
            break
    return docs, None


def to_place(doc):
    """카카오 documents 한 개를 장소 dict로 바꾼다."""
    # "음식점 > 한식 > 육류,고기 > 삼겹살" → 분류 "한식", 종류 "삼겹살"
    parts = doc.get("category_name", "").split(" > ")
    return {
        "id": doc.get("id") or doc["place_name"],
        "name": doc["place_name"],
        "distance": int(doc.get("distance") or 0),
        "group": parts[1] if len(parts) > 1 else parts[0],
        "category": parts[-1],
        "url": safe_link(doc.get("place_url")),
        "lat": float(doc["y"]),
        "lon": float(doc["x"]),
    }


def search_nearby(category, lat, lon, radius, keyword=""):
    """역 주변 장소를 검색한다.

    category: "카페" 또는 "음식점", radius: 반경(m)
    keyword: 메뉴 키워드(예: "삼겹살").
      - 비어 있으면 카테고리 검색: ① 역에서 가장 가까운 45곳 + ② 원을 3×3 칸으로 나눠 칸마다 45곳을
        합친 뒤(중복 제거) 가까운 순으로 정렬한다. (최대 10 × 45 = 450곳, 호출 최대 30번)
      - 있으면 키워드 검색: 원 전체에서 관련도순(accuracy)으로 45곳을 받고 그 순서를 그대로 쓴다.
        (거리순으로 받으면 '파스타'에 와인바·빵집처럼 관련 적은 곳이 앞에 섞이기 때문)
    x, y(역 좌표)를 함께 넘기면 응답에 역에서의 거리(distance, m)가 들어온다.

    반환: (장소 목록, 오류 문구)
      장소: {"id", "name", "distance"(m), "group"(세부 분류), "category"(가장 자세한 종류), "url", "lat", "lon"}
      일부 칸만 실패하면 찾은 장소와 함께 안내 문구를 돌려준다.
    """
    base = {"category_group_code": CATEGORY_CODES[category], "x": lon, "y": lat, "size": 15}

    docs = []
    error = None
    if keyword.strip() == "":
        # ① 역에서 가장 가까운 45곳 (칸으로만 나누면 역 바로 앞 가게가 적게 나오므로 먼저 받는다)
        params = dict(base)
        params["radius"] = radius
        params["sort"] = "distance"
        docs, error = fetch_pages(CATEGORY_URL, params)
        # ② 원을 3×3 칸으로 나눠 칸마다 45곳씩 (원 바깥쪽까지 고르게)
        cells = [] if error else split_into_cells(lat, lon, radius)  # 첫 검색부터 실패하면 칸 검색은 건너뛴다
        for rect in cells:
            params = dict(base)  # 칸마다 새 dict (원본을 바꾸지 않도록 복사)
            params["rect"] = rect
            cell_docs, cell_error = fetch_pages(CATEGORY_URL, params)
            docs += cell_docs
            if cell_error:  # 키 없음·쿼터 초과·네트워크 오류는 다른 칸도 실패하므로 멈춘다
                error = cell_error
                break
    else:
        params = dict(base)
        params["query"] = keyword.strip()
        params["radius"] = radius
        params["sort"] = "accuracy"
        docs, error = fetch_pages(KEYWORD_URL, params)

    places = []
    seen = set()  # 이미 넣은 장소 id (칸 경계에 걸친 장소가 두 번 들어가지 않도록)
    try:
        for doc in docs:
            place = to_place(doc)
            # 정사각형 모서리 부분은 원 밖이므로 뺀다
            if place["id"] in seen or place["distance"] > radius:
                continue
            seen.add(place["id"])
            places.append(place)
    except PARSE_ERRORS:
        error = PARSE_ERROR_MESSAGE

    if keyword.strip() == "":
        places.sort(key=lambda p: p["distance"])  # 칸별 결과를 합쳤으니 가까운 순으로 다시 정렬

    if len(places) == 0:
        if error:
            return [], error
        what = f"'{keyword.strip()}' {category}" if keyword.strip() else category
        return [], f"반경 {radius}m 안에 {what}가 없습니다."
    if error:
        return places, f"일부 구역은 검색하지 못했습니다. ({error})"
    return places, None


def build_time_table(people, cands, demo_mode=False, progress=None):
    """후보역 × 참여자 소요시간 표를 만든다.

    people: 참여자 dict 목록 (name, lat, lon), cands: 후보역 DataFrame (name, lat, lon)
    demo_mode: True면 API를 부르지 않고 모두 추정치로 채운다.
    progress: st.progress(...)로 만든 진행 표시줄 (없으면 None)

    반환: (times, est, errors)
      times: 행 = 역 이름, 열 = 참여자 이름, 값 = 분
      est:   times와 같은 모양, 추정치로 채운 칸이면 True
      errors: 발생한 오류 문구 목록 (중복 없이)
    """
    station_names = list(cands["name"])
    person_names = [p["name"] for p in people]
    times = pd.DataFrame(0, index=station_names, columns=person_names)
    est = pd.DataFrame(False, index=station_names, columns=person_names)
    errors = []

    total = len(station_names) * len(people)  # 전체 호출 수
    done = 0
    for _, station in cands.iterrows():
        end = {"lat": station["lat"], "lon": station["lon"]}
        for person in people:
            minutes = None
            if not demo_mode:
                minutes, error = get_transit_minutes(person, end)
                if error and error not in errors:
                    errors.append(error)

            if minutes is None:  # 데모 모드이거나 API 실패 → 추정치
                minutes = estimate_minutes(person, end)
                est.loc[station["name"], person["name"]] = True

            times.loc[station["name"], person["name"]] = minutes

            done += 1
            if progress is not None:
                progress.progress(done / total, text=f"이동시간 조회 중... ({done}/{total})")

    return times, est, errors


# ---------------- 동작 확인: python -m utils.kakao_api ----------------
# (실제 API를 10~12번 호출한다)
if __name__ == "__main__":
    places, error = search_places("서울대입구역")
    print("장소 검색:", error or [p["name"] for p in places])

    a = {"name": "A", "lat": 37.4813, "lon": 126.9527}  # 서울대입구
    b = {"name": "B", "lat": 37.5385, "lon": 127.1238}  # 천호
    gangnam = {"lat": 37.4979, "lon": 127.0276}
    minutes, error = get_transit_minutes(a, gangnam)
    print("서울대입구 → 강남 대중교통:", error or f"{minutes}분")
    print("서울대입구 → 강남 추정치:", estimate_minutes(a, gangnam), "분")

    assert len(split_into_cells(gangnam["lat"], gangnam["lon"], 1000)) == 9  # 3×3 칸

    near, error = search_nearby("음식점", gangnam["lat"], gangnam["lon"], 1000)
    farthest = max(p["distance"] for p in near) if near else 0
    print("강남 1000m 음식점:", error or f"{len(near)}곳, 가장 먼 곳 {farthest}m")
    assert len(near) > 45 and farthest > 500  # 45곳 제한을 넘고, 원 바깥쪽까지 찾는다
    assert len(set(p["id"] for p in near)) == len(near)  # 중복 없음
    assert all(p["distance"] <= 1000 for p in near)    # 모두 원 안

    near, error = search_nearby("음식점", gangnam["lat"], gangnam["lon"], 500, keyword="파스타")
    print("강남 500m '파스타' 음식점:", error or f"{len(near)}곳, 예: {[(p['name'], p['group']) for p in near[:3]]}")

    near, error = search_nearby("음식점", gangnam["lat"], gangnam["lon"], 300, keyword="없는메뉴이름xyz")
    print("없는 메뉴:", error)
    assert near == [] and error is not None

    cands = pd.DataFrame({"name": ["강남", "사당"], "lat": [37.4979, 37.4765], "lon": [127.0276, 126.9816]})
    times, est, errors = build_time_table([a, b], cands, demo_mode=True)
    print("\n데모 모드 표:\n", times)
    assert est.all().all()  # 데모 모드면 전부 추정치

    times, est, errors = build_time_table([a, b], cands)
    print("\n실제 API 표:\n", times)
    print("추정치 칸:", int(est.sum().sum()), "개 / 오류:", errors)
    print("\nkakao_api.py 확인 완료")
