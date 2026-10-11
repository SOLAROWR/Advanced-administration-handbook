---
description: "[Action2-④] 실적 결과 분석 — Beat/Miss 여부와 Thesis 채점"
argument-hint: "<종목명> 예) HD현대일렉트릭"
---
대상 종목: **$ARGUMENTS**

CLAUDE.md 규칙을 따르세요. 먼저 아래 파일을 읽습니다:
- `reports/` 의 가장 최근 `earnings-preview_<종목>` 보고서 (채점 기준표)
- `theses/<종목>.md`

웹 검색으로 **가장 최근 발표된 실적**을 확인한 뒤:

1. **Beat / Miss 표** — 항목 | 컨센서스 | 실제 | 차이(%) | 판정(Beat/In-line/Miss)
2. **체크포인트 채점** — earnings-preview 에서 정한 5개 기준 각각 좋은/나쁜 신호 판정
3. **경영진 코멘트·가이던스 변화** 핵심 3줄
4. **시장 반응** — 발표 후 주가 변화와 이유
5. **Thesis 채점** — 핵심 가정 4개 각각 ✅/⚠️/❌ 갱신, 훼손 조건 해당 여부
6. **결론** — 보유 유지 / 비중 확대 검토 / 비중 축소 검토 / 재검토 중 하나와 이유

`theses/<종목>.md` 의 상태 표와 점검 기록을 업데이트하고,
결과를 `reports/<오늘날짜>_earnings_<종목>.md` 로 저장하세요.
