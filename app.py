"""
where2meet 시작 파일: 페이지 목록(사이드바 메뉴)을 정하고, 모든 페이지에 공통인 데모 모드 토글을 그린다.

실행: streamlit run app.py

st.navigation으로 페이지를 직접 등록하면 사이드바에 파일 이름(app, 1_중간지점_찾기 …) 대신
원하는 이름(홈, 중간지점 찾기 …)과 아이콘을 보여줄 수 있다.
이 파일은 어떤 페이지를 보든 매번 먼저 실행되므로, 데모 모드 토글은 여기서 한 번만 그리면 된다.
"""

import streamlit as st

from utils.state import demo_mode_toggle

pages = [
    st.Page("pages/0_홈.py", title="홈", icon="🚇", default=True),
    st.Page("pages/1_중간지점_찾기.py", title="중간지점 찾기", icon="📍"),
    st.Page("pages/2_주변_장소.py", title="주변 장소", icon="☕"),
    st.Page("pages/3_정산.py", title="정산", icon="💰"),
    st.Page("pages/4_분석_실험실.py", title="분석 실험실", icon="🔬"),
]

current_page = st.navigation(pages)  # 사이드바 메뉴를 만들고, 지금 보고 있는 페이지를 돌려준다
demo_mode_toggle()                    # 모든 페이지 공통 사이드바 토글
current_page.run()                    # 선택한 페이지 파일을 실행한다
