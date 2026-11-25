"""
화면 문구 도우미: 사용자가 입력한 글자를 화면 문구에 안전하게 넣기

Streamlit의 st.markdown, st.warning 같은 문구는 글자를 마크다운으로 해석한다.
그래서 이름에 [글](주소)를 쓰면 링크가 되고, **를 쓰면 굵은 글씨가 된다.
사용자가 입력한 글자는 md_escape로 특수문자 앞에 \\를 붙여 '글자 그대로' 보이게 한다.

(HTML 태그는 Streamlit이 기본으로 막아 준다.
 folium 지도 툴팁은 HTML로 그려지므로 파이썬 기본 모듈의 html.escape를 쓴다.)
"""

# 마크다운에서 특별한 뜻이 있는 글자들 (\$는 Streamlit에서 수식 기호)
MARKDOWN_SPECIAL = "\\`*_{}[]()#+-.!|~<>$"


def md_escape(text):
    """마크다운 특수문자 앞에 \\를 붙인다.  예) "[민수](x)" → "\\[민수\\]\\(x\\)" (화면에는 [민수](x) 그대로)"""
    result = ""
    for ch in str(text):
        if ch in MARKDOWN_SPECIAL:
            result += "\\" + ch
        else:
            result += ch
    return result


# ---------------- 동작 확인: python -m utils.text ----------------
if __name__ == "__main__":
    assert md_escape("민수") == "민수"
    assert md_escape("**굵게**") == "\\*\\*굵게\\*\\*"
    assert md_escape("[클릭](https://a.b)") == "\\[클릭\\]\\(https://a\\.b\\)"
    print(md_escape("<b>민수</b> $10"))
    print("text.py 확인 완료")
