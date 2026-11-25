"""
주변 장소 페이지: 확정한 역 주변의 카페·음식점

- 중간지점 찾기에서 확정한 역(st.session_state["selected_station"])을 쓴다.
- 종류(카페/음식점)와 반경(300~1000m)을 고르면 가까운 순으로 보여준다.
  (카카오는 한 번에 45곳까지만 주므로, 가까운 45곳 + 반경을 9구역으로 나눠 구역마다 찾아 최대 450곳)
- 메뉴 키워드(예: 삼겹살)를 넣으면 그 메뉴와 관련된 곳을 관련도 순으로 찾는다.
- 받은 결과 안에서 세부 분류(한식·양식…)로 거를 수 있다. (API 추가 호출 없음)
- 같은 조건이면 다시 검색하지 않는다. (조건이 바뀔 때만 API 호출)
"""

import html

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.candidates import load_stations
from utils.kakao_api import search_nearby
from utils.text import md_escape

st.set_page_config(page_title="주변 장소", page_icon="☕", layout="wide")

MARKER_COLORS = {"카페": "green", "음식점": "orange"}

demo_mode = st.session_state.get("demo_mode", False)  # 사이드바 토글은 app.py에서 그린다
st.title("☕ 약속 장소 주변 둘러보기")

# ---------------- 선행 데이터 확인 ----------------
if "selected_station" not in st.session_state:
    st.info("아직 약속 장소를 확정하지 않았습니다. 먼저 중간지점을 찾고 역을 확정해 주세요.")
    st.page_link("pages/1_중간지점_찾기.py", label="중간지점 찾기로 가기", icon="📍")
    st.stop()

station_name = st.session_state["selected_station"]
stations = load_stations()
found = stations[stations["name"] == station_name]
if len(found) == 0:
    st.error(f"'{station_name}'역의 위치 정보를 찾지 못했습니다.")
    st.stop()
station = found.iloc[0]

st.subheader(f"📍 {station_name}역")
st.caption(station["lines"])

# ---------------- 검색 조건 ----------------
c1, c2, c3 = st.columns([1, 2, 2])
with c1:
    category = st.radio("종류", ["카페", "음식점"], horizontal=True)
with c2:
    radius = st.slider("반경 (m)", 300, 1000, 500, step=100)
with c3:
    keyword = st.text_input("메뉴 키워드 (선택)", placeholder="예: 삼겹살, 파스타, 디저트", max_chars=30,
                            help="비워 두면 종류 전체를 가까운 순으로, 입력하면 그 메뉴와 관련된 곳만 찾습니다.")

if demo_mode:
    st.info("데모 모드에서는 카카오 API를 부르지 않으므로 주변 장소 검색을 할 수 없습니다. 지도에 역 위치만 표시합니다.")
    places, error = [], None
else:
    # 조건(역·종류·반경·키워드)이 지난번과 같으면 저장된 결과를 다시 쓴다
    condition = (station_name, category, radius, keyword.strip())
    saved = st.session_state.get("nearby")
    if saved is None or saved["condition"] != condition:
        with st.spinner("주변 장소를 찾는 중... (반경을 여러 구역으로 나눠 찾느라 몇 초 걸립니다)"):
            places, error = search_nearby(category, station["lat"], station["lon"], radius, keyword)
        st.session_state["nearby"] = {"condition": condition, "places": places, "error": error}
    places = st.session_state["nearby"]["places"]
    error = st.session_state["nearby"]["error"]

if error:
    st.warning(md_escape(error))  # 오류 문구에 메뉴 키워드(사용자 입력)가 들어갈 수 있다

# ---------------- 세부 분류 필터 (API 호출 없이 받은 결과 안에서 거르기) ----------------
if places:
    groups = sorted(set(p["group"] for p in places))
    counts = {g: sum(1 for p in places if p["group"] == g) for g in groups}
    pick = st.selectbox("세부 분류", ["전체"] + groups,
                        format_func=lambda g: f"전체 ({len(places)})" if g == "전체" else f"{g} ({counts[g]})")
    if pick != "전체":
        places = [p for p in places if p["group"] == pick]

# ---------------- 결과: 표 + 지도 ----------------
col_table, col_map = st.columns([1, 1])

with col_table:
    if places:
        if keyword.strip():
            st.markdown(f"**'{md_escape(keyword.strip())}' 관련 {category} {len(places)}곳** (관련도 순)")
        else:
            st.markdown(f"**{category} {len(places)}곳** (가까운 순)")
        table = pd.DataFrame(places)
        table = table[["name", "distance", "group", "category", "url"]]
        table.columns = ["이름", "거리(m)", "분류", "종류", "카카오맵"]
        st.dataframe(
            table,
            hide_index=True,
            column_config={"카카오맵": st.column_config.LinkColumn("카카오맵", display_text="열기")},
        )
        if keyword.strip():
            st.caption("메뉴 키워드 검색은 반경 안에서 관련도가 높은 순으로 최대 45곳을 보여줍니다.")
        else:
            st.caption("카카오는 한 번에 45곳까지만 알려 주므로, 가장 가까운 45곳에 더해 반경을 9구역으로 나눠 "
                       "구역마다 찾았습니다. 그래서 반경을 넓히면 바깥쪽 장소도 나옵니다.")
        st.caption("표의 열 이름을 누르면 그 기준으로 정렬됩니다. 장소 정보 출처: 카카오 로컬 API")

with col_map:
    # 반경이 넓으면 한 단계 멀리서 보여줘야 원 전체가 지도에 들어온다
    fmap = folium.Map(location=[station["lat"], station["lon"]], zoom_start=16 if radius <= 500 else 15)
    # 검색 반경 원
    folium.Circle([station["lat"], station["lon"]], radius=radius,
                  color="red", fill=True, fill_opacity=0.05).add_to(fmap)
    folium.Marker([station["lat"], station["lon"]], tooltip=f"{station_name}역",
                  icon=folium.Icon(color="red", icon="star")).add_to(fmap)
    # 장소가 수백 곳이라 핀 아이콘 대신 작은 점(CircleMarker)으로 표시한다
    for place in places:
        folium.CircleMarker(
            [place["lat"], place["lon"]], radius=5,
            color=MARKER_COLORS[category], fill=True, fill_opacity=0.7, weight=1,
            tooltip=f"{html.escape(place['name'])} ({place['distance']}m)",  # 툴팁은 HTML이므로 글자 그대로
        ).add_to(fmap)
    st_folium(fmap, height=480, use_container_width=True, returned_objects=[])

st.divider()
st.page_link("pages/3_정산.py", label="다 먹고 나면? 정산하러 가기", icon="💰")
