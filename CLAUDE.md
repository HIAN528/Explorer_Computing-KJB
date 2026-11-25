# where2meet — 공평한 약속장소 찾기 웹앱

컴퓨팅 탐색 수업 기말 프로젝트(Streamlit 웹앱). 마감: **2026-12-13(일)**.
사용자는 화학교육과 학생으로, Python 기초와 Streamlit을 수업에서 배운 수준이다.

## 앱 개요

여러 명의 출발지를 입력하면, 버스·지하철을 포함한 실제 대중교통 이동시간을 기준으로
모두에게 공평한 약속 장소(지하철역)를 추천한다. 주변 장소 추천과 정산까지 한 흐름으로 이어진다.

- 차별점: 기존 서비스(위밋플레이스 등)는 답을 하나만 준다. 이 앱은 사용자가 공평성 기준을
  고르고, 기준에 따라 결과가 어떻게 달라지는지 비교해서 보여준다.
- 평가 기준: 구현 규모, 기능 간 연계성, 기술 난이도, 사용 편의성, 실행 안정성.

## 작업 원칙 (중요)

1. **학생이 이해하고 설명할 수 있는 코드.** 보고서에 전체 소스코드를 넣고 설명해야 한다.
   - 지나치게 영리한 코드, 불필요한 추상화, 클래스 남용 금지. 함수 위주로 단순하게.
   - 주석과 docstring, 화면 문구는 **한국어**.
   - 새 개념(예: session_state 재실행 구조, 정규화)을 쓰면 작업 후 짧게 설명해 준다.
2. **한 번에 한 단계씩.** 아래 "진행 단계" 순서를 따르고, 각 단계 끝에 실행해서 확인할 방법을 알려준다.
3. **API 키는 절대 코드나 커밋에 넣지 않는다.** `st.secrets["KAKAO_REST_KEY"]`로만 읽는다.
   `.streamlit/secrets.toml`은 사용자가 직접 작성하며, Claude는 이 파일을 읽거나 출력하지 않는다.
4. **카카오 API 결과를 파일·DB에 저장하지 않는다.** 카카오 정책상 실시간 호출만 허용된다.
   `st.cache_data`로 카카오 응답을 캐시하지 말 것. (공공데이터인 `data/stations.csv`는 캐시해도 됨)
   한 세션 안에서 화면 표시를 위해 `st.session_state`에 잠시 들고 있는 것은 괜찮다.
5. **API가 실패해도 앱이 멈추지 않는다.** 모든 외부 호출은 try/except, 실패 시 대체값 + 안내 문구.
6. **AI 활용 기록.** 작업 세션이 끝날 때마다 `docs/ai_log.md` 표에 한 줄 추가한다
   (날짜 | 발생한 문제/요청 | 활용한 도움 | 해결 방법 및 반영 내용). 보고서 필수 항목이다.
   실제로 부딪힌 오류와 해결 과정은 `docs/troubleshooting.md`에도 짧게 남긴다 (보고서 "문제 해결 과정"용).

## 폴더 구조

```
where2meet/
├── app.py                  # 시작 파일: st.navigation으로 페이지 목록(사이드바 이름·아이콘) 등록 + 데모 모드 토글
├── pages/
│   ├── 0_홈.py              # 홈: 한 문장 소개, [약속 장소 찾기]·[예시로 체험하기] 버튼, 사용법, 기준 설명
│   ├── 1_중간지점_찾기.py    # 메인
│   ├── 2_주변_장소.py
│   ├── 3_정산.py
│   └── 4_분석_실험실.py
├── utils/
│   ├── __init__.py
│   ├── kakao_api.py        # 카카오 API 호출 (장소 검색, 대중교통 시간, 주변 장소) + 소요시간 표
│   ├── candidates.py       # 하버사인 거리, 후보역 추출, 중심점
│   ├── fairness.py         # 공평성 점수, 프리셋
│   ├── settle.py           # 정산 알고리즘
│   ├── state.py            # 페이지 이동 후 입력값 유지(prepare/keep), 데모 모드 토글, 예시 채우기(fill_example)
│   └── text.py             # 사용자 입력을 마크다운 문구에 넣을 때 특수문자 처리(md_escape)
├── data/stations.csv       # 지하철역 name, lines, lat, lon (공공데이터 전처리 결과)
├── prepare_data.py         # 원본 공공데이터 → stations.csv 전처리 스크립트
├── docs/                   # ai_log.md, troubleshooting.md
├── .streamlit/secrets.toml # (git 제외) KAKAO_REST_KEY = "..."
├── .gitignore              # .venv/, __pycache__/, .streamlit/secrets.toml
└── requirements.txt        # streamlit, requests, pandas, plotly, folium, streamlit-folium (로컬에서 확인한 버전으로 고정)
```

### 사용자 입력 표시 규칙 (보안 점검 결과)
- folium 툴팁은 HTML로 그려지므로 사용자 입력·카카오 장소 이름은 `html.escape()`로 감싼다.
- `st.markdown`·`st.warning` 등 마크다운 문구에 사용자 입력을 넣을 때는 `md_escape()`를 쓴다.
- 카카오맵 링크는 `safe_link()`로 https 주소만 쓴다. 카카오 응답 해석은 try/except로 감싼다.

## 핵심 로직: 2단계 탐색

1. **후보 추리기 (API 호출 없음):** `stations.csv`의 모든 역에 대해 참여자별 직선거리(하버사인)를 구하고,
   "가장 먼 사람까지의 거리"가 짧은 순(동점이면 총거리)으로 상위 k=10개 역을 후보로 뽑는다.
2. **실제 이동시간 (카카오 API):** 후보역 × 참여자마다 대중교통 소요시간을 조회해
   "행=후보역, 열=참여자, 값=분" 표를 만든다. 호출 수 = 참여자 수 × k (예: 4명 × 10 = 40회).
3. **공평성 점수:** 역별 총합·최장·편차(표준편차, ddof=0)를 0~1로 min-max 정규화 후 가중합. 낮을수록 좋음.
   - 효율형 (1,0,0) / 배려형 (0,1,0) / 균등형 (0,0,1) / 맞춤형 (슬라이더)
   - 가중치 합이 0이면 계산하지 않고 안내 문구.
4. **API 호출과 순위 계산 분리:** 소요시간 표는 버튼을 눌렀을 때 한 번만 만들고 session_state에 보관.
   기준·슬라이더를 바꾸면 API 재호출 없이 순위만 다시 계산한다. (보고서의 핵심 설계 포인트)

### 좌표 규칙
코드 전체에서 좌표는 `lat`(위도), `lon`(경도)로 통일한다. 카카오 API의 `x`=경도, `y`=위도이며
이 변환은 `kakao_api.py` 안에서만 한다.

### API 실패 시 대체 계산
직선거리(km) / 20 km/h × 60 + 10분 (평균 시속 20km + 대기·도보 10분 가정). 결과에 "추정" 표시.
사이드바 "데모 모드" 토글이 켜져 있으면 API를 호출하지 않고 이 추정치만 쓴다.

## 카카오 API 명세 (요약)

모두 `GET`, 헤더 `Authorization: KakaoAK {REST_API_KEY}`, timeout=10.

| 용도 | URL | 주요 파라미터 | 주요 응답 |
|---|---|---|---|
| 키워드 장소 검색 | `https://dapi.kakao.com/v2/local/search/keyword.json` | `query`, `size`(1~15) | `documents[]`: `place_name`, `address_name`, `x`, `y`, `place_url` |
| 카테고리 장소 검색 | `https://dapi.kakao.com/v2/local/search/category.json` | `category_group_code`(CE7 카페, FD6 음식점), `x`, `y`, `radius`(m) 또는 `rect`(사각형 범위), `sort=distance`, `page`(1~3) | `documents[]`: `id`, `place_name`, `distance`, `category_name`, `place_url`, `x`, `y` |
| 대중교통 경로 조회 | `https://dapi.kakao.com/v2/routing/publictraffic` | `start_x`, `start_y`, `end_x`, `end_y` (WGS84 경도/위도) | `status`, `routes[].properties.totalTime`(초), `transfers`, `fare.value`(원), `type`(BUS/SUBWAY/BUS_AND_SUBWAY), `routes[].steps[]` |

- 대중교통 `status` 값: `OK`, `STARTNODES_NULL`, `ENDNODES_NULL`, `EQUAL_POINTS`, `INVALID_REQUEST`, `NO_RESULTS`.
  `EQUAL_POINTS`(출발지 = 도착지)는 0분으로 처리. `routes`는 `OK`일 때만 있음.
- 여러 경로 중 `totalTime`이 가장 짧은 것을 그 구간의 소요시간으로 쓴다.
- 출발 시각 파라미터는 없다 (시간대별 차이 미반영 → 보고서 한계점).
- 오류 `API limit has been exceeded`(code -10)는 쿼터 소진/테스트앱 제한.

## 페이지 간 연결 (st.session_state)

| 키 | 내용 | 만드는 곳 | 쓰는 곳 |
|---|---|---|---|
| `result` | `{"people", "cands", "times", "est", "errors"}` (est = 추정값 여부 표, errors = API 오류 문구) | 중간지점 찾기 | 분석 실험실, 정산 |
| `selected_station` | 확정한 역 이름 | 중간지점 찾기 | 주변 장소 |
| `demo_mode` | 데모 모드 여부 (사이드바 토글, `app.py`에서 한 번만 그림) | app.py | 중간지점 찾기, 주변 장소 |

위젯 값은 `_키` 에 두고 `on_change`로 `키` 에 복사한다 (`prepare`/`keep`). 다른 페이지에 다녀와도 입력이 남게 하기 위함.

선행 데이터가 없는 페이지는 오류 대신 안내 문구 + `st.page_link`로 이전 페이지 안내.

## 페이지별 요구사항

- **홈:** 앱 소개, "왜 지도상 가운데가 공평하지 않은가" 예시, 사용 순서, 기준 4종 설명, 페이지 링크.
  (과제 필수: 목적, 주요 기능, 사용 방법이 웹앱 안에 있어야 함)
- **중간지점 찾기:** 참여자 2~6명(이름 + 출발지 검색 → 검색 결과 5개 중 selectbox 선택,
  입력이 바뀔 때만 재검색) → 기준 선택 → 실행(진행률 표시) → 추천역, 추정값 안내,
  사람별 이동시간 막대그래프(plotly), folium 지도(출발지 파랑, 추천역 빨강 별, 연결선,
  `st_folium(..., returned_objects=[])`), 상위 5개 표, 상위 5개 중 확정 selectbox.
- **주변 장소:** 카페/음식점 선택, 반경 300~1000m, 표(이름·거리·종류·카카오맵 링크) + 지도.
  카카오는 한 조건에 최대 45곳만 주므로 가까운 45곳 + 원을 3×3 칸(`rect`)으로 나눠 칸마다 검색(최대 450곳, 호출 최대 30번).
  메뉴 키워드 검색은 관련도순 45곳.
- **정산:** 참여자 자동 불러오기(없으면 직접 입력), `st.data_editor`로 이름/낸 금액,
  송금 목록("민수 → 지수 15,000원"), 잔액 막대그래프(+받을 돈/−낼 돈). 그리디 방식.
- **분석 실험실 (API 재호출 없음):** 지도상 중간점(centroid)에 가장 가까운 후보역 vs 추천역 비교,
  기준별 1위 역 비교표, 후보역 트레이드오프 산점도(x=총합, y=최장, 색=편차), 각 차트 해석 캡션.

## 진행 단계 (일정)

| 단계 | 내용 | 기한 |
|---|---|---|
| 2 | 폴더 구조, requirements, .gitignore, git 초기화 | 11/26 |
| 3 | API 연결 테스트 앱(app.py 임시) → 로컬 확인 → Streamlit Cloud 첫 배포 확인 | 11/27 |
| 4 | 역 좌표 공공데이터 → prepare_data.py → stations.csv | 11/28 |
| 5 | utils 4개 모듈 + 간단한 동작 확인 | 12/1 |
| 6 | 페이지 구현 (메인 → 주변 장소 → 정산 → 분석 실험실 → 홈 → 데모 모드) | 12/7 |
| 7 | 최종 배포, 예외 입력 테스트 | 12/9 |
| 8 | 보고서(.ipynb) 작성 | 12/12 |

## 실행

```bash
source .venv/bin/activate      # Windows: .venv\Scripts\activate
streamlit run app.py
```
