"""
분석 실험실: 왜 이 역이 공평한지 데이터로 보여준다. (API 호출 없음)

중간지점 찾기에서 만든 소요시간 표(st.session_state["result"])만으로
  1. 지도상 가운데 vs 추천역 비교
  2. 기준별 1위 역 비교표
  3. 후보역 트레이드오프 산점도
를 보여준다.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.candidates import centroid, nearest_station
from utils.fairness import PRESETS, score_stations, summarize

st.set_page_config(page_title="분석 실험실", page_icon="🔬", layout="wide")

st.title("🔬 분석 실험실")
st.caption("중간지점 찾기에서 조회한 이동시간만으로 분석합니다. 카카오 API를 다시 부르지 않습니다.")

# ---------------- 선행 데이터 확인 ----------------
if "result" not in st.session_state:
    st.info("분석할 결과가 없습니다. 먼저 중간지점 찾기에서 [공평한 약속 장소 찾기]를 실행해 주세요.")
    st.page_link("pages/1_중간지점_찾기.py", label="중간지점 찾기로 가기", icon="📍")
    st.stop()

result = st.session_state["result"]
people = result["people"]
cands = result["cands"].set_index("name")
times = result["times"]
est = result["est"]


def current_weights():
    """중간지점 찾기에서 고른 기준의 (이름, 가중치). 맞춤형 가중치가 모두 0이면 배려형으로."""
    preset = st.session_state.get("preset", "배려형")
    if preset == "맞춤형":
        weights = (st.session_state.get("w_total", 5), st.session_state.get("w_max", 5), st.session_state.get("w_std", 5))
        if sum(weights) > 0:
            return preset, weights
        st.caption("맞춤형 중요도가 모두 0이라 배려형 기준으로 분석합니다.")
        preset = "배려형"
    return preset, PRESETS[preset]


preset, weights = current_weights()
ranking = score_stations(times, weights)
best = ranking.index[0]
summary = summarize(times)

if est.any().any():
    st.warning(f"이동시간 {int(est.sum().sum())}칸은 직선거리 추정치입니다. 분석 결과도 그만큼 정확하지 않을 수 있습니다.")


# ---------------- 1. 지도상 가운데 vs 추천역 ----------------
st.header("1. 지도상 가운데는 공평할까?")
st.caption("참여자 위치의 평균(지도상 중간점)에서 가장 가까운 후보역과, 실제 이동시간으로 고른 추천역을 비교합니다.")

center_lat, center_lon = centroid(people)
middle = nearest_station(result["cands"], center_lat, center_lon)["name"]

compare = pd.DataFrame({
    "참여자": list(times.columns) * 2,
    "역": [f"지도상 가운데: {middle}역"] * len(times.columns) + [f"추천({preset}): {best}역"] * len(times.columns),
    "이동시간(분)": list(times.loc[middle]) + list(times.loc[best]),
})
fig = px.bar(compare, x="참여자", y="이동시간(분)", color="역", barmode="group", text="이동시간(분)",
             color_discrete_sequence=["#9ca3af", "#ef4444"])
fig.update_layout(height=380, margin=dict(t=30, b=10), legend_title_text="")
st.plotly_chart(fig)

c1, c2, c3 = st.columns(3)
c1.metric("최장 이동시간", f"{summary.loc[best, '최장']:.0f}분",
          delta=f"{summary.loc[best, '최장'] - summary.loc[middle, '최장']:+.0f}분 (가운데 대비)", delta_color="inverse")
c2.metric("이동시간 총합", f"{summary.loc[best, '총합']:.0f}분",
          delta=f"{summary.loc[best, '총합'] - summary.loc[middle, '총합']:+.0f}분", delta_color="inverse")
c3.metric("이동시간 편차", f"{summary.loc[best, '편차']:.1f}분",
          delta=f"{summary.loc[best, '편차'] - summary.loc[middle, '편차']:+.1f}분", delta_color="inverse")

if middle == best:
    st.caption(f"💡 이번에는 지도상 가운데({middle}역)가 {preset} 기준 추천역과 같습니다. "
               "출발지들이 노선으로 고르게 이어져 있으면 지도상 가운데도 공평할 수 있습니다.")
else:
    diff = summary.loc[middle, "최장"] - summary.loc[best, "최장"]
    if diff > 0:
        st.caption(f"💡 지도상 가운데인 {middle}역은 가장 오래 걸리는 사람이 {summary.loc[middle, '최장']:.0f}분이지만, "
                   f"추천역 {best}역은 {summary.loc[best, '최장']:.0f}분으로 {diff:.0f}분 짧습니다. "
                   "지하철 노선과 환승 때문에 직선거리로 가운데인 곳이 시간으로도 가운데인 것은 아닙니다.")
    else:
        st.caption(f"💡 지도상 가운데인 {middle}역과 추천역 {best}역은 최장 이동시간은 비슷하지만, "
                   f"{preset} 기준으로 총합·편차까지 따지면 {best}역이 더 낫습니다.")
st.caption("※ 이동시간을 아는 곳은 후보역뿐이므로, 지도상 중간점에서 가장 가까운 '후보역'을 가운데로 봅니다.")


# ---------------- 2. 기준별 1위 비교 ----------------
st.header("2. 기준에 따라 1위가 달라질까?")

rows = []
for name, w in PRESETS.items():
    top = score_stations(times, w).index[0]
    rows.append({"기준": name, "1위 역": f"{top}역", "총합(분)": summary.loc[top, "총합"],
                 "최장(분)": summary.loc[top, "최장"], "편차(분)": round(summary.loc[top, "편차"], 1)})
if preset == "맞춤형":
    rows.append({"기준": f"맞춤형 {weights}", "1위 역": f"{best}역", "총합(분)": summary.loc[best, "총합"],
                 "최장(분)": summary.loc[best, "최장"], "편차(분)": round(summary.loc[best, "편차"], 1)})
table = pd.DataFrame(rows)
st.dataframe(table, hide_index=True)

winners = set(table["1위 역"])
if len(winners) == 1:
    st.caption(f"💡 이번 모임은 어떤 기준으로 봐도 {table['1위 역'][0]}이 1위입니다. 고민할 필요가 없는 경우예요.")
else:
    st.caption(f"💡 기준에 따라 1위가 {len(winners)}곳으로 갈립니다. 모두의 시간을 아낄지(효율), "
               "가장 먼 사람을 배려할지(배려), 다 같이 비슷하게 움직일지(균등)에 따라 '공평한 곳'이 달라집니다.")


# ---------------- 3. 트레이드오프 산점도 ----------------
st.header("3. 후보역 한눈에 보기: 트레이드오프")

scatter = summary.copy()
scatter["역"] = scatter.index
scatter["편차"] = scatter["편차"].round(1)
scatter["표시"] = ["추천역" if s == best else ("지도상 가운데" if s == middle else "후보역") for s in scatter.index]
fig2 = px.scatter(scatter, x="총합", y="최장", color="편차", symbol="표시", text="역",
                  hover_data={"역": True, "총합": True, "최장": True, "편차": True, "표시": False},
                  color_continuous_scale="Viridis_r",
                  symbol_map={"추천역": "star", "지도상 가운데": "diamond", "후보역": "circle"},
                  labels={"총합": "이동시간 총합(분)", "최장": "최장 이동시간(분)", "편차": "편차(분)"})
fig2.update_traces(marker=dict(size=14, line=dict(width=1, color="white")), textposition="top center")
fig2.update_layout(height=480, margin=dict(t=30, b=10),
                   legend=dict(orientation="h", y=-0.2, title_text=""))
st.plotly_chart(fig2)

# 해석 문구: 효율형 1위(총합 최소)와 배려형 1위(최장 최소)가 같은지
# (동점일 때도 위 비교표와 같은 역을 가리키도록 score_stations의 순위를 쓴다)
min_total = score_stations(times, PRESETS["효율형"]).index[0]
min_max = score_stations(times, PRESETS["배려형"]).index[0]
if min_total == min_max:
    st.caption(f"💡 왼쪽 아래로 갈수록 좋은 역입니다. {min_total}역이 총합과 최장 모두 가장 작아서 "
               "효율과 배려 사이에 갈등이 없습니다.")
else:
    st.caption(f"💡 왼쪽 아래로 갈수록 좋은 역입니다. 총합이 가장 작은 곳은 {min_total}역, "
               f"최장이 가장 작은 곳은 {min_max}역으로 서로 다릅니다. "
               "한쪽을 좋게 하면 다른 쪽이 나빠지는 '트레이드오프'가 있다는 뜻입니다. 색이 밝을수록 편차가 작습니다.")
