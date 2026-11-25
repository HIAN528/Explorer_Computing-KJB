# AI 활용 기록

| 날짜 | 발생한 문제/요청 | 활용한 도움 | 해결 방법 및 반영 내용 |
|---|---|---|---|
| 2026-11-25 | 2·3단계: 프로젝트 뼈대 만들기, 카카오 API 연결 테스트 앱 요청 | Claude Code로 폴더 구조·requirements.txt·.gitignore 생성, .venv 가상환경 구성, 테스트 앱 작성, git 초기화 | `app.py`에 키워드 검색 → 대중교통 경로 조회 테스트 앱 작성(최소 소요시간·환승·요금 표시, 원본 JSON expander). 모든 호출에 try/except와 timeout=10 적용. secrets 파일이 `.streamlit/` 폴더 밖에 `.streamlitsecrets.toml`이라는 이름으로 잘못 저장된 것을 발견해 두 이름 모두 .gitignore에 추가하고, 첫 커밋에서 제외된 것을 `git check-ignore`로 확인. 파일을 `.streamlit/secrets.toml`로 옮긴 뒤 서울대입구역 → 강남역 조회로 두 API 정상 동작 확인(14분·환승 0회·1,550원). 기존 수업 저장소 main에 10주차 과제가 있어, 충돌을 피하려고 별도 `where2meet` 브랜치로 push |
| 2026-11-25 | 4단계: 역 좌표 공공데이터 → stations.csv 전처리 | Claude Code로 공공데이터 출처 조사(국가철도공단 역사정보 XLSX), 원본 구조 분석, 데이터 오류 탐지, 전처리 스크립트 작성 | `prepare_data.py` 작성: 수도권 필터(1,099→796행) → 역·노선 이름 정리 → 좌표 오류 2건 수정(마곡·이촌, 위키백과 좌표) → 같은 이름 먼 역 구분(양평) → 환승역 합치기로 656개 역 `stations.csv` 생성. 하버사인 거리 함수는 `utils/candidates.py`에 만들어 재사용 |
| 2026-11-25 | 5단계: utils 4개 모듈(후보역·공평성·정산·카카오 API) 구현 | Claude Code로 모듈 설계(함수 입출력 형태 통일), 코드 작성, 모듈별 동작 확인 코드 작성·실행 | `candidates.py`(하버사인·후보 k개·중간점), `fairness.py`(min-max 정규화 가중합, 가중치 합 0이면 None), `settle.py`(그리디 정산), `kakao_api.py`(실패 시 (None, 오류) 반환, 추정치 대체, 소요시간 표 생성) 작성. 각 파일 맨 아래 `python -m utils.모듈명`으로 실행하는 확인 코드를 넣어 모두 통과 확인. 테스트 기댓값(서울역–강남 거리)을 잘못 잡은 것을 계산으로 확인해 수정 |
