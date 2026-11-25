"""
정산 페이지: 누가 누구에게 얼마를 보내면 되는지

- 중간지점 찾기의 참여자 이름을 자동으로 불러온다. (없으면 직접 입력)
- st.data_editor 표에 각자 낸 금액을 적으면, 그리디 방식으로 송금 목록을 만든다.
- 사람별 잔액(+ 받을 돈 / − 낼 돈)을 막대그래프로 보여준다.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.settle import settle
from utils.text import md_escape

st.set_page_config(page_title="정산", page_icon="💰", layout="wide")

st.title("💰 정산하기")
st.caption("각자 낸 금액을 적으면, 송금 횟수가 적도록 누가 누구에게 얼마를 보내면 되는지 계산합니다.")


def initial_table():
    """처음 보여줄 표: 중간지점 찾기의 참여자 이름 (없으면 빈 이름 2줄)"""
    if "result" in st.session_state:
        names = [p["name"] for p in st.session_state["result"]["people"]]
    else:
        names = ["", ""]
    return pd.DataFrame({"이름": names, "낸 금액": [0] * len(names)})


def reset_table():
    """[참여자 다시 불러오기] 버튼: 저장된 표를 지우고 처음 상태로"""
    st.session_state.pop("settle_saved", None)
    st.session_state.pop("_settle_editor", None)


if "result" in st.session_state:
    st.info("중간지점 찾기의 참여자를 불러왔습니다. 낸 금액만 적으면 됩니다.")
else:
    st.info("중간지점 찾기 결과가 없어 직접 입력합니다. 표 아래쪽의 + 로 사람을 추가할 수 있습니다.")
    st.page_link("pages/1_중간지점_찾기.py", label="중간지점 찾기로 가기", icon="📍")

# ---------------- 입력 표 ----------------
# 다른 페이지에 다녀와도 입력이 남도록, 편집한 표를 settle_saved에 저장해 둔다.
# 페이지에 새로 들어왔을 때(편집기 상태가 없을 때)만 저장된 표를 시작 값으로 쓴다.
if "_settle_editor" not in st.session_state:
    st.session_state["settle_base"] = st.session_state.get("settle_saved", initial_table())

col_table, col_button = st.columns([3, 1])
with col_table:
    edited = st.data_editor(
        st.session_state["settle_base"],
        key="_settle_editor",
        num_rows="dynamic",  # 행 추가·삭제 가능
        hide_index=True,
        column_config={
            "이름": st.column_config.TextColumn("이름", required=True),
            # format="localized": 45000 → 45,000 처럼 천 단위 쉼표
            "낸 금액": st.column_config.NumberColumn("낸 금액 (원)", min_value=0, step=100, format="localized"),
        },
    )
st.session_state["settle_saved"] = edited
with col_button:
    st.button("참여자 다시 불러오기", on_click=reset_table,
              help="표를 지우고 중간지점 찾기의 참여자 이름으로 다시 채웁니다.")

# ---------------- 입력 정리·검사 ----------------
table = edited.copy()
table["이름"] = table["이름"].fillna("").astype(str).str.strip()
table["낸 금액"] = table["낸 금액"].fillna(0)
# 금액은 적었는데 이름을 빠뜨린 줄은 조용히 빠지지 않도록 알려 준다
no_name = table[(table["이름"] == "") & (table["낸 금액"] != 0)]
if len(no_name) > 0:
    st.warning(f"이름이 빈 줄 {len(no_name)}개(금액 {int(no_name['낸 금액'].sum()):,}원)는 계산에서 뺐습니다. "
               "포함하려면 이름을 적어 주세요.")
table = table[table["이름"] != ""]  # 이름이 빈 줄은 빼고 계산

if len(table) < 2:
    st.warning("정산하려면 이름이 있는 사람이 2명 이상 필요합니다.")
    st.stop()
if table["이름"].duplicated().any():
    st.error("이름이 겹칩니다. 서로 다른 이름을 써 주세요.")
    st.stop()

names = list(table["이름"])
paid = [int(x) for x in table["낸 금액"]]
total = sum(paid)
if total == 0:
    st.info("낸 금액을 입력하면 정산 결과가 나옵니다.")
    st.stop()

# ---------------- 결과 ----------------
transfers, balances = settle(names, paid)

st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("총액", f"{total:,}원")
m2.metric("1인당", f"{total / len(names):,.0f}원")
m3.metric("송금 횟수", f"{len(transfers)}번")

col_list, col_chart = st.columns([1, 1])

with col_list:
    st.subheader("송금 목록")
    if len(transfers) == 0:
        st.success("모두 똑같이 냈습니다. 보낼 돈이 없어요!")
    for t in transfers:
        # 이름은 사용자가 입력한 글자이므로 마크다운 기호가 있어도 글자 그대로 보이게 한다
        st.markdown(f"- **{md_escape(t['from'])}** → **{md_escape(t['to'])}** &nbsp; {t['amount']:,}원")
    st.caption("1원 단위로 반올림하므로, 나누어떨어지지 않으면 몇 원 차이가 날 수 있습니다.")

with col_chart:
    st.subheader("사람별 잔액")
    chart_df = pd.DataFrame({
        "이름": list(balances.keys()),
        "잔액(원)": list(balances.values()),
    })
    chart_df["구분"] = ["받을 돈" if b > 0 else ("낼 돈" if b < 0 else "없음") for b in chart_df["잔액(원)"]]
    fig = px.bar(chart_df, x="이름", y="잔액(원)", color="구분", text="잔액(원)",
                 color_discrete_map={"받을 돈": "#16a34a", "낼 돈": "#dc2626", "없음": "#9ca3af"})
    # 막대 밖에 가로로 금액 표시 (+22,500원 / -22,500원)
    fig.update_traces(texttemplate="%{y:+,}원", textposition="outside", textangle=0, cliponaxis=False)
    fig.add_hline(y=0, line_color="gray")
    fig.update_layout(height=380, margin=dict(t=30, b=10))
    st.plotly_chart(fig)
    st.caption("잔액 = 낸 돈 − 1인당 금액. 양수(+)는 돌려받을 돈, 음수(−)는 더 내야 할 돈입니다.")
