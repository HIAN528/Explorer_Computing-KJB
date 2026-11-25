"""
메인 페이지: 공평한 약속 장소 찾기

흐름
  1. 참여자 이름과 출발지를 입력한다. (출발지는 검색 결과 5개 중에서 고름)
  2. 공평성 기준을 고른다.
  3. [찾기] 버튼 → 후보역 10개 추리기(API 없음) → 후보역 × 참여자 소요시간 표(API 호출)
     → 표를 st.session_state["result"]에 보관한다.
  4. 결과 화면은 보관된 표로 매번 순위만 다시 계산한다.
     → 기준·슬라이더를 바꿔도 API를 다시 부르지 않는다. (핵심 설계)
"""

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from utils.candidates import find_candidates, load_stations, search_stations
from utils.fairness import PRESET_DESCRIPTIONS, PRESETS, score_stations
from utils.kakao_api import build_time_table, search_places
from utils.state import keep, prepare

st.set_page_config(page_title="중간지점 찾기", page_icon="📍", layout="wide")

MIN_PEOPLE = 2
MAX_PEOPLE = 6
NUM_CANDIDATES = 10  # 후보역 수 k

EXAMPLE = [  # [예시 채우기] 버튼용
    ("민수", "서울대입구역"),
    ("지수", "노원역"),
    ("철수", "천호역"),
]


# 입력값 유지 도우미 prepare/keep은 utils/state.py에 있다.
# (다른 페이지에 다녀와도 입력칸 값이 남도록 하는 장치)

def fill_example():
    """예시 참여자 3명을 입력칸에 채운다."""
    st.session_state["count"] = len(EXAMPLE)
    for i, (name, query) in enumerate(EXAMPLE):
        st.session_state[f"name_{i}"] = name
        st.session_state[f"query_{i}"] = query
        st.session_state[f"choice_{i}"] = 0


# ---------------- 출발지 검색 ----------------

def get_search(i, query, demo_mode, stations):
    """i번째 참여자의 출발지 검색 결과를 돌려준다.

    검색어나 데모 모드가 바뀌었을 때만 새로 검색하고, 아니면 저장해 둔 결과를 쓴다.
    (입력칸 하나만 고쳐도 화면 전체가 다시 실행되므로, 매번 검색하면 API를 낭비한다)
    반환: {"query", "demo", "places", "notice"}
    """
    searches = st.session_state.setdefault("searches", {})
    saved = searches.get(i)
    if saved is not None and saved["query"] == query and saved["demo"] == demo_mode:
        return saved

    notice = None
    if query.strip() == "":
        places = []
    elif demo_mode:
        places = search_stations(stations, query)
        notice = "데모 모드: 역 이름으로만 검색합니다."
    else:
        places, error = search_places(query)
        if error and "검색 결과가 없습니다" not in error:
            # 카카오 검색 실패 → 역 이름 검색으로 대신한다
            places = search_stations(stations, query)
            notice = f"카카오 검색 실패({error}) → 역 이름으로 찾은 결과입니다."

    result = {"query": query, "demo": demo_mode, "places": places, "notice": notice}
    searches[i] = result
    st.session_state[f"choice_{i}"] = 0  # 검색 결과가 바뀌었으니 첫 번째 항목으로
    return result


def place_label(place):
    return f"{place['name']} · {place['address']}"


# ---------------- 화면: 입력 ----------------

stations = load_stations()
demo_mode = st.session_state.get("demo_mode", False)  # 사이드바 토글은 app.py에서 그린다

st.title("📍 공평한 약속 장소 찾기")
st.caption("출발지를 입력하면 실제 대중교통 시간을 기준으로 모두에게 공평한 지하철역을 추천합니다.")
if demo_mode:
    st.info("데모 모드입니다. 이동시간은 모두 직선거리로 계산한 추정치입니다.")

st.subheader("1. 참여자와 출발지")
col_count, col_example = st.columns([3, 1])
with col_count:
    prepare("count", 3)
    count = st.number_input("참여자 수", MIN_PEOPLE, MAX_PEOPLE, step=1,
                            key="_count", on_change=keep, args=["count"])
with col_example:
    st.write("")  # 버튼 높이를 입력칸과 맞추기 위한 빈 줄
    st.button("예시 채우기", on_click=fill_example)

people = []          # 출발지를 고른 참여자 목록
input_problems = []  # 입력 오류 문구
for i in range(count):
    c1, c2, c3 = st.columns([1, 2, 3])
    with c1:
        prepare(f"name_{i}", f"참여자{i + 1}")
        name = st.text_input("이름", key=f"_name_{i}", on_change=keep, args=[f"name_{i}"])
    with c2:
        prepare(f"query_{i}", "")
        query = st.text_input("출발지 검색", key=f"_query_{i}", on_change=keep, args=[f"query_{i}"],
                              placeholder="예: 서울대입구역, 홍대입구")
    search = get_search(i, query, demo_mode, stations)
    with c3:
        places = search["places"]
        if len(places) == 0:
            st.selectbox("검색 결과", ["(검색어를 입력하세요)" if query.strip() == "" else "(검색 결과 없음)"],
                         key=f"_empty_{i}", disabled=True)
        else:
            prepare(f"choice_{i}", 0)
            choice = st.selectbox("검색 결과", range(len(places)), format_func=lambda k, p=places: place_label(p[k]),
                                  key=f"_choice_{i}", on_change=keep, args=[f"choice_{i}"])
            chosen = places[choice]
            people.append({"name": name.strip(), "place": chosen["name"], "lat": chosen["lat"], "lon": chosen["lon"]})
        if search["notice"]:
            st.caption(search["notice"])

    if name.strip() == "":
        input_problems.append(f"{i + 1}번째 참여자의 이름을 입력하세요.")
    if len(places) == 0:
        input_problems.append(f"{i + 1}번째 참여자의 출발지를 검색해서 고르세요.")

names = [p["name"] for p in people]
if len(names) != len(set(names)):
    input_problems.append("참여자 이름이 겹칩니다. 서로 다른 이름을 써 주세요.")


# ---------------- 화면: 기준 선택 ----------------

st.subheader("2. 공평성 기준")
prepare("preset", "배려형")
preset = st.radio("어떤 장소가 공평한가요?", list(PRESET_DESCRIPTIONS.keys()), horizontal=True,
                  key="_preset", on_change=keep, args=["preset"])
st.caption(PRESET_DESCRIPTIONS[preset])

if preset == "맞춤형":
    s1, s2, s3 = st.columns(3)
    with s1:
        prepare("w_total", 5)
        w_total = st.slider("총합 중요도", 0, 10, key="_w_total", on_change=keep, args=["w_total"])
    with s2:
        prepare("w_max", 5)
        w_max = st.slider("최장 중요도", 0, 10, key="_w_max", on_change=keep, args=["w_max"])
    with s3:
        prepare("w_std", 5)
        w_std = st.slider("편차 중요도", 0, 10, key="_w_std", on_change=keep, args=["w_std"])
    weights = (w_total, w_max, w_std)
else:
    weights = PRESETS[preset]


# ---------------- 실행: 소요시간 표 만들기 (API 호출은 여기서만) ----------------

calls = count * NUM_CANDIDATES
button_help = f"후보역 {NUM_CANDIDATES}곳 × {count}명 = 대중교통 조회 {calls}회"
if st.button("🔍 공평한 약속 장소 찾기", type="primary", help=button_help):
    if input_problems:
        for problem in input_problems:
            st.error(problem)
    else:
        cands = find_candidates(stations, people, k=NUM_CANDIDATES)
        bar = st.progress(0.0, text="이동시간 조회 준비 중...")
        times, est, errors = build_time_table(people, cands, demo_mode=demo_mode, progress=bar)
        bar.empty()
        st.session_state["result"] = {"people": people, "cands": cands, "times": times, "est": est, "errors": errors}
        st.session_state.pop("selected_station", None)  # 새로 찾았으니 이전 확정은 취소


# ---------------- 결과 (보관된 표로 순위만 다시 계산) ----------------

if "result" not in st.session_state:
    st.stop()

result = st.session_state["result"]
r_people = result["people"]
cands = result["cands"].set_index("name")
times = result["times"]
est = result["est"]

st.divider()
st.subheader("3. 추천 결과")
st.caption(f"마지막으로 [찾기]를 누른 시점의 입력 기준입니다. 기준을 바꾸면 API 호출 없이 순위만 다시 계산합니다. (현재 기준: {preset})")

ranking = score_stations(times, weights)
if ranking is None:
    st.warning("중요도를 모두 0으로 두면 점수를 계산할 수 없습니다. 하나 이상 0보다 크게 해 주세요.")
    st.stop()

best = ranking.index[0]
best_row = cands.loc[best]

st.success(f"### 🏆 {best}역\n{best_row['lines']}")
m1, m2, m3 = st.columns(3)
m1.metric("이동시간 총합", f"{ranking.loc[best, '총합']:.0f}분")
m2.metric("가장 오래 걸리는 사람", f"{ranking.loc[best, '최장']:.0f}분")
m3.metric("이동시간 편차", f"{ranking.loc[best, '편차']:.1f}분")

num_est = int(est.sum().sum())
if num_est > 0:
    st.warning(f"이동시간 {num_est}칸(전체 {est.size}칸 중)은 카카오 API 대신 직선거리로 계산한 **추정치**입니다. "
               "(직선거리 ÷ 시속 20km + 대기·도보 10분)")
    if result["errors"]:
        with st.expander("API 오류 내용 보기"):
            for error in result["errors"]:
                st.write("- " + error)

col_chart, col_map = st.columns(2)

with col_chart:
    st.markdown(f"**{best}역까지 사람별 이동시간**")
    chart_df = pd.DataFrame({
        "참여자": times.columns,
        "이동시간(분)": times.loc[best].values,
        "구분": ["추정" if e else "실제" for e in est.loc[best]],
    })
    fig = px.bar(chart_df, x="참여자", y="이동시간(분)", color="구분", text="이동시간(분)",
                 color_discrete_map={"실제": "#3b82f6", "추정": "#9ca3af"})
    fig.add_hline(y=chart_df["이동시간(분)"].mean(), line_dash="dot",
                  annotation_text=f"평균 {chart_df['이동시간(분)'].mean():.0f}분")
    fig.update_layout(height=420, margin=dict(t=30, b=10))
    st.plotly_chart(fig)

with col_map:
    st.markdown("**지도** (파랑: 출발지, 빨간 별: 추천역)")
    fmap = folium.Map(location=[best_row["lat"], best_row["lon"]], zoom_start=11)
    for person in r_people:
        minutes = times.loc[best, person["name"]]
        folium.PolyLine([[person["lat"], person["lon"]], [best_row["lat"], best_row["lon"]]],
                        color="red", weight=3, opacity=0.5, tooltip=f"{person['name']}: {minutes}분").add_to(fmap)
        folium.Marker([person["lat"], person["lon"]], tooltip=f"{person['name']} ({person['place']})",
                      icon=folium.Icon(color="blue", icon="user")).add_to(fmap)
    folium.Marker([best_row["lat"], best_row["lon"]], tooltip=f"추천: {best}역",
                  icon=folium.Icon(color="red", icon="star")).add_to(fmap)
    # 모든 지점이 화면에 들어오게 지도 범위를 맞춘다
    lats = [p["lat"] for p in r_people] + [best_row["lat"]]
    lons = [p["lon"] for p in r_people] + [best_row["lon"]]
    fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    st_folium(fmap, height=420, use_container_width=True, returned_objects=[])

st.markdown("**상위 5개 후보역**")
top5 = ranking.head(5).copy()
top5["역"] = top5.index + "역"
top5["노선"] = [cands.loc[name, "lines"] for name in top5.index]
for person in r_people:  # 사람별 이동시간 열 (추정치는 * 표시)
    top5[person["name"]] = [
        f"{times.loc[s, person['name']]}*" if est.loc[s, person["name"]] else str(times.loc[s, person["name"]])
        for s in top5.index
    ]
top5["편차"] = top5["편차"].round(1)
top5["점수"] = top5["점수"].round(3)
columns = ["순위", "역", "노선", "총합", "최장", "편차", "점수"] + [p["name"] for p in r_people]
st.dataframe(top5[columns], hide_index=True)
st.caption("단위: 분. 점수는 0~1 (낮을수록 좋음). * 표시는 추정치.")


# ---------------- 확정 → 주변 장소로 ----------------

st.subheader("4. 약속 장소 확정")
top3 = list(ranking.index[:3])
c1, c2 = st.columns([3, 1])
with c1:
    pick = st.selectbox("상위 3개 중에서 고르세요", top3,
                        format_func=lambda s: f"{ranking.loc[s, '순위']}위 · {s}역 (최장 {ranking.loc[s, '최장']:.0f}분)")
with c2:
    st.write("")
    if st.button("이 역으로 확정"):
        st.session_state["selected_station"] = pick

if "selected_station" in st.session_state:
    st.success(f"✅ 약속 장소를 **{st.session_state['selected_station']}역**으로 확정했습니다.")
    st.page_link("pages/2_주변_장소.py", label="주변 카페·음식점 보러 가기", icon="☕")
