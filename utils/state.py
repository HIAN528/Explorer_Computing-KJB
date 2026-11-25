"""
여러 페이지에서 함께 쓰는 화면 상태 도우미

Streamlit 여러 페이지 앱에서는 다른 페이지에 다녀오면 입력칸(위젯)의 값이 지워진다.
그래서 위젯 값은 "_이름" 키에 두고, 바뀔 때마다 "이름" 키(일반 값)에 복사해 둔다.
페이지를 다시 열면 "이름" 키의 값을 위젯에 다시 넣어 준다.

    prepare("count", 3)                      # 위젯을 그리기 전에
    st.number_input(..., key="_count", on_change=keep, args=["count"])
    count = st.session_state["count"]        # 값은 밑줄 없는 키에서 읽는다
"""

import streamlit as st


def prepare(key, default):
    """위젯을 그리기 전에 호출: 저장해 둔 값(없으면 기본값)을 위젯 키에 넣는다."""
    if key not in st.session_state:
        st.session_state[key] = default
    st.session_state["_" + key] = st.session_state[key]


def keep(key):
    """위젯 값이 바뀌면 호출(on_change): 위젯 값을 일반 키에 복사한다."""
    st.session_state[key] = st.session_state["_" + key]


# 예시 참여자: 중간지점 찾기의 [예시 채우기]와 홈의 [예시로 체험하기]에서 함께 쓴다
EXAMPLE = [
    ("민수", "서울대입구역"),
    ("지수", "노원역"),
    ("철수", "천호역"),
]


def fill_example():
    """예시 참여자 3명을 중간지점 찾기 입력칸에 채운다. (값은 밑줄 없는 키에 넣고, 페이지가 prepare로 위젯에 옮긴다)"""
    st.session_state["count"] = len(EXAMPLE)
    for i, (name, query) in enumerate(EXAMPLE):
        st.session_state[f"name_{i}"] = name
        st.session_state[f"query_{i}"] = query
        st.session_state[f"choice_{i}"] = 0


def demo_mode_toggle():
    """사이드바에 '데모 모드' 토글을 그리고, 현재 값(True/False)을 돌려준다.

    app.py에서 한 번만 호출한다. app.py는 어떤 페이지를 보든 먼저 실행되므로 모든 페이지에 토글이 보인다.
    값은 st.session_state["demo_mode"]에 저장되고, 각 페이지는 그 값을 읽어 쓴다.
    """
    with st.sidebar:
        prepare("demo_mode", False)
        st.toggle("데모 모드 (API 호출 안 함)", key="_demo_mode", on_change=keep, args=["demo_mode"],
                  help="켜면 카카오 API를 부르지 않습니다. 이동시간은 직선거리 추정치, "
                       "출발지는 역 이름으로만 검색하고, 주변 장소 검색은 쉽니다. "
                       "API 키가 없거나 호출 한도를 넘었을 때 발표·시연용으로 씁니다.")
    return st.session_state["demo_mode"]
