"""
[임시] 카카오 API 연결 테스트 앱 (3단계)

출발지·도착지 이름을 입력하면
  1) 키워드 장소 검색 API로 좌표를 찾고
  2) 대중교통 경로 API로 최소 소요시간·환승 횟수·요금을 보여준다.
원본 응답(JSON)은 expander로 열어서 확인할 수 있다.

※ 6단계에서 이 파일은 '홈' 페이지로 바뀐다.
"""

import requests
import streamlit as st

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
TRANSIT_URL = "https://dapi.kakao.com/v2/routing/publictraffic"


def get_api_key():
    """secrets.toml에서 카카오 REST API 키를 읽는다. 없으면 None."""
    try:
        return st.secrets["KAKAO_REST_KEY"]
    except Exception:
        return None


def call_kakao(url, params, api_key):
    """카카오 API를 GET으로 호출한다.

    반환: (응답 JSON, 오류 문구). 성공하면 오류 문구는 None,
    실패하면 응답 JSON은 None(또는 오류 응답 본문)이다.
    """
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.exceptions.Timeout:
        return None, "응답 시간이 10초를 넘었습니다."
    except requests.exceptions.RequestException as e:
        return None, f"네트워크 오류: {e}"

    # 응답 본문을 JSON으로 바꾼다 (실패하면 글자 그대로 보관)
    try:
        data = response.json()
    except ValueError:
        data = {"raw_text": response.text}

    if response.status_code != 200:
        # 예: 401 키 오류, 429 / code -10 쿼터 초과
        return data, f"HTTP {response.status_code} 오류: {data}"
    return data, None


def search_place(query, api_key):
    """키워드로 장소를 검색해 첫 번째 결과를 돌려준다.

    반환: (장소 정보 dict 또는 None, 원본 응답, 오류 문구)
    장소 정보: {"name", "address", "lat", "lon"}
    """
    data, error = call_kakao(KEYWORD_URL, {"query": query, "size": 5}, api_key)
    if error:
        return None, data, error

    documents = data.get("documents", [])
    if len(documents) == 0:
        return None, data, f"'{query}' 검색 결과가 없습니다."

    first = documents[0]
    place = {
        "name": first["place_name"],
        "address": first["address_name"],
        # 카카오는 x = 경도, y = 위도. 우리 코드에서는 lat/lon으로 바꿔 쓴다.
        "lat": float(first["y"]),
        "lon": float(first["x"]),
    }
    return place, data, None


def get_transit(start, end, api_key):
    """두 지점 사이의 대중교통 경로를 조회한다.

    반환: (요약 dict 또는 None, 원본 응답, 오류 문구)
    요약: {"minutes", "transfers", "fare", "type", "route_count"}
    """
    params = {
        "start_x": start["lon"],
        "start_y": start["lat"],
        "end_x": end["lon"],
        "end_y": end["lat"],
    }
    data, error = call_kakao(TRANSIT_URL, params, api_key)
    if error:
        return None, data, error

    status = data.get("status")
    if status == "EQUAL_POINTS":
        # 출발지와 도착지가 같으면 0분으로 처리
        summary = {"minutes": 0, "transfers": 0, "fare": 0, "type": "-", "route_count": 0}
        return summary, data, None
    if status != "OK":
        return None, data, f"경로를 찾지 못했습니다. (status = {status})"

    routes = data.get("routes", [])
    if len(routes) == 0:
        return None, data, "status는 OK인데 경로 목록이 비어 있습니다."

    # 여러 경로 중 소요시간(totalTime, 초)이 가장 짧은 경로를 고른다
    best = routes[0]
    for route in routes:
        if route["properties"]["totalTime"] < best["properties"]["totalTime"]:
            best = route

    props = best["properties"]
    summary = {
        "minutes": round(props["totalTime"] / 60),
        "transfers": props.get("transfers", "?"),
        "fare": props.get("fare", {}).get("value", "?"),
        "type": props.get("type", "?"),
        "route_count": len(routes),
    }
    return summary, data, None


# ---------------- 화면 ----------------

st.set_page_config(page_title="where2meet - API 테스트", page_icon="🧪")
st.title("🧪 카카오 API 연결 테스트")
st.caption("임시 페이지입니다. 장소 검색 → 대중교통 경로 조회가 잘 되는지 확인합니다.")

api_key = get_api_key()
if api_key is None:
    st.error(
        "API 키를 찾지 못했습니다. `.streamlit/secrets.toml` 파일에 "
        '`KAKAO_REST_KEY = "..."` 한 줄이 있는지 확인하세요.'
    )
    st.stop()
else:
    st.success("API 키를 불러왔습니다.")

col1, col2 = st.columns(2)
start_query = col1.text_input("출발지", value="서울대입구역")
end_query = col2.text_input("도착지", value="강남역")

if st.button("경로 조회", type="primary"):
    if start_query.strip() == "" or end_query.strip() == "":
        st.warning("출발지와 도착지를 모두 입력하세요.")
        st.stop()

    # 1) 키워드 검색으로 좌표 찾기
    start, start_raw, start_err = search_place(start_query, api_key)
    end, end_raw, end_err = search_place(end_query, api_key)

    st.subheader("1. 장소 검색 결과")
    col1, col2 = st.columns(2)
    with col1:
        if start_err:
            st.error(f"출발지: {start_err}")
        else:
            st.write(f"**{start['name']}**")
            st.write(start["address"])
            st.write(f"위도 {start['lat']:.5f}, 경도 {start['lon']:.5f}")
        with st.expander("출발지 원본 응답 JSON"):
            st.json(start_raw)
    with col2:
        if end_err:
            st.error(f"도착지: {end_err}")
        else:
            st.write(f"**{end['name']}**")
            st.write(end["address"])
            st.write(f"위도 {end['lat']:.5f}, 경도 {end['lon']:.5f}")
        with st.expander("도착지 원본 응답 JSON"):
            st.json(end_raw)

    if start_err or end_err:
        st.stop()

    # 2) 대중교통 경로 조회
    st.subheader("2. 대중교통 경로 (최소 소요시간 기준)")
    summary, transit_raw, transit_err = get_transit(start, end, api_key)

    if transit_err:
        st.error(transit_err)
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("소요시간", f"{summary['minutes']}분")
        m2.metric("환승", f"{summary['transfers']}회")
        fare = summary["fare"]
        m3.metric("요금", f"{fare:,}원" if isinstance(fare, int) else f"{fare}원")
        m4.metric("경로 종류", summary["type"])
        st.caption(f"조회된 경로 {summary['route_count']}개 중 가장 빠른 경로입니다.")

    with st.expander("대중교통 원본 응답 JSON"):
        st.json(transit_raw)
