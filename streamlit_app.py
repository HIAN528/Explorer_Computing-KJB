import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="10주차 과제", page_icon="🎓", layout="wide")

# ----------------------------
# 사이드바 메뉴
# ----------------------------
st.sidebar.header("📂 메뉴")
menu = st.sidebar.radio("페이지 선택", ["🙋 자기소개", "📅 수업시간표", "🗺️ 가보고 싶은 장소"])


# ----------------------------
# 1. 자기소개
# ----------------------------
def page_intro():
    st.title("🙋 자기소개")
    st.caption("F37.206 컴퓨팅 탐색: 실생활에서 활용하기 - 10주차 과제")

    st.header("안녕하세요! 저는 김종범입니다.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://api.dicebear.com/9.x/thumbs/png?seed=kimjongbeom", width=200,
                 caption="프로필 이미지")
    with col2:
        st.subheader("📌 기본 정보")
        st.markdown("""
- **이름**: 김종범
- **소속**: 서울대학교 화학교육과
""")

    st.subheader("💡 관심 분야")
    st.write("**화학**을 공부하면서, 학생들에게 화학을 더 쉽고 재미있게 가르치는 방법에 관심이 많습니다. "
             "Streamlit 같은 도구로 *데이터 시각화*와 웹 앱을 만들어 수업에 활용해 보고 싶습니다.")

    st.subheader("🎯 취미")
    st.markdown("""
1. 배드민턴 🏸
2. 게임하기 🎮
3. 음악 듣기 🎧
""")

    st.subheader("🛠️ 다룰 수 있는 것")
    st.code("print('Hello, Streamlit!')", language="python")

    st.subheader("📢 한마디")
    st.info("한 학기 동안 열심히 배워서 멋진 웹 앱을 만들고 싶습니다!")


# ----------------------------
# 2. 수업시간표
# ----------------------------
def page_timetable():
    st.title("📅 나의 수업시간표")
    st.caption("2026학년도 2학기")

    timetable = pd.DataFrame({
        "시간": ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"],
        "월": ["", "", "", "", "양자화학", "양자화학 / 기기분석", "기기분석", ""],
        "화": ["", "무기화학 2", "무기화학 2", "", "물리화학실험", "물리화학실험", "물리화학실험", "물리화학실험"],
        "수": ["", "", "", "", "양자화학", "양자화학 / 기기분석", "기기분석", ""],
        "목": ["", "무기화학 2", "무기화학 2", "배드민턴초급", "배드민턴초급", "", "", ""],
        "금": ["컴퓨팅 탐색", "컴퓨팅 탐색", "컴퓨팅 탐색", "화학교재연구 및 지도법", "화학교재연구 및 지도법",
              "화학교재연구 및 지도법", "", ""],
    }).set_index("시간")

    st.subheader("🗓️ 주간 시간표")
    st.table(timetable)

    st.subheader("📚 수강 과목 목록")
    courses = pd.DataFrame({
        "과목명": ["무기화학 2", "양자화학", "기기분석", "물리화학실험", "배드민턴초급",
                "컴퓨팅 탐색: 실생활에서 활용하기", "화학교재연구 및 지도법"],
        "요일": ["화, 목", "월, 수", "월, 수", "화", "목", "금", "금"],
        "시간": ["11:00~12:15", "14:00~15:15", "15:30~16:45", "14:00~17:50", "13:00~14:50",
               "10:00~12:50", "13:00~15:50"],
        "강의실": ["11-101", "28-301", "28-301", "13-105", "-", "26-104", "11-102"],
    })
    st.dataframe(courses, hide_index=True)

    st.metric(label="이번 학기 수강 과목", value=f"{len(courses)}과목")


# ----------------------------
# 3. 가보고 싶은 장소 (지도)
# ----------------------------
def page_map():
    st.title("🗺️ 가보고 싶은 장소")
    st.write("언젠가 꼭 가보고 싶은 국내 여행지를 지도에 표시했습니다.")

    # ← 원하는 장소로 수정 가능 (위도 lat, 경도 lon)
    places = pd.DataFrame({
        "place": ["제주 성산일출봉", "부산 해운대", "경주 불국사", "강릉 안목해변", "전주 한옥마을", "울릉도 독도전망대"],
        "lat": [33.4581, 35.1587, 35.7900, 37.7717, 35.8150, 37.4843],
        "lon": [126.9425, 129.1604, 129.3320, 128.9475, 127.1530, 130.9057],
        "reason": ["일출 보기", "바다 수영", "역사 탐방", "커피 거리", "한옥 체험", "섬 여행"],
    })

    st.subheader("📍 st.map으로 표시")
    st.map(places, size=3000, color="#FF4B4B")

    st.subheader("📍 PyDeck으로 표시 (점에 마우스를 올려보세요)")
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=places,
        get_position="[lon, lat]",
        get_radius=8000,
        get_color=[255, 75, 75],
        pickable=True,
    )
    tooltip = {"text": "장소: {place}\n이유: {reason}", "style": {"color": "white"}}
    view_state = pdk.ViewState(latitude=36.0, longitude=128.0, zoom=6, pitch=0)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

    with st.expander("📋 장소 목록 보기"):
        st.table(places[["place", "reason"]].rename(columns={"place": "장소", "reason": "가고 싶은 이유"}))


# ----------------------------
# 메뉴에 따라 페이지 표시
# ----------------------------
if menu == "🙋 자기소개":
    page_intro()
elif menu == "📅 수업시간표":
    page_timetable()
else:
    page_map()
