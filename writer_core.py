"""Core engine for AutoScenarioWriter Alpha.

Manages multi-provider LLM configuration, MemoryAI v1.0.0 scenario JSON CRUD,
and human Inner Speech Markdown reading/writing/editing.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

APP_VERSION = "0.1.0-alpha"

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
LOCAL_CONFIG_PATH = BASE_DIR / "local_config.yaml"
ENV_PATH = BASE_DIR / ".env"

GEMINI_COMPAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

VALID_SCENARIO_TYPES = (
    "hidden_intent_conflict",
    "belief_revision_setup",
    "belief_revision_flip",
    "delayed_feedback_setup",
    "delayed_feedback_result",
    "value_tradeoff",
    "routine_low_salience",
    "multi_memory_synthesis",
)

PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "gemini": {
        "label": "Google Gemini",
        "base_url": GEMINI_COMPAT_URL,
        "api_key_env": "GEMINI_API_KEY",
        "requires_key": True,
        "default_model": "gemini-2.5-flash",
        "suggested_models": [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3-flash-preview",
        ],
        "help": "Google AI Studio에서 발급한 GEMINI_API_KEY를 사용합니다.",
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "requires_key": True,
        "default_model": "gpt-4o-mini",
        "suggested_models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
        ],
        "help": "OpenAI Platform에서 발급한 OPENAI_API_KEY를 사용합니다.",
    },
    "openrouter": {
        "label": "OpenRouter (Claude · Llama 등 다중 모델)",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "requires_key": True,
        "default_model": "anthropic/claude-3.5-sonnet",
        "suggested_models": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini",
            "google/gemini-2.5-flash",
            "meta-llama/llama-3.3-70b-instruct",
        ],
        "help": "OpenRouter API 키 하나로 Claude, GPT, Gemini, 오픈소스 모델을 자유롭게 선택할 수 있습니다.",
    },
    "ollama": {
        "label": "로컬 Ollama (API 키 불필요)",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "",
        "requires_key": False,
        "default_model": "qwen2.5:7b",
        "suggested_models": [
            "qwen2.5:7b",
            "llama3.1:8b",
            "gemma3:12b",
            "deepseek-r1:8b",
        ],
        "help": "로컬 PC에서 실행 중인 Ollama 서버에 연결합니다. 외부로 데이터가 전송되지 않습니다.",
    },
    "custom": {
        "label": "커스텀 OpenAI 호환 API (vLLM · LM Studio · DeepSeek 등)",
        "base_url": "",
        "api_key_env": "CUSTOM_API_KEY",
        "requires_key": False,
        "default_model": "",
        "suggested_models": [],
        "help": "OpenAI 호환 /v1 엔드포인트를 제공하는 모든 자체 서버나 외부 API를 연결할 수 있습니다.",
    },
}

SCENARIO_WRITER_PROMPT = """당신은 MemoryAI(3계층 기억 공고화 장기기억 AI) 연구용 일일 시나리오를 표준 JSON으로 정제하는 전문 어시스턴트입니다.
사용자가 입력한 오늘의 메모, 사건, 또는 대화 초안을 바탕으로 MemoryAI v1.0.0 에피소드 JSON 1개를 **반드시 한국어 JSON**으로 생성하세요.

[분류 기준]
- scenario_type은 반드시 다음 8개 중 가장 적합한 1개를 선택:
  hidden_intent_conflict, belief_revision_setup, belief_revision_flip,
  delayed_feedback_setup, delayed_feedback_result, value_tradeoff,
  routine_low_salience, multi_memory_synthesis
- expected_salience:
  - 단순 일상·날씨·점심·단답 조회 -> "low"
  - 일반적인 기록 -> "medium"
  - 감정 충돌·판단 착오·전제 변화·가치 충돌·깊은 성찰 -> "high"
- chat_log: 실제 사용자와 AI가 나눈 자연스러운 3~6턴 대화 형식("사용자: ...\\nAI: ...")으로 정리. 이미 대화 로그가 주어졌다면 원문의 핵심 맥락을 보존.
{inner_instruction}

[출력 JSON 스키마 (JSON만 출력)]
{{
  "title": "오늘 사건의 핵심 요약 제목 (10~35자)",
  "scenario_type": "위 8개 중 하나",
  "expected_salience": "high | medium | low",
  "cognitive_trap": "AI가 빠지기 쉬운 인지 편향 또는 관찰 포인트 (단순 일상이면 '없음')",
  "expected_principle": "장기기억 공고화 후 AI가 내재화하면 좋을 If-Then 행동 원칙 (선택, 없으면 빈 문자열)",
  "relational_goal": "AI가 파악하고 공감해야 할 관계적 맥락 (선택, 없으면 빈 문자열)",
  "chat_log": "사용자: ...\\nAI: ...\\n사용자: ...\\nAI: ..."{inner_schema}
}}

[날짜]: {date_iso}
[사용자 입력 원문]:
{raw_input}
"""


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = copy.deepcopy(v)
    return merged


def _load_dotenv_chain() -> None:
    """Load AutoScenarioWriter/.env first, then fallback to ../MemoryAI/.env."""
    for env_path in (ENV_PATH, BASE_DIR.parent / "MemoryAI" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v:
                os.environ.setdefault(k, v)


def _write_env_key(key_name: str, key_value: str) -> None:
    """Create or update a key inside AutoScenarioWriter/.env (gitignored)."""
    if not key_name:
        return
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    updated = False
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            if k.strip() == key_name:
                new_lines.append(f"{key_name}={key_value}")
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        if not new_lines:
            new_lines.append("# AutoScenarioWriter 로컬 API 키 설정 (Git에 커밋되지 않습니다)")
        new_lines.append(f"{key_name}={key_value}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[key_name] = key_value


def _mask_key(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def load_config() -> dict[str, Any]:
    base: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            base = yaml.safe_load(f) or {}
    if LOCAL_CONFIG_PATH.exists():
        with LOCAL_CONFIG_PATH.open("r", encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        return _deep_merge(base, local)
    return base


def is_setup_completed(cfg: dict[str, Any] | None = None) -> bool:
    c = cfg or load_config()
    return bool(c.get("setup_completed", False))


def get_output_dir(cfg: dict[str, Any] | None = None) -> Path:
    c = cfg or load_config()
    raw_dir = c.get("paths", {}).get("output_scenarios_dir", "./scenarios")
    p = Path(raw_dir).expanduser()
    out = p.resolve() if p.is_absolute() else (BASE_DIR / p).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def get_public_settings() -> dict[str, Any]:
    """Return current settings safely for the web UI (API key is masked)."""
    _load_dotenv_chain()
    cfg = load_config()
    llm = cfg.get("llm", {})
    provider = str(llm.get("provider", "gemini")).lower()
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
    env_name = str(llm.get("api_key_env") or preset.get("api_key_env") or "")
    raw_key = os.getenv(env_name, "") if env_name else ""

    return {
        "app_version": APP_VERSION,
        "setup_completed": is_setup_completed(cfg),
        "llm": {
            "provider": provider,
            "model": str(llm.get("model") or preset.get("default_model") or ""),
            "base_url": str(llm.get("base_url") or preset.get("base_url") or ""),
            "api_key_env": env_name,
            "timeout": float(llm.get("timeout", 60.0)),
            "has_api_key": bool(raw_key),
            "api_key_masked": _mask_key(raw_key),
        },
        "paths": {
            "output_scenarios_dir": str(
                cfg.get("paths", {}).get("output_scenarios_dir", "./scenarios")
            ),
            "resolved_output_dir": str(get_output_dir(cfg)),
        },
        "defaults": {
            "language": str(cfg.get("defaults", {}).get("language", "ko")),
            "cycle_days": int(cfg.get("defaults", {}).get("cycle_days", 10)),
            "author": str(cfg.get("defaults", {}).get("author", "human_researcher")),
            "user_role": str(
                cfg.get("defaults", {}).get("user_role", "인간 연구자 (사용자)")
            ),
            "agent_role": str(
                cfg.get("defaults", {}).get("agent_role", "장기기억 AI 어시스턴트")
            ),
            "domain": str(
                cfg.get("defaults", {}).get("domain", "일상 및 연구·개발 협업")
            ),
        },
        "presets": PROVIDER_PRESETS,
    }


def save_user_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist researcher's personal settings to local_config.yaml and .env."""
    llm_in = payload.get("llm") or {}
    paths_in = payload.get("paths") or {}
    defaults_in = payload.get("defaults") or {}

    provider = str(llm_in.get("provider") or "gemini").strip().lower()
    if provider not in PROVIDER_PRESETS:
        provider = "custom"
    preset = PROVIDER_PRESETS[provider]

    model = str(llm_in.get("model") or "").strip()
    if not model:
        raise ValueError("사용할 모델명을 입력해 주세요.")

    base_url = str(llm_in.get("base_url") or preset.get("base_url") or "").strip()
    if provider in ("ollama", "custom", "openrouter", "gemini") and not base_url:
        raise ValueError("선택한 제공자에는 Base URL이 필요합니다.")

    env_name = str(llm_in.get("api_key_env") or preset.get("api_key_env") or "").strip()
    api_key_input = str(llm_in.get("api_key") or "").strip()

    if api_key_input and env_name:
        _write_env_key(env_name, api_key_input)

    out_dir_str = str(paths_in.get("output_scenarios_dir") or "./scenarios").strip() or "./scenarios"
    timeout = float(llm_in.get("timeout") or 60.0)
    cycle_days = max(1, int(defaults_in.get("cycle_days") or 10))

    local_cfg: dict[str, Any] = {
        "setup_completed": True,
        "paths": {
            "output_scenarios_dir": out_dir_str,
        },
        "llm": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key_env": env_name,
            "timeout": timeout,
        },
        "defaults": {
            "language": str(defaults_in.get("language") or "ko").strip() or "ko",
            "cycle_days": cycle_days,
            "author": str(defaults_in.get("author") or "human_researcher").strip()
            or "human_researcher",
            "user_role": str(defaults_in.get("user_role") or "인간 연구자 (사용자)").strip()
            or "인간 연구자 (사용자)",
            "agent_role": str(
                defaults_in.get("agent_role") or "장기기억 AI 어시스턴트"
            ).strip()
            or "장기기억 AI 어시스턴트",
            "domain": str(defaults_in.get("domain") or "일상 및 연구·개발 협업").strip()
            or "일상 및 연구·개발 협업",
        },
    }

    with LOCAL_CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(local_cfg, f, allow_unicode=True, sort_keys=False)

    # Ensure output directory exists right away
    get_output_dir(load_config())
    return get_public_settings()


def create_client(
    cfg: dict[str, Any] | None = None,
    override: dict[str, Any] | None = None,
) -> tuple[OpenAI, str]:
    _load_dotenv_chain()
    c = cfg or load_config()
    llm = dict(c.get("llm", {}))
    if override:
        for k, v in override.items():
            if v is not None and v != "":
                llm[k] = v

    provider = str(os.getenv("AUTOSCENARIO_PROVIDER", llm.get("provider", "gemini"))).lower()
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
    model = str(llm.get("model") or preset.get("default_model") or "").strip()
    if not model:
        raise ValueError("모델명이 설정되지 않았습니다. 초기 설정 페이지에서 모델을 입력해 주세요.")

    timeout = float(llm.get("timeout", 60.0))
    base_url = str(llm.get("base_url") or preset.get("base_url") or "").strip()
    env_name = str(llm.get("api_key_env") or preset.get("api_key_env") or "").strip()

    explicit_key = str(override.get("api_key") or "").strip() if override else ""
    api_key = explicit_key or (os.getenv(env_name, "") if env_name else "")

    if provider == "ollama":
        return (
            OpenAI(
                base_url=base_url or "http://localhost:11434/v1",
                api_key=api_key or "ollama",
                timeout=timeout,
            ),
            model,
        )

    if provider == "custom":
        if not base_url:
            raise ValueError("커스텀 API의 Base URL이 설정되지 않았습니다.")
        return (
            OpenAI(
                base_url=base_url,
                api_key=api_key or "custom-no-key",
                timeout=timeout,
            ),
            model,
        )

    if not api_key:
        raise EnvironmentError(
            f"API 키({env_name})가 설정되지 않았습니다. 설정 페이지에서 API 키를 입력하거나 .env 파일을 확인해 주세요."
        )

    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url and provider != "openai":
        kwargs["base_url"] = base_url
    elif base_url and base_url != "https://api.openai.com/v1":
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs), model


def test_llm_connection(override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a minimal ping request to verify model/endpoint/API key."""
    client, model = create_client(override=override)
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "연결 테스트입니다. 'OK'라고만 짧게 답해 주세요."}],
        max_tokens=16,
        temperature=0.0,
    )
    reply = (res.choices[0].message.content or "").strip()
    return {"ok": True, "model": model, "reply": reply or "OK"}


def _safe_json_loads(raw_text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.DOTALL)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    return parsed if isinstance(parsed, dict) else {}


def draft_episode_with_ai(
    raw_input: str,
    date_iso: str | None = None,
    include_inner_speech: bool = False,
) -> dict[str, Any]:
    """Use configured LLM to structure raw user notes/dialogue into a MemoryAI episode."""
    cfg = load_config()
    client, model = create_client(cfg)
    today_iso = date_iso or dt.date.today().isoformat()

    if include_inner_speech:
        inner_instruction = (
            "- 내적 발화 초안도 함께 생성: emotional_tone(쉼표 구분 감정 태그), "
            "inner_speech(대화 전후 인간이 느꼈을 정제되지 않은 속마음·망설임), "
            "hidden_context(직접 말하지 않았지만 AI가 눈치채길 바랐던 숨은 맥락)."
        )
        inner_schema = (
            ',\n  "emotional_tone": "감정1, 감정2",'
            '\n  "inner_speech": "정제되지 않은 인간의 내적 발화 초안",'
            '\n  "hidden_context": "숨은 맥락 및 의도 초안"'
        )
    else:
        inner_instruction = ""
        inner_schema = ""

    messages = [
        {
            "role": "system",
            "content": "반드시 한국어 JSON 객체만 출력하세요. 불필요한 설명이나 코드 블록 외 텍스트를 넣지 마세요.",
        },
        {
            "role": "user",
            "content": SCENARIO_WRITER_PROMPT.format(
                date_iso=today_iso,
                raw_input=raw_input,
                inner_instruction=inner_instruction,
                inner_schema=inner_schema,
            ),
        },
    ]

    try:
        res = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )
    except Exception:
        # Fallback for OpenAI-compatible servers/models that do not support response_format
        res = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )

    data = _safe_json_loads(res.choices[0].message.content or "{}")
    stype = data.get("scenario_type", "routine_low_salience")
    if stype not in VALID_SCENARIO_TYPES:
        stype = "routine_low_salience"
    sal = data.get("expected_salience", "medium")
    if sal not in ("high", "medium", "low"):
        sal = "medium"

    result: dict[str, Any] = {
        "date": today_iso,
        "title": str(data.get("title") or f"{today_iso} 일상 기록").strip(),
        "scenario_type": stype,
        "expected_salience": sal,
        "cognitive_trap": str(data.get("cognitive_trap") or "없음").strip(),
        "expected_principle": str(data.get("expected_principle") or "").strip(),
        "relational_goal": str(data.get("relational_goal") or "").strip(),
        "chat_log": str(data.get("chat_log") or raw_input).strip(),
    }
    if include_inner_speech:
        tone = data.get("emotional_tone", "")
        if isinstance(tone, list):
            tone = ", ".join(str(x).strip() for x in tone if str(x).strip())
        result["inner_speech_data"] = {
            "emotional_tone": str(tone).strip(),
            "inner_speech": str(data.get("inner_speech") or "").strip(),
            "hidden_context": str(data.get("hidden_context") or "").strip(),
        }
    return result


# ---------------------------------------------------------------------------
# Inner Speech Markdown Parsing & Rendering
# ---------------------------------------------------------------------------

def parse_inner_speech_md(md_text: str) -> dict[str, Any]:
    """Parse inner_speech_*.md (frontmatter + 3 sections) into structured fields."""
    result: dict[str, Any] = {
        "author": "human_researcher",
        "emotional_tone": "",
        "ai_comprehension_score": "",
        "inner_speech": "",
        "hidden_context": "",
        "eval_naturalness": "",
        "eval_context": "",
        "eval_notes": "",
        "raw_markdown": md_text,
    }
    if not md_text.strip():
        return result

    body = md_text
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", md_text, flags=re.DOTALL)
    if fm_match:
        fm_raw, body = fm_match.group(1), fm_match.group(2)
        try:
            fm = yaml.safe_load(fm_raw) or {}
            if isinstance(fm, dict):
                if fm.get("author"):
                    result["author"] = str(fm["author"]).strip()
                tones = fm.get("emotional_tone")
                if isinstance(tones, list):
                    result["emotional_tone"] = ", ".join(str(t).strip() for t in tones if str(t).strip())
                elif tones:
                    result["emotional_tone"] = str(tones).strip()
                score = fm.get("ai_comprehension_score")
                if score is not None and str(score).strip().lower() not in ("", "null", "none"):
                    result["ai_comprehension_score"] = str(score).strip()
        except Exception:
            pass

    def _extract_section(pattern: str, next_patterns: list[str]) -> str:
        m = re.search(pattern, body, flags=re.MULTILINE)
        if not m:
            return ""
        start = m.end()
        end = len(body)
        for np in next_patterns:
            nm = re.search(np, body[start:], flags=re.MULTILINE)
            if nm:
                end = min(end, start + nm.start())
        return body[start:end].strip()

    inner_sec = _extract_section(
        r"^#\s+인간의 내적 발화[^\n]*\n?",
        [r"^##\s+숨은 맥락", r"^##\s+AI 반응에 대한"],
    )
    hidden_sec = _extract_section(
        r"^##\s+숨은 맥락[^\n]*\n?",
        [r"^##\s+AI 반응에 대한"],
    )
    eval_sec = _extract_section(
        r"^##\s+AI 반응에 대한[^\n]*\n?",
        [],
    )

    result["inner_speech"] = inner_sec
    result["hidden_context"] = hidden_sec

    if eval_sec:
        for line in eval_sec.splitlines():
            s = line.strip()
            if "관계적 자연스러움" in s:
                result["eval_naturalness"] = re.sub(r"^-\s*\*\*관계적 자연스러움:\*\*\s*", "", s).strip()
            elif "맥락 포착 여부" in s:
                result["eval_context"] = re.sub(r"^-\s*\*\*맥락 포착 여부:\*\*\s*", "", s).strip()
            elif "수정/보완 메모" in s:
                result["eval_notes"] = re.sub(r"^-\s*\*\*수정/보완 메모:\*\*\s*", "", s).strip()

    return result


def render_inner_speech_md(
    scenario_id: str,
    inner_data: dict[str, Any],
    default_author: str = "human_researcher",
) -> str:
    """Render structured inner speech fields into MemoryAI inner_speech_*.md format."""
    if inner_data.get("use_raw_markdown") and str(inner_data.get("raw_markdown") or "").strip():
        return str(inner_data["raw_markdown"]).rstrip() + "\n"

    author = str(inner_data.get("author") or default_author).strip() or default_author
    tone_raw = str(inner_data.get("emotional_tone") or "")
    tones = [t.strip() for t in tone_raw.split(",") if t.strip()]
    tones_yaml = "[" + ", ".join(tones) + "]"

    score_raw = str(inner_data.get("ai_comprehension_score") or "").strip()
    score_yaml = score_raw if score_raw in ("1", "2", "3", "4", "5") else "null"

    inner_text = str(inner_data.get("inner_speech") or "").strip()
    hidden_text = str(inner_data.get("hidden_context") or "").strip()
    eval_nat = str(inner_data.get("eval_naturalness") or "").strip()
    eval_ctx = str(inner_data.get("eval_context") or "").strip()
    eval_notes = str(inner_data.get("eval_notes") or "").strip()

    return (
        f"---\n"
        f"scenario_id: {scenario_id}\n"
        f"author: {author}\n"
        f"emotional_tone: {tones_yaml}\n"
        f"ai_comprehension_score: {score_yaml}\n"
        f"---\n\n"
        f"# 인간의 내적 발화 (Inner Speech)\n"
        f"{inner_text}\n\n"
        f"## 숨은 맥락 및 의도 (Hidden Context)\n"
        f"{hidden_text}\n\n"
        f"## AI 반응에 대한 인간 연구자의 사후 평가 (Human Evaluation)\n"
        f"- **관계적 자연스러움:** {eval_nat}\n"
        f"- **맥락 포착 여부:** {eval_ctx}\n"
        f"- **수정/보완 메모:** {eval_notes}\n"
    )


def _has_inner_speech_content(inner_data: dict[str, Any] | None) -> bool:
    if not inner_data:
        return False
    if inner_data.get("use_raw_markdown") and str(inner_data.get("raw_markdown") or "").strip():
        return True
    keys = (
        "emotional_tone",
        "ai_comprehension_score",
        "inner_speech",
        "hidden_context",
        "eval_naturalness",
        "eval_context",
        "eval_notes",
    )
    return any(str(inner_data.get(k) or "").strip() for k in keys)


# ---------------------------------------------------------------------------
# Scenario JSON CRUD
# ---------------------------------------------------------------------------

def _safe_resolve_file(out_dir: Path, filename: str) -> Path:
    clean_name = Path(filename).name
    if not clean_name or clean_name != filename or not clean_name.endswith(".json"):
        raise ValueError("올바르지 않은 시나리오 파일명입니다.")
    target = (out_dir / clean_name).resolve()
    if target.parent != out_dir.resolve():
        raise ValueError("허용된 시나리오 폴더 외부 파일에는 접근할 수 없습니다.")
    return target


def _parse_linked_days(raw: Any, current_day: int) -> list[int]:
    if isinstance(raw, list):
        nums = []
        for x in raw:
            try:
                n = int(x)
                if 1 <= n < current_day and n not in nums:
                    nums.append(n)
            except (TypeError, ValueError):
                continue
        return sorted(nums)
    if isinstance(raw, str) and raw.strip():
        nums = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                n = int(part)
                if 1 <= n < current_day and n not in nums:
                    nums.append(n)
            except ValueError:
                continue
        return sorted(nums)
    return []


def list_daily_scenarios() -> list[dict[str, Any]]:
    """List all scenario JSON files inside the configured output directory."""
    out_dir = get_output_dir()
    items: list[dict[str, Any]] = []
    for p in sorted(out_dir.glob("*.json"), key=lambda x: x.name, reverse=True):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(doc, list):
                eps = doc
                title = p.stem
            elif isinstance(doc, dict) and isinstance(doc.get("episodes"), list):
                eps = doc["episodes"]
                title = str(doc.get("title") or p.stem)
            else:
                continue
            inner_count = sum(
                1
                for ep in eps
                if isinstance(ep, dict)
                and (ep.get("inner_speech_file") or ep.get("inner_speech_inline"))
            )
            items.append(
                {
                    "file": p.name,
                    "title": title,
                    "count": len(eps),
                    "inner_count": inner_count,
                }
            )
        except Exception:
            continue
    return items


def load_scenario_file(filename: str) -> dict[str, Any]:
    """Load a scenario JSON file along with each episode's linked inner_speech_*.md."""
    out_dir = get_output_dir()
    path = _safe_resolve_file(out_dir, filename)
    if not path.exists():
        raise FileNotFoundError(f"시나리오 파일을 찾을 수 없습니다: {filename}")

    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        episodes = doc
        title = path.stem
        dataset_id = path.stem
    elif isinstance(doc, dict):
        episodes = doc.get("episodes", [])
        title = str(doc.get("title") or path.stem)
        dataset_id = str(doc.get("dataset_id") or path.stem)
    else:
        raise ValueError("지원하지 않는 JSON 구조입니다.")

    enriched_episodes: list[dict[str, Any]] = []
    for idx, ep in enumerate(episodes):
        if not isinstance(ep, dict):
            continue
        item = copy.deepcopy(ep)
        item["_index"] = idx
        inner_file = str(ep.get("inner_speech_file") or "").strip()
        inner_data = parse_inner_speech_md("")
        if inner_file:
            inner_path = (out_dir / Path(inner_file).name).resolve()
            if inner_path.parent == out_dir.resolve() and inner_path.exists():
                inner_data = parse_inner_speech_md(inner_path.read_text(encoding="utf-8"))
        item["_inner_speech_data"] = inner_data
        enriched_episodes.append(item)

    return {
        "file": path.name,
        "dataset_id": dataset_id,
        "title": title,
        "episodes": enriched_episodes,
    }


def save_daily_scenario(
    episode_data: dict[str, Any],
    date_iso: str | None = None,
    inner_speech_data: dict[str, Any] | None = None,
    target_filename: str | None = None,
    episode_index: int | None = None,
    # Legacy flat parameters for backwards compatibility
    inner_speech_text: str = "",
    hidden_context_text: str = "",
    emotional_tone: str = "",
) -> dict[str, Any]:
    """Create or update an episode in a MemoryAI v1.0.0 scenario JSON + inner speech MD."""
    cfg = load_config()
    defaults = cfg.get("defaults", {})
    default_author = str(defaults.get("author", "human_researcher"))
    out_dir = get_output_dir(cfg)

    iso = (date_iso or episode_data.get("date") or dt.date.today().isoformat()).strip()
    date_slug = iso.replace("-", "_")

    if target_filename:
        json_path = _safe_resolve_file(out_dir, target_filename)
    else:
        json_path = out_dir / f"{date_slug}.json"

    if json_path.exists():
        doc = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(doc, list):
            episodes = doc
            doc = {
                "schema_version": "1.0.0",
                "dataset_id": re.sub(r"[^a-z0-9_-]", "_", json_path.stem.lower()),
                "title": f"{iso} 실전 일일 시나리오",
                "description": "AutoScenarioWriter로 생성·편집된 실전 시나리오",
                "language": defaults.get("language", "ko"),
                "cycle_days": int(defaults.get("cycle_days", 10)),
                "episodes": episodes,
            }
        else:
            episodes = doc.get("episodes", [])
    else:
        episodes = []
        doc = {
            "schema_version": "1.0.0",
            "dataset_id": f"daily_{date_slug}",
            "title": f"{iso} 실전 일일 시나리오",
            "description": "AutoScenarioWriter로 생성·편집된 실제 일일 대화·경험 시나리오",
            "language": defaults.get("language", "ko"),
            "cycle_days": int(defaults.get("cycle_days", 10)),
            "persona": {
                "user_role": defaults.get("user_role", "인간 연구자 (사용자)"),
                "agent_role": defaults.get("agent_role", "장기기억 AI 어시스턴트"),
                "domain": defaults.get("domain", "일상 및 연구·개발 협업"),
            },
            "metadata": {
                "author": default_author,
                "created_at": iso,
                "tags": ["real-daily", date_slug],
            },
            "episodes": episodes,
        }

    is_update = (
        episode_index is not None
        and isinstance(episode_index, int)
        and 0 <= episode_index < len(episodes)
    )

    if is_update:
        existing_ep = episodes[episode_index]
        day_num = int(existing_ep.get("day", episode_index + 1))
        scenario_id = str(existing_ep.get("scenario_id") or f"{date_slug}_{day_num:02d}")
        existing_inner_file = str(existing_ep.get("inner_speech_file") or "").strip()
    else:
        day_num = len(episodes) + 1
        scenario_id = f"{date_slug}_{day_num:02d}"
        existing_inner_file = ""

    stype = str(episode_data.get("scenario_type") or "routine_low_salience")
    if stype not in VALID_SCENARIO_TYPES:
        stype = "routine_low_salience"
    sal = str(episode_data.get("expected_salience") or "medium")
    if sal not in ("high", "medium", "low"):
        sal = "medium"

    ep: dict[str, Any] = {
        "day": day_num,
        "date": iso,
        "scenario_id": scenario_id,
        "scenario_type": stype,
        "expected_salience": sal,
        "linked_days": _parse_linked_days(episode_data.get("linked_days"), day_num),
        "title": str(episode_data.get("title") or f"{iso} 기록").strip(),
        "cognitive_trap": str(episode_data.get("cognitive_trap") or "없음").strip(),
        "chat_log": str(episode_data.get("chat_log") or "").strip(),
    }
    if str(episode_data.get("expected_principle") or "").strip():
        ep["expected_principle"] = str(episode_data["expected_principle"]).strip()
    if str(episode_data.get("relational_goal") or "").strip():
        ep["relational_goal"] = str(episode_data["relational_goal"]).strip()
    if str(episode_data.get("inner_speech_inline") or "").strip():
        ep["inner_speech_inline"] = str(episode_data["inner_speech_inline"]).strip()

    # Merge legacy flat params if inner_speech_data not supplied
    if inner_speech_data is None and (
        inner_speech_text.strip() or hidden_context_text.strip() or emotional_tone.strip()
    ):
        inner_speech_data = {
            "author": default_author,
            "emotional_tone": emotional_tone,
            "inner_speech": inner_speech_text,
            "hidden_context": hidden_context_text,
        }

    saved_inner = ""
    if _has_inner_speech_content(inner_speech_data):
        inner_name = existing_inner_file or f"inner_speech_{scenario_id}.md"
        inner_name = Path(inner_name).name
        md = render_inner_speech_md(
            scenario_id=scenario_id,
            inner_data=inner_speech_data or {},
            default_author=default_author,
        )
        inner_path = (out_dir / inner_name).resolve()
        inner_path.write_text(md, encoding="utf-8")
        ep["inner_speech_file"] = inner_name
        saved_inner = str(inner_path)
    elif existing_inner_file:
        # Researcher cleared inner speech completely: remove link
        ep.pop("inner_speech_file", None)

    if is_update:
        episodes[episode_index] = ep
        saved_index = episode_index
    else:
        episodes.append(ep)
        saved_index = len(episodes) - 1

    doc["episodes"] = episodes
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "mode": "updated" if is_update else "created",
        "json_file": json_path.name,
        "json_path": str(json_path),
        "inner_speech_file": ep.get("inner_speech_file", ""),
        "inner_speech_path": saved_inner,
        "episode_index": saved_index,
        "episode_count": len(episodes),
    }


def delete_episode(filename: str, episode_index: int) -> dict[str, Any]:
    """Delete an episode from a scenario JSON file and re-index days 1..N."""
    out_dir = get_output_dir()
    path = _safe_resolve_file(out_dir, filename)
    if not path.exists():
        raise FileNotFoundError(f"시나리오 파일을 찾을 수 없습니다: {filename}")

    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("episodes"), list):
        raise ValueError("지원하지 않는 시나리오 파일 형식입니다.")

    episodes = doc["episodes"]
    if not (0 <= episode_index < len(episodes)):
        raise IndexError("삭제할 에피소드 인덱스가 유효하지 않습니다.")

    removed = episodes.pop(episode_index)
    if not episodes:
        path.unlink()
        return {"file": filename, "deleted_file": True, "remaining": 0, "removed_title": removed.get("title", "")}

    for i, ep in enumerate(episodes):
        ep["day"] = i + 1
        ep["linked_days"] = _parse_linked_days(ep.get("linked_days"), i + 1)

    doc["episodes"] = episodes
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "file": filename,
        "deleted_file": False,
        "remaining": len(episodes),
        "removed_title": removed.get("title", ""),
    }
