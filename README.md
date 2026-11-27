# AutoScenarioWriter (Alpha)

> **장기기억 AI(MemoryAI) 연구를 위한 실전 일일 시나리오 · 인간 내적 발화(Inner Speech) 작성 및 편집기**  
> 현재 버전: `v0.1.0-alpha` (한국어 안내 버전)

---

## 1. 이 프로그램은 왜 만들어졌나요? (개발 목적)

현대의 대규모 언어 모델(LLM)은 방대한 사전 학습 지식을 가지고 있지만, 사람과 장기간 상호작용하며 경험을 축적하고 스스로의 사고방식과 관계적 태도를 교정하는 데에는 근본적인 한계가 있습니다.

- 새로운 경험을 바로 학습하면 기존 지식이 무너지는 **파국적 망각(Catastrophic Forgetting)** 문제가 발생합니다.
- 단순 검색(RAG)이나 사건 직후의 짧은 요약은 **시간 순서, 인과관계, 그리고 대화 이면의 미묘한 감정과 숨은 의도**를 쉽게 유실합니다.

**AutoScenarioWriter**는 인간 뇌의 **3계층 기억 공고화(Memory Consolidation)** 과정을 모방하는 장기기억 인공지능 연구 프로젝트(**MemoryAI**)에서, 연구자들이 일상과 연구 협업 속에서 일어나는 실제 대화와 **인간의 내적 발화(Inner Speech)**를 표준 규격(`MemoryAI Scenario v1.0.0`)으로 손쉽게 수집·구조화·수정할 수 있도록 만든 오픈소스 웹 에디터입니다.

---

## 2. 무엇을 학습시키기 위한 데이터인가요? (학습 목표)

이 에디터로 작성한 시나리오(`YYYY_MM_DD.json`)와 내적 발화(`inner_speech_*.md`)는 장기기억 AI의 **3계층 기억 공고화 파이프라인**에 투입되어, AI가 단순한 명령 수행기를 넘어 **메타인지와 관계적 지능**을 내재화하도록 학습·검증하는 데 사용됩니다.

### 3계층 기억 공고화 학습 구조
1. **1단계 — 24시간 1인칭 일기장 (해마 모방):** 시나리오의 대화 로그를 바탕으로 AI가 사건 맥락, 감정 가중치(`salience`, `valence`, `arousal`), 예측 오차가 담긴 1인칭 일기를 생성합니다.
2. **2단계 — 10일 주기 목차화 및 의도적 망각 (수면 리플레이 모방):** 중요도가 낮은 일상(`expected_salience: low`)은 **의도적 망각(Active Forgetting)** 대상으로 걸러내고, 핵심 사건 간의 인과 그래프와 목차를 압축합니다.
3. **3단계 — 장기기억 내재화 (대뇌 신피질 모방):** 예측 오차에서 도출한 교정 원칙을 **DPO(Direct Preference Optimization)** 데이터로 변환하고, **경험 재생(Experience Replay) 기반 QLoRA** 학습을 통해 AI의 직관과 행동 원칙으로 내재화합니다.

### 핵심 학습·검증 대상 (4대 인지 부하 + 내적 발화)
- **표면 의도와 숨은 의도의 충돌 (`hidden_intent_conflict`):** 겉으로 드러난 요청 뒤에 숨은 감정적 압박이나 진짜 의도를 파악하는 능력
- **시간차 전제 뒤집기 (`belief_revision_setup` / `belief_revision_flip`):** 과거에 확정했던 전제가 며칠 뒤 뒤집혔을 때 기존 신념을 안전하게 갱신하는 능력
- **지연된 피드백과 인과 추적 (`delayed_feedback_setup` / `delayed_feedback_result`):** 과거의 결정이 며칠 또는 다음 사이클 뒤에 가져온 결과를 연결해 원인을 성찰하는 능력
- **다중 가치 충돌 및 종합 회고 (`value_tradeoff`, `multi_memory_synthesis`):** 속도·품질·관계 등 상충하는 가치를 조율하고 여러 기억을 교차 통합하는 능력
- **의도적 망각 대조군 (`routine_low_salience`):** 학습 가치가 낮은 단순 잡담·조회를 과감히 버리는 선별 능력
- **인간의 내적 발화 (`inner_speech_*.md`):** 대화 로그에 직접 적히지 않은 인간의 정제되지 않은 속마음, 감정 톤, 숨은 맥락, 그리고 AI 반응에 대한 인간 연구자의 사후 평가(1~5점)를 함께 기록하여 **관계적 자연스러움과 맥락 포착 능력**을 정교하게 학습·평가합니다.

---

## 3. 주요 기능 (Alpha)

- **초기 모델 설정 페이지 (연구자별 자유 모델 선택):** 처음 실행 시 초기 설정 화면이 열리며, 각 연구자가 사용하는 모델(Google Gemini, OpenAI GPT, OpenRouter, 로컬 Ollama, vLLM/LM Studio 등 커스텀 OpenAI 호환 서버)과 저장 경로를 직접 지정하고 연결 테스트까지 바로 할 수 있습니다.
- **시나리오 · 내적 발화 통합 에디터:**
  - 새 에피소드 작성뿐만 아니라 **기존에 저장된 시나리오 파일과 `inner_speech_*.md`를 불러와 직접 수정·덮어쓰기·삭제**할 수 있습니다.
  - 내적 발화 영역은 **구조화 편집(폼)**과 **마크다운 원문 직접 편집** 모드를 모두 지원합니다.
- **AI 초안 자동 생성 (선택 기능):** 자유 형식의 메모나 대화 원문을 입력하면 설정한 AI 모델이 `MemoryAI Scenario v1.0.0` 구조와 내적 발화 초안을 자동으로 정리해 줍니다. (AI 없이 직접 수동 작성·편집도 가능합니다.)
- **실행 시 웹페이지 자동 오픈:** 프로그램을 실행하면 로컬 웹 서버가 켜지면서 기본 브라우저에 에디터(또는 초기 설정 페이지)가 자동으로 열립니다.
- **PC · 모바일 반응형 지원:** 같은 Wi-Fi 환경의 스마트폰 브라우저에서도 접속해 이동 중 메모와 내적 발화를 기록할 수 있습니다.

---

## 4. 설치 및 빠른 시작

### 사전 준비
- **Python 3.10 이상**

### 1) 저장소 클론 및 패키지 설치
```bash
git clone <이-저장소-URL>
cd AutoScenarioWriter
pip install -r requirements.txt
```

### 2) 프로그램 실행 (웹페이지 자동 실행)

- **Windows:** `run_writer.bat` 더블클릭 또는 터미널에서:
  ```powershell
  python web_app.py
  ```
- **macOS / Linux:**
  ```bash
  chmod +x run_writer.sh
  ./run_writer.sh
  # 또는
  python3 web_app.py
  ```

> 실행하면 브라우저가 자동으로 `http://127.0.0.1:8770` 주소로 열립니다.  
> 브라우저 자동 실행 없이 백그라운드 서버만 띄우려면 `python web_app.py --no-open` 옵션을 사용하세요.

---

## 5. 초기 설정 및 지원 모델 안내

처음 실행하면 **초기 설정 페이지**가 표시됩니다. 아래 항목을 입력하고 **설정 저장하고 에디터 시작하기**를 누르면, 다음 실행부터는 바로 에디터 화면이 열립니다. (에디터 상단의 `⚙️ 모델 · 초기 설정` 버튼으로 언제든 변경할 수 있습니다.)

| 제공자 | 설명 | API 키 필요 여부 |
| :--- | :--- | :---: |
| **Google Gemini** | `gemini-2.5-flash`, `gemini-2.5-pro` 등 | 필요 (`GEMINI_API_KEY`) |
| **OpenAI (GPT)** | `gpt-4o-mini`, `gpt-4o`, `gpt-4.1` 등 | 필요 (`OPENAI_API_KEY`) |
| **OpenRouter** | Claude, GPT, Gemini, Llama 등 다중 모델 | 필요 (`OPENROUTER_API_KEY`) |
| **로컬 Ollama** | `qwen2.5:7b`, `llama3.1:8b` 등 완전 로컬 실행 | 불필요 |
| **커스텀 OpenAI 호환 API** | vLLM, LM Studio, DeepSeek, 연구실 자체 서버 등 | 서버 설정에 따름 |

- 개인 설정은 `local_config.yaml`, API 키는 `.env` 파일에 로컬로만 저장되며 `.gitignore`에 의해 Git 커밋에서 자동으로 제외됩니다.

---

## 6. 생성되는 데이터 구조

저장된 파일은 기본적으로 `./scenarios/` 폴더(설정에서 `../MemoryAI/datasets/scenarios` 등으로 변경 가능)에 생성됩니다.

### 1) 일일 시나리오 파일 (`YYYY_MM_DD.json`)
`MemoryAI Scenario v1.0.0` 표준 JSON 규격을 따릅니다.
- `schema_version`, `dataset_id`, `title`, `language`, `cycle_days`, `persona`, `metadata`
- `episodes[]`: `day`, `date`, `scenario_id`, `scenario_type`, `expected_salience`, `linked_days`, `title`, `cognitive_trap`, `expected_principle`, `relational_goal`, `chat_log`, `inner_speech_file`

### 2) 인간 내적 발화 파일 (`inner_speech_YYYY_MM_DD_NN.md`)
```markdown
---
scenario_id: 2026_11_27_01
author: human_researcher
emotional_tone: [고민, 기대]
ai_comprehension_score: 4
---

# 인간의 내적 발화 (Inner Speech)
(대화를 시작하기 전후 머릿속에 떠올랐던 정제되지 않은 생각과 망설임)

## 숨은 맥락 및 의도 (Hidden Context)
(직접 말하지 않았지만 AI가 눈치채길 바랐던 핵심 맥락)

## AI 반응에 대한 인간 연구자의 사후 평가 (Human Evaluation)
- **관계적 자연스러움:** ...
- **맥락 포착 여부:** ...
- **수정/보완 메모:** ...
```

---

## 7. 프로젝트 구조

```text
AutoScenarioWriter/
├── README.md               # 프로젝트 목적, 학습 목표 및 한국어 사용 가이드
├── LICENSE                 # MIT 라이선스
├── .gitignore              # API 키(.env), 개인 설정(local_config.yaml), 데이터 보호
├── .env.example            # API 키 환경변수 예시 파일
├── config.yaml             # 공용 기본 설정 (초기 상태: setup_completed: false)
├── requirements.txt        # 의존 패키지 (openai, pyyaml)
├── writer_core.py          # 다중 LLM 클라이언트, 시나리오 JSON & 내적발화 MD 처리 엔진
├── web_app.py              # 초기 설정 마법사 및 시나리오·내적발화 웹 에디터 서버
├── run_writer.bat          # Windows 원클릭 실행 (웹페이지 자동 오픈)
├── run_writer.sh           # macOS / Linux 원클릭 실행 (웹페이지 자동 오픈)
└── register_startup.bat    # Windows 부팅 시 백그라운드 자동 실행 등록
```

---

## 8. 알파 버전 안내

- 본 배포판은 **Alpha (`v0.1.0-alpha`)** 단계로, 현재 한국어 인터페이스 및 한국어 안내 문서 중심으로 제공됩니다.
- 연구 현장의 피드백을 바탕으로 다국어 지원, JSON 스키마 자동 검증 UI, 일괄 내보내기 등의 기능이 순차적으로 추가될 예정입니다.
