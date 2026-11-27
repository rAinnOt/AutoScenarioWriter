# AutoScenarioWriter Alpha — AI 에이전트 컨텍스트 가이드

이 프로젝트는 **MemoryAI(3계층 기억 공고화 장기기억 AI)** 연구용 실전 일일 시나리오(`YYYY_MM_DD.json`) 및 인간의 내적 발화(`inner_speech_*.md`)를 작성·편집하기 위한 독립 GitHub 배포용 알파 웹 에디터입니다.

## 핵심 파일
- `config.yaml`: Git에 커밋되는 공용 기본 설정 (`setup_completed: false`, 기본 출력 `./scenarios`)
- `local_config.yaml` / `.env` (`.gitignore` 대상): 연구자별 모델·API 키·저장 경로 설정 (웹 초기 설정 페이지에서 자동 생성)
- `writer_core.py`: 다중 LLM 제공자(Gemini, OpenAI, OpenRouter, Ollama, 커스텀 OpenAI 호환 API) 클라이언트, 연결 테스트, MemoryAI Scenario v1.0.0 JSON CRUD, `inner_speech_*.md` 파싱/렌더링 엔진
- `web_app.py`: 초기 설정 마법사 + 시나리오/내적발화 통합 에디터 웹 서버 (기본 실행 시 브라우저 자동 오픈, `--no-open`으로 비활성화 가능)
- `run_writer.bat` / `run_writer.sh`: Windows / macOS·Linux 원클릭 실행 스크립트

## 규격 및 보안 규칙
- 출력 JSON은 MemoryAI Scenario v1.0.0 규격을 준수한다.
- `.env`, `local_config.yaml`, `scenarios/`는 절대 Git에 커밋하지 않는다.
