# 문제 해결 기록

## 1. secrets.toml 파일 위치가 잘못됨 (2026-11-25)

- **증상:** 테스트 앱 실행 시 "API 키를 찾지 못했습니다" 안내가 뜸.
- **원인:** 키 파일이 `.streamlit/secrets.toml`이 아니라 프로젝트 맨 위에
  `.streamlitsecrets.toml`이라는 이름으로 저장되어 있었다 (폴더 구분자 `/`가 빠짐).
  Streamlit은 `.streamlit` 폴더 안의 `secrets.toml`만 읽는다.
- **해결:** 파일을 `.streamlit/secrets.toml`로 옮겼다. 키가 실수로 커밋되지 않도록
  `.gitignore`에 두 이름을 모두 적고, `git check-ignore -v`로 제외 여부를 확인했다.
- **결과:** 옮긴 뒤 "API 키를 불러왔습니다"가 표시되고, 서울대입구역 → 강남역 조회가
  정상 동작했다 (14분, 환승 0회, 1,550원, SUBWAY, 경로 14개 중 최단).
