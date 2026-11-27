"""AutoScenarioWriter Alpha — Local & Mobile Web Server with Setup Wizard & Inner Speech Editor."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from writer_core import (
    APP_VERSION,
    delete_episode,
    draft_episode_with_ai,
    get_output_dir,
    get_public_settings,
    is_setup_completed,
    list_daily_scenarios,
    load_config,
    load_scenario_file,
    save_daily_scenario,
    save_user_settings,
    test_llm_connection,
)


def _detect_lan_ip() -> str:
    """Detect local LAN IP so the user can open this web app on their smartphone."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


HTML_UI = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>AutoScenarioWriter Alpha — 장기기억 AI 시나리오 · 내적발화 에디터</title>
<style>
  :root {
    --bg: #0b1120;
    --bg2: #0f172a;
    --card: #162033;
    --border: #2b3a55;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --primary: #4f46e5;
    --ok: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --inner-bg: #171d36;
    --inner-border: #4338ca;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  .topbar {
    position: sticky;
    top: 0;
    z-index: 20;
    background: rgba(11, 17, 32, 0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
    padding: 12px 18px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .brand { display: flex; align-items: center; gap: 10px; }
  .brand h1 { margin: 0; font-size: 18px; letter-spacing: -0.02em; }
  .badge {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    background: #1e3a8a;
    color: #93c5fd;
    border: 1px solid #3b82f6;
  }
  .pill {
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--bg2);
    border: 1px solid var(--border);
    color: var(--muted);
  }
  .nav-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .nav-btn {
    padding: 7px 13px;
    border-radius: 9px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .nav-btn.active {
    background: linear-gradient(135deg, #0284c7, #4f46e5);
    border-color: transparent;
    color: #fff;
  }

  .container { max-width: 1240px; margin: 0 auto; padding: 16px; }
  .setup-container { max-width: 780px; margin: 0 auto; padding: 16px; }
  .hidden { display: none !important; }

  .status {
    padding: 11px 14px;
    border-radius: 10px;
    font-size: 13px;
    margin-bottom: 14px;
    display: none;
    white-space: pre-wrap;
  }
  .status.ok { display: block; background: #064e3b; border: 1px solid #10b981; color: #d1fae5; }
  .status.err { display: block; background: #450a0a; border: 1px solid #ef4444; color: #fee2e2; }
  .status.info { display: block; background: #1e293b; border: 1px solid #38bdf8; color: #e0f2fe; }

  .layout {
    display: grid;
    grid-template-columns: 310px 1fr;
    gap: 16px;
    align-items: start;
  }
  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
  }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 14px;
  }
  .card.inner-card {
    background: var(--inner-bg);
    border: 1px solid var(--inner-border);
  }
  .card-title {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .subtext { font-size: 12.5px; color: var(--muted); margin: 0; }

  label {
    font-size: 12.5px;
    color: var(--muted);
    font-weight: 600;
    display: block;
    margin-bottom: 4px;
  }
  input, select, textarea {
    width: 100%;
    background: var(--bg2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 9px 11px;
    font-size: 13.5px;
    font-family: inherit;
  }
  input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--accent);
  }
  textarea { resize: vertical; line-height: 1.55; }
  .mono { font-family: "Consolas", "D2Coding", monospace; font-size: 13px; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  @media (max-width: 640px) {
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
  }

  .btn {
    padding: 10px 14px;
    border-radius: 9px;
    border: 1px solid var(--border);
    background: #1e293b;
    color: #fff;
    font-size: 13.5px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .btn:hover { filter: brightness(1.08); }
  .btn:disabled { opacity: 0.55; cursor: wait; }
  .btn.full { width: 100%; }
  .btn.primary { background: linear-gradient(135deg, #0284c7, #4f46e5); border: none; }
  .btn.ok { background: #059669; border: none; }
  .btn.danger { background: #991b1b; border-color: #ef4444; }
  .btn.sm { padding: 6px 10px; font-size: 12px; }

  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .row-between { display: flex; gap: 8px; align-items: center; justify-content: space-between; flex-wrap: wrap; }

  .file-list { display: flex; flex-direction: column; gap: 6px; max-height: 62vh; overflow-y: auto; }
  .file-item {
    padding: 9px 11px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    transition: border-color 0.15s;
  }
  .file-item:hover, .file-item.selected { border-color: var(--accent); }
  .file-item .fname { font-size: 13px; font-weight: 700; color: var(--text); }
  .file-item .fmeta { font-size: 11.5px; color: var(--muted); margin-top: 2px; display: flex; justify-content: space-between; }

  .ep-list { margin-top: 8px; display: flex; flex-direction: column; gap: 5px; }
  .ep-item {
    padding: 8px 10px;
    background: #111c33;
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    font-size: 12.5px;
  }
  .ep-item:hover { border-color: var(--accent); }
  .ep-item.active { border-color: var(--ok); background: #0c2a2a; }
  .ep-badges { display: flex; gap: 5px; margin-top: 3px; flex-wrap: wrap; }
  .tag {
    font-size: 10.5px;
    padding: 1px 6px;
    border-radius: 6px;
    background: #1e293b;
    color: #cbd5e1;
  }
  .tag.high { background: #7f1d1d; color: #fecaca; }
  .tag.medium { background: #78350f; color: #fde68a; }
  .tag.low { background: #1e293b; color: #94a3b8; }
  .tag.inner { background: #312e81; color: #c7d2fe; }

  .mode-banner {
    padding: 10px 12px;
    border-radius: 10px;
    background: #0f172a;
    border: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 13px;
  }
  .mode-banner.edit-mode { border-color: var(--warn); background: #1c1917; }

  .chip-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
  .chip {
    font-size: 12px;
    padding: 4px 9px;
    border-radius: 999px;
    background: var(--bg2);
    border: 1px solid var(--border);
    color: var(--accent);
    cursor: pointer;
  }
  .chip:hover { border-color: var(--accent); }

  .tab-group { display: inline-flex; background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; padding: 2px; }
  .tab-btn {
    border: none;
    background: transparent;
    color: var(--muted);
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
  }
  .tab-btn.active { background: var(--primary); color: #fff; }

  .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text); cursor: pointer; }
  .checkbox-row input { width: auto; }
</style>
</head>
<body>

<header class="topbar">
  <div class="brand">
    <h1>AutoScenarioWriter</h1>
    <span class="badge">Alpha</span>
    <span id="modelPill" class="pill">모델 로딩 중...</span>
  </div>
  <div class="nav-actions">
    <button id="navEditor" class="nav-btn active" onclick="switchView('editor')">📝 시나리오 · 내적발화 에디터</button>
    <button id="navSetup" class="nav-btn" onclick="switchView('setup')">⚙️ 모델 · 초기 설정</button>
  </div>
</header>

<!-- =========================== SETUP / SETTINGS VIEW =========================== -->
<main id="viewSetup" class="setup-container hidden">
  <div id="setupStatus" class="status"></div>

  <section class="card">
    <h2 class="card-title">🚀 AutoScenarioWriter Alpha 초기 설정</h2>
    <p class="subtext">
      각 연구자가 사용하는 AI 모델(Gemini, OpenAI, OpenRouter, 로컬 Ollama, 사내/연구실 커스텀 서버 등)과
      시나리오 저장 경로를 설정하세요. 설정을 완료하면 다음 실행부터는 바로 에디터 화면이 자동으로 열립니다.
    </p>
  </section>

  <section class="card">
    <h3 class="card-title">1. AI 모델 연결 설정</h3>
    <div class="grid-2">
      <div>
        <label>LLM 제공자 (Provider)</label>
        <select id="sProvider" onchange="onProviderChange()"></select>
      </div>
      <div>
        <label>모델명 (직접 입력 가능)</label>
        <input id="sModel" type="text" placeholder="예: gemini-2.5-flash, gpt-4o-mini, qwen2.5:7b" />
      </div>
    </div>

    <div>
      <label>추천 모델 빠른 선택</label>
      <div id="sModelChips" class="chip-list"></div>
      <p id="sProviderHelp" class="subtext" style="margin-top:6px;"></p>
    </div>

    <div class="grid-2">
      <div>
        <label>API Base URL (OpenAI 호환 엔드포인트)</label>
        <input id="sBaseUrl" type="text" placeholder="https://..." />
      </div>
      <div>
        <label id="sKeyLabel">API 키 (로컬 .env에 안전하게 저장됨)</label>
        <input id="sApiKey" type="password" placeholder="새 API 키 입력 (기존 키 유지 시 비워두기)" autocomplete="off" />
        <p id="sKeyHint" class="subtext" style="margin-top:4px;"></p>
      </div>
    </div>

    <div class="row">
      <button id="btnTestLLM" class="btn" onclick="testConnection()">🔌 모델 연결 테스트</button>
      <span id="testResultText" class="subtext"></span>
    </div>
  </section>

  <section class="card">
    <h3 class="card-title">2. 저장 경로 및 연구자 기본 정보</h3>
    <div>
      <label>시나리오 저장 폴더 (상대 경로 또는 절대 경로)</label>
      <input id="sOutDir" type="text" placeholder="./scenarios" />
      <p class="subtext" style="margin-top:4px;">
        기본값은 현재 폴더의 <code>./scenarios</code>입니다. MemoryAI 프로젝트와 바로 연동하려면
        <code>../MemoryAI/datasets/scenarios</code>처럼 지정할 수 있습니다.
      </p>
    </div>

    <div class="grid-2">
      <div>
        <label>연구자 작성자 ID (내적발화 author 기본값)</label>
        <input id="sAuthor" type="text" placeholder="human_researcher" />
      </div>
      <div>
        <label>기억 공고화 사이클 일수 (cycle_days)</label>
        <input id="sCycleDays" type="number" min="1" value="10" />
      </div>
    </div>

    <div class="grid-3">
      <div>
        <label>사용자 역할 (user_role)</label>
        <input id="sUserRole" type="text" placeholder="인간 연구자 (사용자)" />
      </div>
      <div>
        <label>AI 역할 (agent_role)</label>
        <input id="sAgentRole" type="text" placeholder="장기기억 AI 어시스턴트" />
      </div>
      <div>
        <label>연구/대화 도메인 (domain)</label>
        <input id="sDomain" type="text" placeholder="일상 및 연구·개발 협업" />
      </div>
    </div>

    <button id="btnSaveSetup" class="btn primary full" onclick="saveSettings()">✅ 설정 저장하고 에디터 시작하기</button>
  </section>
</main>

<!-- =========================== EDITOR VIEW =========================== -->
<main id="viewEditor" class="container hidden">
  <div id="editorStatus" class="status"></div>

  <div class="layout">
    <!-- Left Sidebar: Scenario & Episode Browser -->
    <aside class="card">
      <div class="card-title">
        <span>📂 저장된 시나리오</span>
        <button class="btn sm primary" onclick="startNewEpisode()">+ 새 에피소드</button>
      </div>
      <p id="outDirLabel" class="subtext" style="word-break:break-all;"></p>
      <div id="fileList" class="file-list"></div>
    </aside>

    <!-- Right Main Panel: Scenario + Inner Speech Editor -->
    <div>
      <div id="modeBanner" class="mode-banner">
        <span id="modeText"><strong>새 에피소드 작성 모드</strong> — 날짜별 <code>YYYY_MM_DD.json</code>에 새 에피소드를 추가합니다.</span>
        <div class="row">
          <button id="btnCancelEdit" class="btn sm hidden" onclick="startNewEpisode()">새 에피소드로 전환</button>
          <button id="btnDeleteEp" class="btn sm danger hidden" onclick="deleteCurrentEpisode()">🗑 에피소드 삭제</button>
        </div>
      </div>

      <!-- AI Draft Box -->
      <section class="card" style="margin-top:12px;">
        <div class="card-title">
          <span>✨ AI 초안 자동 생성 (선택)</span>
          <label class="checkbox-row" style="margin:0; font-weight:500;">
            <input id="chkDraftInner" type="checkbox" checked />
            내적 발화 초안도 함께 생성
          </label>
        </div>
        <textarea id="rawInput" rows="4" placeholder="오늘의 메모, 사건, 대화 원문, 속마음을 자유롭게 적어보세요. AI가 MemoryAI v1.0.0 표준 구조와 내적 발화 초안으로 정리해 드립니다. (AI 없이 아래 폼에 직접 작성·수정하는 것도 가능합니다.)"></textarea>
        <button id="btnDraft" class="btn primary" onclick="generateWithAI()">✨ AI로 시나리오 · 내적발화 초안 생성</button>
      </section>

      <!-- Scenario Episode JSON Editor -->
      <section class="card">
        <h3 class="card-title">📄 시나리오 에피소드 편집 (MemoryAI Scenario v1.0.0)</h3>

        <div class="grid-3">
          <div>
            <label>날짜 (date / 파일명 기준)</label>
            <input id="fDate" type="date" />
          </div>
          <div>
            <label>시나리오 유형 (scenario_type)</label>
            <select id="fType">
              <option value="hidden_intent_conflict">hidden_intent_conflict (표면·숨은 의도 충돌)</option>
              <option value="belief_revision_setup">belief_revision_setup (전제 뒤집기 - 설정)</option>
              <option value="belief_revision_flip">belief_revision_flip (전제 뒤집기 - 반전)</option>
              <option value="delayed_feedback_setup">delayed_feedback_setup (지연 피드백 - 원인)</option>
              <option value="delayed_feedback_result">delayed_feedback_result (지연 피드백 - 결과)</option>
              <option value="value_tradeoff">value_tradeoff (다중 가치 충돌)</option>
              <option value="routine_low_salience" selected>routine_low_salience (단순 일상 · 망각 대조군)</option>
              <option value="multi_memory_synthesis">multi_memory_synthesis (다중 기억 종합 회고)</option>
            </select>
          </div>
          <div>
            <label>중요도 등급 (expected_salience)</label>
            <select id="fSalience">
              <option value="high">high (장기기억 보존)</option>
              <option value="medium" selected>medium (일반 기록)</option>
              <option value="low">low (의도적 망각 대상)</option>
            </select>
          </div>
        </div>

        <div class="grid-2">
          <div>
            <label>제목 (title)</label>
            <input id="fTitle" type="text" placeholder="사건의 핵심 요약 제목" />
          </div>
          <div>
            <label>연결된 과거 일차 (linked_days — 쉼표 구분 숫자, 선택)</label>
            <input id="fLinkedDays" type="text" placeholder="예: 1, 3 (현재 일차보다 작은 숫자)" />
          </div>
        </div>

        <div class="grid-2">
          <div>
            <label>인지 함정 / 관찰 포인트 (cognitive_trap)</label>
            <input id="fTrap" type="text" placeholder="예: 표면 요청만 보고 감정적 압박을 놓침 (없으면 '없음')" />
          </div>
          <div>
            <label>관계적 관찰 목표 (relational_goal — 선택)</label>
            <input id="fRelGoal" type="text" placeholder="AI가 파악하고 공감해야 할 관계적 맥락" />
          </div>
        </div>

        <div>
          <label>기대 행동 원칙 (expected_principle — 공고화 후 기대되는 If-Then 원칙, 선택)</label>
          <input id="fPrinciple" type="text" placeholder="예: 사용자가 마감 압박을 호소할 때는 해결책보다 감정 확인과 우선순위 정리를 먼저 제안한다." />
        </div>

        <div>
          <label>정제된 대화 로그 (chat_log)</label>
          <textarea id="fChatLog" rows="7" placeholder="사용자: ...&#10;AI: ..."></textarea>
        </div>
      </section>

      <!-- Inner Speech Editor (First-Class Section) -->
      <section class="card inner-card">
        <div class="card-title">
          <span>🧠 인간의 내적 발화 에디터 (Inner Speech)</span>
          <div class="tab-group">
            <button id="tabInnerForm" class="tab-btn active" onclick="setInnerMode('form')">구조화 편집</button>
            <button id="tabInnerRaw" class="tab-btn" onclick="setInnerMode('raw')">마크다운 원문 편집</button>
          </div>
        </div>
        <p class="subtext">
          대화 로그에 직접 드러나지 않는 인간의 속마음, 숨은 맥락, AI 반응에 대한 사후 평가를 기록·수정합니다.
          입력 내용이 있으면 <code>inner_speech_&lt;scenario_id&gt;.md</code>로 자동 연동 저장됩니다.
        </p>

        <!-- Structured Inner Speech Form -->
        <div id="innerFormPanel" style="display:flex; flex-direction:column; gap:10px;">
          <div class="grid-3">
            <div>
              <label>작성자 (author)</label>
              <input id="fInnerAuthor" type="text" placeholder="human_researcher" />
            </div>
            <div>
              <label>감정 톤 태그 (emotional_tone, 쉼표 구분)</label>
              <input id="fTone" type="text" placeholder="고민, 기대, 답답함" />
            </div>
            <div>
              <label>AI 맥락 이해도 사후 평가 (1~5점)</label>
              <select id="fCompScore">
                <option value="">미평가 (null)</option>
                <option value="1">1점 — 맥락을 전혀 포착하지 못함</option>
                <option value="2">2점 — 표면적 이해에 그침</option>
                <option value="3">3점 — 보통 수준으로 이해</option>
                <option value="4">4점 — 숨은 의도를 잘 포착함</option>
                <option value="5">5점 — 깊은 관계적 공감 및 이해</option>
              </select>
            </div>
          </div>

          <div>
            <label>인간의 내적 발화 (# 인간의 내적 발화)</label>
            <textarea id="fInnerText" rows="4" placeholder="대화 전후 머릿속에 떠올랐던 정제되지 않은 생각, 망설임, 속마음을 자유롭게 작성·수정하세요."></textarea>
          </div>

          <div>
            <label>숨은 맥락 및 의도 (## 숨은 맥락 및 의도)</label>
            <textarea id="fHiddenContext" rows="3" placeholder="AI에게 직접 말하지는 않았지만, AI가 눈치채거나 함께 고민해 주길 바랐던 핵심 맥락"></textarea>
          </div>

          <div style="border-top:1px solid #312e81; padding-top:10px;">
            <label style="color:#c7d2fe; margin-bottom:8px;">AI 반응에 대한 인간 연구자의 사후 평가 (Human Evaluation)</label>
            <div class="grid-2">
              <div>
                <label>관계적 자연스러움</label>
                <input id="fEvalNat" type="text" placeholder="AI가 단순 명령 입력기가 아닌 관계적 상대로 대했는가?" />
              </div>
              <div>
                <label>맥락 포착 여부</label>
                <input id="fEvalCtx" type="text" placeholder="내적 발화의 결을 어느 정도 이해했는가?" />
              </div>
            </div>
            <div style="margin-top:8px;">
              <label>수정 / 보완 메모 (다음 10일 목차·DPO 학습 피드백)</label>
              <textarea id="fEvalNotes" rows="2" placeholder="향후 기억 공고화나 DPO 학습에 반영되었으면 하는 연구자 메모"></textarea>
            </div>
          </div>

          <div>
            <label>(선택) JSON 인라인 짧은 내적 발화 (inner_speech_inline)</label>
            <input id="fInnerInline" type="text" placeholder="JSON 파일 내부에도 한 줄 요약을 남기고 싶을 때 입력" />
          </div>
        </div>

        <!-- Raw Markdown Inner Speech Panel -->
        <div id="innerRawPanel" class="hidden">
          <label>inner_speech 마크다운 원문 직접 편집</label>
          <textarea id="fInnerRaw" class="mono" rows="16" placeholder="---\nscenario_id: ...\n---"></textarea>
          <p class="subtext" style="margin-top:4px;">
            원문 편집 탭에서 저장하면 위 마크다운 텍스트가 그대로 <code>inner_speech_*.md</code>에 저장됩니다.
          </p>
        </div>
      </section>

      <button id="btnSave" class="btn ok full" onclick="saveCurrentEpisode()">💾 시나리오 및 내적발화 저장</button>
    </div>
  </div>
</main>

<script>
let appSettings = null;
let selectedFile = null;
let loadedFileDoc = null;
let editingFile = null;
let editingIndex = null;
let innerEditMode = "form";

function todayIso() {
  const d = new Date();
  const offset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 10);
}

function showStatus(targetId, msg, kind = "ok") {
  const el = document.getElementById(targetId);
  el.className = "status " + kind;
  el.textContent = msg;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearStatus(targetId) {
  const el = document.getElementById(targetId);
  el.className = "status";
  el.textContent = "";
}

function switchView(view) {
  const vSetup = document.getElementById("viewSetup");
  const vEditor = document.getElementById("viewEditor");
  const nSetup = document.getElementById("navSetup");
  const nEditor = document.getElementById("navEditor");
  if (view === "setup") {
    vSetup.classList.remove("hidden");
    vEditor.classList.add("hidden");
    nSetup.classList.add("active");
    nEditor.classList.remove("active");
  } else {
    vSetup.classList.add("hidden");
    vEditor.classList.remove("hidden");
    nSetup.classList.remove("active");
    nEditor.classList.add("active");
    refreshFileList();
  }
}

/* ==================== SETTINGS ==================== */
async function loadSettings() {
  const res = await fetch("/api/settings");
  appSettings = await res.json();

  const providerSel = document.getElementById("sProvider");
  providerSel.innerHTML = Object.entries(appSettings.presets).map(([k, p]) =>
    `<option value="${k}">${p.label}</option>`
  ).join("");

  providerSel.value = appSettings.llm.provider || "gemini";
  onProviderChange(true);

  document.getElementById("sModel").value = appSettings.llm.model || "";
  document.getElementById("sBaseUrl").value = appSettings.llm.base_url || "";
  document.getElementById("sApiKey").value = "";
  document.getElementById("sOutDir").value = appSettings.paths.output_scenarios_dir || "./scenarios";
  document.getElementById("sAuthor").value = appSettings.defaults.author || "human_researcher";
  document.getElementById("sCycleDays").value = appSettings.defaults.cycle_days || 10;
  document.getElementById("sUserRole").value = appSettings.defaults.user_role || "";
  document.getElementById("sAgentRole").value = appSettings.defaults.agent_role || "";
  document.getElementById("sDomain").value = appSettings.defaults.domain || "";

  document.getElementById("modelPill").textContent =
    `${appSettings.llm.provider} · ${appSettings.llm.model || "미설정"}`;
  document.getElementById("outDirLabel").textContent =
    `저장 폴더: ${appSettings.paths.resolved_output_dir}`;
  document.getElementById("fInnerAuthor").value = appSettings.defaults.author || "human_researcher";

  if (!appSettings.setup_completed) {
    switchView("setup");
    showStatus("setupStatus", "처음 실행하셨습니다! 사용할 AI 모델과 저장 경로를 설정한 뒤 시작해 주세요.", "info");
  } else {
    switchView("editor");
  }
}

function onProviderChange(isInit = false) {
  if (!appSettings) return;
  const prov = document.getElementById("sProvider").value;
  const preset = appSettings.presets[prov] || appSettings.presets.custom;

  if (!isInit) {
    document.getElementById("sBaseUrl").value = preset.base_url || "";
    if (preset.default_model) {
      document.getElementById("sModel").value = preset.default_model;
    }
  }

  document.getElementById("sProviderHelp").textContent = preset.help || "";
  const chips = document.getElementById("sModelChips");
  if (preset.suggested_models && preset.suggested_models.length) {
    chips.innerHTML = preset.suggested_models.map(m =>
      `<span class="chip" onclick="document.getElementById('sModel').value='${m}'">${m}</span>`
    ).join("");
  } else {
    chips.innerHTML = `<span class="subtext">사용 중인 서버의 모델명을 직접 입력해 주세요.</span>`;
  }

  const keyInput = document.getElementById("sApiKey");
  const keyHint = document.getElementById("sKeyHint");
  if (!preset.requires_key) {
    keyInput.placeholder = "선택 입력 (로컬 Ollama/사내 서버는 비워두어도 됩니다)";
    keyHint.textContent = "API 키 없이 바로 연결할 수 있습니다.";
  } else {
    keyInput.placeholder = "API 키를 입력하세요";
    if (appSettings.llm.provider === prov && appSettings.llm.has_api_key) {
      keyHint.textContent = `현재 저장된 키 있음: ${appSettings.llm.api_key_masked} (변경할 때만 새로 입력)`;
    } else {
      keyHint.textContent = `환경변수 ${preset.api_key_env} 이름으로 로컬 .env에 저장됩니다.`;
    }
  }
}

async function testConnection() {
  const btn = document.getElementById("btnTestLLM");
  const out = document.getElementById("testResultText");
  btn.disabled = true;
  out.textContent = "연결 확인 중...";
  try {
    const res = await fetch("/api/test-llm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: document.getElementById("sProvider").value,
        model: document.getElementById("sModel").value.trim(),
        base_url: document.getElementById("sBaseUrl").value.trim(),
        api_key: document.getElementById("sApiKey").value.trim(),
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    out.textContent = `✅ 연결 성공! (${data.model} 응답: ${data.reply})`;
    showStatus("setupStatus", `모델 연결 성공: ${data.model}`, "ok");
  } catch (e) {
    out.textContent = `❌ 연결 실패`;
    showStatus("setupStatus", "모델 연결 테스트 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function saveSettings() {
  const btn = document.getElementById("btnSaveSetup");
  btn.disabled = true;
  try {
    const payload = {
      llm: {
        provider: document.getElementById("sProvider").value,
        model: document.getElementById("sModel").value.trim(),
        base_url: document.getElementById("sBaseUrl").value.trim(),
        api_key: document.getElementById("sApiKey").value.trim(),
      },
      paths: {
        output_scenarios_dir: document.getElementById("sOutDir").value.trim() || "./scenarios",
      },
      defaults: {
        author: document.getElementById("sAuthor").value.trim() || "human_researcher",
        cycle_days: parseInt(document.getElementById("sCycleDays").value || "10", 10),
        user_role: document.getElementById("sUserRole").value.trim(),
        agent_role: document.getElementById("sAgentRole").value.trim(),
        domain: document.getElementById("sDomain").value.trim(),
      }
    };
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    appSettings = data;
    document.getElementById("modelPill").textContent =
      `${appSettings.llm.provider} · ${appSettings.llm.model}`;
    document.getElementById("outDirLabel").textContent =
      `저장 폴더: ${appSettings.paths.resolved_output_dir}`;
    document.getElementById("fInnerAuthor").value = appSettings.defaults.author || "human_researcher";
    clearStatus("setupStatus");
    switchView("editor");
    showStatus("editorStatus", "설정이 저장되었습니다! 이제 시나리오와 내적 발화를 작성·편집할 수 있습니다.", "ok");
  } catch (e) {
    showStatus("setupStatus", "설정 저장 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

/* ==================== FILE & EPISODE BROWSER ==================== */
async function refreshFileList() {
  const res = await fetch("/api/recent");
  const items = await res.json();
  const list = document.getElementById("fileList");
  if (!items.length) {
    list.innerHTML = `<div class="subtext" style="padding:8px;">아직 저장된 시나리오 파일이 없습니다.<br/>오른쪽에서 첫 시나리오를 작성해 보세요!</div>`;
    return;
  }
  list.innerHTML = items.map(it => {
    const isSel = selectedFile === it.file;
    let epsHtml = "";
    if (isSel && loadedFileDoc && loadedFileDoc.file === it.file) {
      epsHtml = `<div class="ep-list">` + loadedFileDoc.episodes.map(ep => {
        const isActive = editingFile === it.file && editingIndex === ep._index;
        const hasInner = Boolean(ep.inner_speech_file || ep.inner_speech_inline);
        return `
          <div class="ep-item ${isActive ? 'active' : ''}" onclick="event.stopPropagation(); selectEpisode('${it.file}', ${ep._index})">
            <div><strong>Day ${ep.day}</strong> · ${escapeHtml(ep.title || "(제목 없음)")}</div>
            <div class="ep-badges">
              <span class="tag ${ep.expected_salience || 'medium'}">${ep.expected_salience || 'medium'}</span>
              ${hasInner ? '<span class="tag inner">🧠 내적발화</span>' : ''}
            </div>
          </div>
        `;
      }).join("") + `</div>`;
    }
    return `
      <div class="file-item ${isSel ? 'selected' : ''}" onclick="openScenarioFile('${it.file}')">
        <div class="fname">${escapeHtml(it.file)}</div>
        <div class="fmeta">
          <span>${escapeHtml(it.title)}</span>
          <span>${it.count}건 · 🧠${it.inner_count || 0}</span>
        </div>
        ${epsHtml}
      </div>
    `;
  }).join("");
}

async function openScenarioFile(filename) {
  try {
    const res = await fetch("/api/scenario?file=" + encodeURIComponent(filename));
    const doc = await res.json();
    if (!res.ok) throw new Error(doc.error || res.statusText);
    selectedFile = filename;
    loadedFileDoc = doc;
    await refreshFileList();
    if (doc.episodes && doc.episodes.length) {
      selectEpisode(filename, doc.episodes[0]._index);
    }
  } catch (e) {
    showStatus("editorStatus", "파일 불러오기 실패: " + e.message, "err");
  }
}

function selectEpisode(filename, idx) {
  if (!loadedFileDoc || loadedFileDoc.file !== filename) return;
  const ep = loadedFileDoc.episodes.find(e => e._index === idx);
  if (!ep) return;

  editingFile = filename;
  editingIndex = idx;

  document.getElementById("fDate").value = ep.date || todayIso();
  document.getElementById("fTitle").value = ep.title || "";
  document.getElementById("fType").value = ep.scenario_type || "routine_low_salience";
  document.getElementById("fSalience").value = ep.expected_salience || "medium";
  document.getElementById("fLinkedDays").value = Array.isArray(ep.linked_days) ? ep.linked_days.join(", ") : "";
  document.getElementById("fTrap").value = ep.cognitive_trap || "";
  document.getElementById("fRelGoal").value = ep.relational_goal || "";
  document.getElementById("fPrinciple").value = ep.expected_principle || "";
  document.getElementById("fChatLog").value = ep.chat_log || "";
  document.getElementById("fInnerInline").value = ep.inner_speech_inline || "";

  const inner = ep._inner_speech_data || {};
  document.getElementById("fInnerAuthor").value =
    inner.author || (appSettings && appSettings.defaults.author) || "human_researcher";
  document.getElementById("fTone").value = inner.emotional_tone || "";
  document.getElementById("fCompScore").value = inner.ai_comprehension_score || "";
  document.getElementById("fInnerText").value = inner.inner_speech || "";
  document.getElementById("fHiddenContext").value = inner.hidden_context || "";
  document.getElementById("fEvalNat").value = inner.eval_naturalness || "";
  document.getElementById("fEvalCtx").value = inner.eval_context || "";
  document.getElementById("fEvalNotes").value = inner.eval_notes || "";
  document.getElementById("fInnerRaw").value = inner.raw_markdown || buildMarkdownPreview(ep.scenario_id || "day_001");

  updateModeBanner();
  refreshFileList();
}

function startNewEpisode() {
  editingFile = null;
  editingIndex = null;
  document.getElementById("fDate").value = todayIso();
  document.getElementById("rawInput").value = "";
  document.getElementById("fTitle").value = "";
  document.getElementById("fType").value = "routine_low_salience";
  document.getElementById("fSalience").value = "medium";
  document.getElementById("fLinkedDays").value = "";
  document.getElementById("fTrap").value = "";
  document.getElementById("fRelGoal").value = "";
  document.getElementById("fPrinciple").value = "";
  document.getElementById("fChatLog").value = "";
  document.getElementById("fInnerInline").value = "";

  document.getElementById("fInnerAuthor").value =
    (appSettings && appSettings.defaults.author) || "human_researcher";
  document.getElementById("fTone").value = "";
  document.getElementById("fCompScore").value = "";
  document.getElementById("fInnerText").value = "";
  document.getElementById("fHiddenContext").value = "";
  document.getElementById("fEvalNat").value = "";
  document.getElementById("fEvalCtx").value = "";
  document.getElementById("fEvalNotes").value = "";
  document.getElementById("fInnerRaw").value = "";

  setInnerMode("form");
  updateModeBanner();
  refreshFileList();
}

function updateModeBanner() {
  const banner = document.getElementById("modeBanner");
  const text = document.getElementById("modeText");
  const btnCancel = document.getElementById("btnCancelEdit");
  const btnDel = document.getElementById("btnDeleteEp");
  const btnSave = document.getElementById("btnSave");

  if (editingFile !== null && editingIndex !== null) {
    banner.classList.add("edit-mode");
    text.innerHTML = `<strong>편집 모드</strong> — <code>${escapeHtml(editingFile)}</code>의 <strong>#${editingIndex + 1}번째 에피소드</strong>와 내적 발화를 수정 중입니다.`;
    btnCancel.classList.remove("hidden");
    btnDel.classList.remove("hidden");
    btnSave.textContent = "💾 수정 내용 덮어쓰기 저장 (JSON + 내적발화 MD)";
  } else {
    banner.classList.remove("edit-mode");
    text.innerHTML = `<strong>새 에피소드 작성 모드</strong> — 날짜별 <code>YYYY_MM_DD.json</code>에 새 에피소드를 추가합니다.`;
    btnCancel.classList.add("hidden");
    btnDel.classList.add("hidden");
    btnSave.textContent = "💾 새 에피소드 저장 (JSON + 내적발화 MD)";
  }
}

/* ==================== INNER SPEECH MODE ==================== */
function buildMarkdownPreview(scenarioId = "draft") {
  const author = document.getElementById("fInnerAuthor").value.trim() || "human_researcher";
  const tones = document.getElementById("fTone").value.split(",").map(s => s.trim()).filter(Boolean);
  const score = document.getElementById("fCompScore").value || "null";
  return [
    "---",
    `scenario_id: ${scenarioId}`,
    `author: ${author}`,
    `emotional_tone: [${tones.join(", ")}]`,
    `ai_comprehension_score: ${score}`,
    "---",
    "",
    "# 인간의 내적 발화 (Inner Speech)",
    document.getElementById("fInnerText").value.trim(),
    "",
    "## 숨은 맥락 및 의도 (Hidden Context)",
    document.getElementById("fHiddenContext").value.trim(),
    "",
    "## AI 반응에 대한 인간 연구자의 사후 평가 (Human Evaluation)",
    `- **관계적 자연스러움:** ${document.getElementById("fEvalNat").value.trim()}`,
    `- **맥락 포착 여부:** ${document.getElementById("fEvalCtx").value.trim()}`,
    `- **수정/보완 메모:** ${document.getElementById("fEvalNotes").value.trim()}`,
    ""
  ].join("\n");
}

function setInnerMode(mode) {
  innerEditMode = mode;
  const formP = document.getElementById("innerFormPanel");
  const rawP = document.getElementById("innerRawPanel");
  const tForm = document.getElementById("tabInnerForm");
  const tRaw = document.getElementById("tabInnerRaw");
  if (mode === "raw") {
    if (!document.getElementById("fInnerRaw").value.trim()) {
      document.getElementById("fInnerRaw").value = buildMarkdownPreview();
    }
    formP.classList.add("hidden");
    rawP.classList.remove("hidden");
    tForm.classList.remove("active");
    tRaw.classList.add("active");
  } else {
    formP.classList.remove("hidden");
    rawP.classList.add("hidden");
    tForm.classList.add("active");
    tRaw.classList.remove("active");
  }
}

/* ==================== AI DRAFT & SAVE ==================== */
async function generateWithAI() {
  const raw = document.getElementById("rawInput").value.trim();
  const dateIso = document.getElementById("fDate").value || todayIso();
  const includeInner = document.getElementById("chkDraftInner").checked;
  if (!raw) {
    showStatus("editorStatus", "먼저 오늘의 메모나 대화 원문을 입력해 주세요.", "err");
    return;
  }
  const btn = document.getElementById("btnDraft");
  btn.disabled = true;
  btn.textContent = "⏳ AI가 시나리오와 내적 발화 초안을 생성하는 중...";
  try {
    const res = await fetch("/api/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_input: raw,
        date: dateIso,
        include_inner_speech: includeInner
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    document.getElementById("fTitle").value = data.title || "";
    document.getElementById("fType").value = data.scenario_type || "routine_low_salience";
    document.getElementById("fSalience").value = data.expected_salience || "medium";
    document.getElementById("fTrap").value = data.cognitive_trap || "";
    document.getElementById("fPrinciple").value = data.expected_principle || "";
    document.getElementById("fRelGoal").value = data.relational_goal || "";
    document.getElementById("fChatLog").value = data.chat_log || "";

    if (data.inner_speech_data) {
      document.getElementById("fTone").value = data.inner_speech_data.emotional_tone || "";
      document.getElementById("fInnerText").value = data.inner_speech_data.inner_speech || "";
      document.getElementById("fHiddenContext").value = data.inner_speech_data.hidden_context || "";
      document.getElementById("fInnerRaw").value = buildMarkdownPreview();
    }
    showStatus("editorStatus", "AI 초안 생성 완료! 아래 시나리오와 내적 발화 내용을 자유롭게 수정한 뒤 저장하세요.", "ok");
  } catch (e) {
    showStatus("editorStatus", "AI 초안 생성 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ AI로 시나리오 · 내적발화 초안 생성";
  }
}

async function saveCurrentEpisode() {
  const dateIso = document.getElementById("fDate").value || todayIso();
  const chatLog = document.getElementById("fChatLog").value.trim();
  if (!chatLog) {
    showStatus("editorStatus", "정제된 대화 로그(chat_log)가 비어 있습니다. 내용을 입력해 주세요.", "err");
    return;
  }

  const payload = {
    date: dateIso,
    target_filename: editingFile,
    episode_index: editingIndex,
    episode: {
      date: dateIso,
      title: document.getElementById("fTitle").value.trim(),
      scenario_type: document.getElementById("fType").value,
      expected_salience: document.getElementById("fSalience").value,
      linked_days: document.getElementById("fLinkedDays").value.trim(),
      cognitive_trap: document.getElementById("fTrap").value.trim(),
      expected_principle: document.getElementById("fPrinciple").value.trim(),
      relational_goal: document.getElementById("fRelGoal").value.trim(),
      inner_speech_inline: document.getElementById("fInnerInline").value.trim(),
      chat_log: chatLog,
    },
    inner_speech_data: {
      use_raw_markdown: innerEditMode === "raw",
      raw_markdown: document.getElementById("fInnerRaw").value,
      author: document.getElementById("fInnerAuthor").value.trim(),
      emotional_tone: document.getElementById("fTone").value.trim(),
      ai_comprehension_score: document.getElementById("fCompScore").value,
      inner_speech: document.getElementById("fInnerText").value,
      hidden_context: document.getElementById("fHiddenContext").value,
      eval_naturalness: document.getElementById("fEvalNat").value,
      eval_context: document.getElementById("fEvalCtx").value,
      eval_notes: document.getElementById("fEvalNotes").value,
    }
  };

  const btn = document.getElementById("btnSave");
  btn.disabled = true;
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);

    const innerMsg = data.inner_speech_file ? ` + 내적발화(${data.inner_speech_file})` : "";
    const verb = data.mode === "updated" ? "수정 저장 완료" : "새 에피소드 저장 완료";
    showStatus("editorStatus", `${verb}: ${data.json_file}${innerMsg} (총 ${data.episode_count}건)`, "ok");

    selectedFile = data.json_file;
    await openScenarioFile(data.json_file);
    selectEpisode(data.json_file, data.episode_index);
  } catch (e) {
    showStatus("editorStatus", "저장 실패: " + e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function deleteCurrentEpisode() {
  if (editingFile === null || editingIndex === null) return;
  if (!confirm(`정말로 ${editingFile}의 #${editingIndex + 1}번째 에피소드를 삭제하시겠습니까?`)) return;
  try {
    const res = await fetch("/api/delete-episode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file: editingFile, episode_index: editingIndex })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    showStatus("editorStatus", `삭제 완료: "${data.removed_title}" (남은 에피소드 ${data.remaining}건)`, "ok");
    if (data.deleted_file) {
      selectedFile = null;
      loadedFileDoc = null;
      startNewEpisode();
    } else {
      await openScenarioFile(data.file);
    }
  } catch (e) {
    showStatus("editorStatus", "삭제 실패: " + e.message, "err");
  }
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

document.getElementById("fDate").value = todayIso();
loadSettings();
</script>
</body>
</html>
"""


class AutoWriterHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/setup"):
            raw = HTML_UI.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/settings":
            self._send_json(get_public_settings())
            return

        if path == "/api/recent":
            self._send_json(list_daily_scenarios())
            return

        if path == "/api/scenario":
            filename = (qs.get("file") or [""])[0]
            try:
                self._send_json(load_scenario_file(filename))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/settings":
            try:
                body = self._read_json()
                updated = save_user_settings(body)
                self._send_json(updated)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/test-llm":
            try:
                body = self._read_json()
                result = test_llm_connection(override=body)
                self._send_json(result)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/draft":
            try:
                body = self._read_json()
                draft = draft_episode_with_ai(
                    raw_input=str(body.get("raw_input") or ""),
                    date_iso=body.get("date") or dt.date.today().isoformat(),
                    include_inner_speech=bool(body.get("include_inner_speech", False)),
                )
                self._send_json(draft)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/save":
            try:
                body = self._read_json()
                ep_idx = body.get("episode_index")
                if ep_idx is not None and ep_idx != "":
                    ep_idx = int(ep_idx)
                else:
                    ep_idx = None
                result = save_daily_scenario(
                    episode_data=body.get("episode") or {},
                    date_iso=body.get("date"),
                    inner_speech_data=body.get("inner_speech_data"),
                    target_filename=body.get("target_filename") or None,
                    episode_index=ep_idx,
                    inner_speech_text=str(body.get("inner_speech") or ""),
                    hidden_context_text=str(body.get("hidden_context") or ""),
                    emotional_tone=str(body.get("emotional_tone") or ""),
                )
                self._send_json(result)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/delete-episode":
            try:
                body = self._read_json()
                result = delete_episode(
                    filename=str(body.get("file") or ""),
                    episode_index=int(body.get("episode_index")),
                )
                self._send_json(result)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return


def run_server(open_browser: bool = True) -> None:
    cfg = load_config()
    srv_cfg = cfg.get("server", {})
    host = srv_cfg.get("host", "0.0.0.0")
    port = int(srv_cfg.get("port", 8770))
    lan_ip = _detect_lan_ip()
    out_dir = get_output_dir(cfg)
    setup_done = is_setup_completed(cfg)

    server = ThreadingHTTPServer((host, port), AutoWriterHandler)
    print("============================================================")
    print(f"  AutoScenarioWriter {APP_VERSION} 실행 중 (종료: Ctrl+C)")
    print(f"  - PC 접속:     http://127.0.0.1:{port}")
    print(f"  - 모바일 접속: http://{lan_ip}:{port}  (같은 Wi-Fi)")
    print(f"  - 저장 경로:   {out_dir}")
    if not setup_done:
        print("  - 안내: 초기 설정이 필요합니다. 열리는 웹페이지에서 사용할 모델을 설정해 주세요.")
    print("============================================================")

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[AutoScenarioWriter] 서버를 종료했습니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoScenarioWriter Alpha Local & Mobile Web App")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="실행 시 웹 브라우저를 자동으로 열지 않습니다 (백그라운드 실행용).",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="(하위 호환용) 실행 시 웹 브라우저를 자동으로 엽니다 (기본값이 이미 자동 실행입니다).",
    )
    args = parser.parse_args()
    run_server(open_browser=not args.no_open)
