# AI 활용 기록

| 날짜 | 발생한 문제/요청 | 활용한 도움 | 해결 방법 및 반영 내용 |
|---|---|---|---|
| 2026-11-25 | 2·3단계: 프로젝트 뼈대 만들기, 카카오 API 연결 테스트 앱 요청 | Claude Code로 폴더 구조·requirements.txt·.gitignore 생성, .venv 가상환경 구성, 테스트 앱 작성, git 초기화 | `app.py`에 키워드 검색 → 대중교통 경로 조회 테스트 앱 작성(최소 소요시간·환승·요금 표시, 원본 JSON expander). 모든 호출에 try/except와 timeout=10 적용. secrets 파일이 `.streamlit/` 폴더 밖에 `.streamlitsecrets.toml`이라는 이름으로 잘못 저장된 것을 발견해 두 이름 모두 .gitignore에 추가하고, 첫 커밋에서 제외된 것을 `git check-ignore`로 확인. 파일을 `.streamlit/secrets.toml`로 옮긴 뒤 서울대입구역 → 강남역 조회로 두 API 정상 동작 확인(14분·환승 0회·1,550원) |
