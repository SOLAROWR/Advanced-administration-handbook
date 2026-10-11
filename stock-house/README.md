# 📈 1인 투자 하우스 (클로드 주식 리서치 자동화 툴)

Anthropic의 [financial-services-plugins](https://github.com/anthropics/financial-services-plugins) **Equity Research** 워크플로우를 참고해서,
**한국어 + 한국 주식**에 맞게 만든 클로드 슬래시 커맨드 모음입니다.

> ⚠️ 이 도구는 **매매 주문을 하지 않습니다.** 리서치·기록·아침 요약만 합니다. 투자 판단은 본인 책임입니다.

---

## 🗂 폴더 구성

```
stock-house/
├── CLAUDE.md            ← 클로드가 지키는 공통 규칙 (한국어, 출처 표기 등)
├── portfolio.md         ← ✏️ 내 보유/관심 종목 (여기만 고치면 됨)
├── theses/              ← 종목별 투자 논리가 자동 저장되는 곳
├── reports/             ← 모든 분석 보고서가 날짜별로 자동 저장되는 곳
└── .claude/commands/    ← 9개 슬래시 커맨드
```

---

## 🚀 처음 사용하는 법 (3단계)

1. **Claude Code 를 이 `stock-house` 폴더에서 엽니다.**
   (터미널이라면 `cd stock-house` 후 `claude` 입력)
2. **`portfolio.md` 를 열어 예시 줄을 내 종목으로 바꿉니다.**
3. 입력창에 `/` 를 치면 아래 커맨드 목록이 나옵니다. 골라서 실행하세요.

---

## 🔁 워크플로우

### Action 1: 종목 탐색 (새 종목 찾을 때)

| 순서 | 커맨드 | 하는 일 | 입력 예시 |
|---|---|---|---|
| ① | `/sector` | 섹터 조감 | `/sector AI가 전기를 많이 쓴다는데` |
| ② | `/screen` | 종목 압축 | `/screen 전력 인프라, 구조적으로 매력적인 종목` |
| ③ | `/earnings-analysis` | 숫자로 채점 | `/earnings-analysis HD현대일렉트릭` |
| ④ | `/earnings-preview` | 채점 기준 수립 | `/earnings-preview HD현대일렉트릭` |
| ⑤ | `/initiate-coverage` | 매수 결정 (목표가 보고서) | `/initiate-coverage HD현대일렉트릭` |

### Action 2: 추적 관찰 (산 뒤에)

| 순서 | 커맨드 | 하는 일 |
|---|---|---|
| ① | `/thesis 종목명` | 핵심 가정 4개 + 훼손 조건 확정 → `theses/` 에 저장 |
| ② | `/catalysts 종목명` | 앞으로 3개월 이벤트 캘린더 (비우면 보유 종목 전체) |
| ③ | `/earnings-preview 종목명` | 이번 분기 체크포인트 |
| ④ | `/earnings 종목명` | 실적 발표 후 Beat/Miss + Thesis 채점 |

### Action 3: 자동화 루틴 (매일 아침)

| 커맨드 | 하는 일 |
|---|---|
| `/morning-note` | 전체 시장 동향 · 섹터 이슈 · 보유 종목 영향 체크를 5분 요약 |

---

## ⏰ 매일 아침 자동 실행하기

- **Claude Code (웹/앱)**: 클로드에게 *"평일 아침 7시 50분마다 /morning-note 실행해줘"* 라고 말하면 예약(Routine)을 만들어 줍니다.
- **Claude 데스크톱 Cowork**: 예약 작업(Scheduled task)에 `/morning-note` 를 등록하세요.

---

## 💡 공식 플러그인도 함께 쓰고 싶다면

Claude Code 입력창에 아래 두 줄을 입력하면 Anthropic 공식 금융 플러그인을 설치할 수 있습니다 (영어 기반).

```
/plugin marketplace add anthropics/financial-services-plugins
/plugin
```
목록에서 **equity-research** 를 선택해 설치합니다.
이 폴더의 커맨드는 공식 플러그인 없이도 독립적으로 동작합니다.

---

## 📺 유튜브 / 블로그 활용 팁

- `reports/` 에 쌓인 보고서는 그대로 블로그(stiwp.kr, 네이버 블로그) 초안으로 쓸 수 있습니다.
- `/morning-note` 결과 → 쇼츠 대본 / 커뮤니티 글 소재로 활용 가능
- 게시할 때는 꼭 "투자 권유 아님" 문구를 유지하세요.
