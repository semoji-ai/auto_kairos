// Swarm Canvas v2 — Energy theme
//
// 메타포: 에너지의 흐름
// - 클레임 = 에너지 오브 (researcher 셀 안에 spawn)
// - 인용 연결선 = SVG path 따라 입자들이 흘러서 원고 위치에 도착
// - 도착 순간: 글자가 단어 단위로 fade-in (energy → text 응결)
//
// 사용자 결정 (2026-04-09):
// - 캐릭터 직업 X, 그냥 "리서처"
// - 60/40, 단어 단위 typing, 에너지 메타포

(() => {
  const page = document.querySelector('.swarm-canvas-page');
  if (!page) return;

  let workspace = page.dataset.workspace || "";
  let evtSource = null;
  let startTs = null;
  let elapsedTimer = null;
  let lastManuscriptStripped = "";
  let researcherClaimCount = { R1: 0, R2: 0, R3: 0, R4: 0, R5: 0 };
  let crossCount = 0;
  let imageCount = 0;
  // claim id → DOM orb element (인용 연결선 발사 시 위치 lookup용)
  const orbsById = new Map();

  const $ = (id) => document.getElementById(id);
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  // ── helpers ─────────────────
  function setRunning(on) {
    $('btn-start-swarm').style.display = on ? 'none' : '';
    $('btn-stop-swarm').style.display = on ? '' : 'none';
    $('swarm-running-indicator').style.display = on ? '' : 'none';
  }
  function fmtElapsed(sec) {
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}m ${s}s`;
  }
  function startElapsed() {
    if (elapsedTimer) clearInterval(elapsedTimer);
    startTs = Date.now();
    elapsedTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - startTs) / 1000);
      $('swarm-elapsed').textContent = fmtElapsed(sec);
    }, 1000);
  }
  function stopElapsed() {
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  }

  // ── manuscript helpers ──────
  function stripTags(text) {
    return text
      .replace(/\[claim:[^\]]+\]/g, '')
      .replace(/\[char:[^\]]+\]/g, '')
      .replace(/\[TODO:[^\]]+\]/g, '')
      .replace(/  +/g, ' ');
  }

  function extractClaimIds(text) {
    const ids = new Set();
    const re = /\[claim:([^\]]+)\]/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      m[1].split(',').forEach(id => ids.add(id.trim()));
    }
    return Array.from(ids);
  }

  function countTags(text) {
    const claims = (text.match(/\[claim:[^\]]+\]/g) || []).length;
    const chars = (text.match(/\[char:[^\]]+\]/g) || []).length;
    $('claim-tags').textContent = `claim tags: ${claims}`;
    $('char-tags').textContent = `char tags: ${chars}`;
  }

  // ── word-by-word typing ─────
  // 새 텍스트가 들어오면 기존 텍스트 끝에 단어 단위로 추가 + fade-in 애니메이션
  function applyManuscript(fullStripped) {
    const elText = $('manuscript-text');
    if (!fullStripped) {
      elText.innerHTML = '<span class="placeholder">에너지가 응결되어 글이 되기를 기다리는 중...</span>';
      lastManuscriptStripped = "";
      return;
    }

    // 첫 호출 또는 이전 텍스트가 prefix가 아니면 통째로 다시 그림 (initial snapshot 케이스)
    if (!lastManuscriptStripped || !fullStripped.startsWith(lastManuscriptStripped)) {
      elText.innerHTML = '';
      const allWords = splitWords(fullStripped);
      allWords.forEach((w, i) => {
        const span = document.createElement('span');
        span.className = 'word';
        span.textContent = w;
        span.style.animationDelay = `${Math.min(i * 0.02, 1.6)}s`;
        elText.appendChild(span);
      });
    } else {
      // delta 추가분만 단어 단위로 추가
      const delta = fullStripped.slice(lastManuscriptStripped.length);
      const newWords = splitWords(delta);
      newWords.forEach((w, i) => {
        const span = document.createElement('span');
        span.className = 'word';
        span.textContent = w;
        span.style.animationDelay = `${i * 0.05}s`;
        elText.appendChild(span);
      });
    }
    lastManuscriptStripped = fullStripped;
  }

  // 한국어 + 공백/구두점을 단어 단위로 보존하며 split
  function splitWords(text) {
    // 공백 + 한 단어 + 공백... 패턴. 줄바꿈도 단어로 처리.
    // 간단히 \s 단위로 split하되 split 토큰(공백)도 살려서 array로
    const tokens = text.match(/(\s+|\S+)/g) || [];
    return tokens;
  }

  // ── researcher / orbs ───────
  function setResearcherActive(rid, active) {
    const cell = document.querySelector(`.researcher-cell[data-rid="${rid}"]`);
    if (!cell) return;
    cell.classList.toggle('active', !!active);
    const status = cell.querySelector('.r-status');
    if (status) status.textContent = active ? 'researching...' : 'idle';
  }

  function spawnEnergyOrb(claim) {
    const rid = claim.researcher || "R1";
    const area = document.querySelector(`.orb-area[data-rid="${rid}"]`);
    if (!area) return null;

    researcherClaimCount[rid] = (researcherClaimCount[rid] || 0) + 1;
    if (claim.cross_checked) crossCount += 1;
    if (Array.isArray(claim.image_candidates)) imageCount += claim.image_candidates.length;
    updateResearchStats();

    const orb = document.createElement('div');
    orb.className = 'energy-orb' + (claim.cross_checked ? ' cross-checked' : '');
    orb.dataset.rid = rid;
    orb.dataset.claimId = claim.id || '';

    const tip = document.createElement('div');
    tip.className = 'tip';
    const text = claim.text ? claim.text.slice(0, 200) : '';
    const sources = (claim.source_urls || (claim.source_url ? [claim.source_url] : []));
    const sourceLine = sources.slice(0, 2).map(u => {
      try { return new URL(u).hostname.replace('www.', ''); } catch { return u.slice(0, 30); }
    }).join(' + ');
    tip.innerHTML = `<div style="font-weight:600;color:var(--energy-cyan);margin-bottom:4px">${escapeHtml(claim.id || '?')}${claim.cross_checked ? ' ✓✓' : ''}</div>
                     <div style="margin-bottom:6px">${escapeHtml(text)}</div>
                     <div style="font-size:10px;color:var(--ink-low)">${escapeHtml(sourceLine)}</div>`;
    orb.appendChild(tip);

    area.appendChild(orb);
    if (claim.id) orbsById.set(claim.id, orb);
    return orb;
  }

  function updateResearchStats() {
    const total = Object.values(researcherClaimCount).reduce((a, b) => a + b, 0);
    $('research-claim-total').textContent = `claims: ${total}`;
    $('research-cross').textContent = `cross: ${crossCount}`;
    $('research-images').textContent = `images: ${imageCount}`;
  }

  // ── energy particle flow (orb → manuscript) ─────
  // SVG 곡선을 따라 작은 원 입자를 0.1s 간격으로 보내고, 도착 시 원고 위치에서 burst
  function flowEnergyToManuscript(orbEl, color) {
    if (!orbEl) return;
    const fr = orbEl.getBoundingClientRect();
    const tEl = $('manuscript-text');
    const tr = tEl.getBoundingClientRect();
    // 도착 위치: manuscript canvas 하단 (가장 마지막 단어 자리 가정)
    const x1 = fr.left + fr.width / 2;
    const y1 = fr.top + fr.height / 2;
    const x2 = tr.left + tr.width * 0.7;
    const y2 = tr.bottom - 40;

    const svg = $('energy-layer');
    const cx = (x1 + x2) / 2;
    const cy = Math.min(y1, y2) - 80; // 위로 곡선

    const c = color || '#00d4ff';
    const N = 6;
    const dur = 900;
    for (let i = 0; i < N; i++) {
      setTimeout(() => {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', '3.5');
        circle.setAttribute('class', 'energy-particle');
        circle.setAttribute('fill', c);
        circle.style.filter = `drop-shadow(0 0 8px ${c})`;
        svg.appendChild(circle);

        const t0 = performance.now();
        function step(now) {
          const t = Math.min(1, (now - t0) / dur);
          // quadratic Bezier (x1,y1)-(cx,cy)-(x2,y2)
          const u = 1 - t;
          const x = u*u*x1 + 2*u*t*cx + t*t*x2;
          const y = u*u*y1 + 2*u*t*cy + t*t*y2;
          circle.setAttribute('cx', x);
          circle.setAttribute('cy', y);
          circle.setAttribute('opacity', (1 - t * 0.4).toString());
          if (t < 1) requestAnimationFrame(step);
          else {
            // 도착 burst
            burstAt(x2, y2, c);
            svg.removeChild(circle);
          }
        }
        requestAnimationFrame(step);
      }, i * 80);
    }
  }

  function burstAt(x, y, color) {
    const svg = $('energy-layer');
    const burst = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    burst.setAttribute('cx', x);
    burst.setAttribute('cy', y);
    burst.setAttribute('r', '4');
    burst.setAttribute('fill', 'none');
    burst.setAttribute('stroke', color);
    burst.setAttribute('stroke-width', '2');
    burst.style.filter = `drop-shadow(0 0 12px ${color})`;
    svg.appendChild(burst);
    const t0 = performance.now();
    const dur = 500;
    function step(now) {
      const t = Math.min(1, (now - t0) / dur);
      burst.setAttribute('r', String(4 + t * 24));
      burst.setAttribute('opacity', String(1 - t));
      if (t < 1) requestAnimationFrame(step);
      else svg.removeChild(burst);
    }
    requestAnimationFrame(step);
  }

  // ── beats progress ─────────
  function updateBeats(state) {
    if (!state) return;
    const done = (state.beats_done || []).length;
    const pending = (state.beats_pending || []).length;
    const total = done + pending + (state.current_beat ? 1 : 0);
    if (total === 0) return;
    let s = '';
    for (let i = 0; i < done; i++) s += '●';
    for (let i = 0; i < (total - done); i++) s += '○';
    $('beats-progress').textContent = `beats: ${s} ${done}/${total}`;
  }

  // ── validator ───────────────
  function applyValidator(v) {
    $('v-citation').textContent = (v.citation_rate ?? '—');
    $('v-claims-invalid').textContent = (v.claims_invalid ?? '—');
    $('v-chars-invalid').textContent = (v.chars_invalid ?? '—');
    $('v-uncited-char').textContent = (v.uncited_char_paragraphs ?? '—');
    const passes = !!v.passes;
    const pe = $('v-passes');
    pe.textContent = passes ? '✓' : '○';
    pe.classList.toggle('passes', passes);
    const card = $('validator-card');
    const status = card.querySelector('.v-status');
    if (status) status.textContent = passes ? 'passes' : 'checking';
  }

  // ── log feed ────────────────
  function appendLog(entry) {
    const list = $('log-feed-list');
    const div = document.createElement('div');
    const agentClass = entry.agent === 'writer' ? 'agent-writer'
                     : entry.agent === 'validator' ? 'agent-validator' : '';
    div.className = `log-entry level-${entry.level || 'info'} ${agentClass}`;
    const time = (entry.ts || '').slice(11, 19);
    const payload = entry.payload ? JSON.stringify(entry.payload).slice(0, 80) : '';
    div.innerHTML = `<span class="l-time">${time}</span><span class="l-agent">${escapeHtml(entry.agent || '?')}</span><span class="l-event">${escapeHtml(entry.event || '')}</span><span class="l-payload">${escapeHtml(payload)}</span>`;
    list.prepend(div);
    while (list.children.length > 100) list.lastChild.remove();
  }

  // ── snapshot apply ──────────
  function applySnapshot(snap) {
    if (snap.outline?.topic) $('swarm-topic').textContent = snap.outline.topic;
    if (snap.meta?.status) $('swarm-phase').textContent = snap.meta.status;
    if (snap.manuscript) {
      const stripped = stripTags(snap.manuscript);
      lastManuscriptStripped = "";
      applyManuscript(stripped);
      $('manuscript-chars').textContent = `${snap.manuscript.length} chars`;
    }
    if (snap.outline_state) {
      $('manuscript-iter').textContent = `iter ${snap.outline_state.iteration || 0}`;
      $('manuscript-status').textContent = snap.outline_state.status || 'drafting';
      updateBeats(snap.outline_state);
    }
    if (snap.status?.validator) applyValidator(snap.status.validator);
    countTags(snap.manuscript || '');
    setRunning(!!snap.running);

    // 기존 claims가 있으면 모두 orb로 spawn (snapshot 복원)
    if (Array.isArray(snap.claims)) {
      snap.claims.forEach(c => spawnEnergyOrb(c));
    }
  }

  // ── SSE ─────────────────────
  function connectSSE() {
    if (evtSource) { evtSource.close(); evtSource = null; }
    const url = `/api/swarm/events?workspace=${encodeURIComponent(workspace)}`;
    evtSource = new EventSource(url);

    evtSource.addEventListener('snapshot', (e) => {
      const snap = JSON.parse(e.data);
      applySnapshot(snap);
    });

    evtSource.addEventListener('agent_event', (e) => {
      const ev = JSON.parse(e.data);
      appendLog(ev);
      const m = (ev.agent || '').match(/^R\d+$/);
      if (m) {
        if (ev.event === 'claimed_query') {
          setResearcherActive(ev.agent, true);
        } else if (ev.event === 'research_completed') {
          setResearcherActive(ev.agent, false);
        }
      }
      if (ev.agent === 'writer' && ev.event === 'step_completed') {
        const it = ev.payload?.iteration;
        if (it !== undefined) $('manuscript-iter').textContent = `iter ${it}`;
      }
      if (ev.agent === 'orchestrator' && ev.event === 'swarm_started') {
        $('swarm-phase').textContent = 'phase_1';
        startElapsed();
      }
      if (ev.event === 'swarm_completed' || ev.event === 'phase_2_timeout' || ev.event === 'writer_stalled') {
        stopElapsed();
        setRunning(false);
      }
    });

    evtSource.addEventListener('claim_added', (e) => {
      const c = JSON.parse(e.data);
      spawnEnergyOrb(c);
    });

    evtSource.addEventListener('manuscript_updated', (e) => {
      const m = JSON.parse(e.data);
      const stripped = stripTags(m.full_text);
      // 새로 등장한 claim id가 있으면 → 해당 orb에서 에너지 흐름 발사
      const newIds = extractClaimIds(m.full_text);
      newIds.forEach(id => {
        const orb = orbsById.get(id);
        if (orb && !orb.dataset.flowed) {
          orb.dataset.flowed = "1";
          const color = getComputedStyle(orb).getPropertyValue('--orb-color').trim() || '#00d4ff';
          flowEnergyToManuscript(orb, color);
        }
      });
      // 단어 단위 typing 적용
      applyManuscript(stripped);
      $('manuscript-chars').textContent = `${m.chars} chars`;
      countTags(m.full_text);
    });

    evtSource.addEventListener('writer_state', (e) => {
      const s = JSON.parse(e.data);
      $('manuscript-iter').textContent = `iter ${s.iteration || 0}`;
      $('manuscript-status').textContent = s.status || 'drafting';
      updateBeats(s);
    });

    evtSource.addEventListener('validator_status', (e) => {
      const s = JSON.parse(e.data);
      if (s.validator) applyValidator(s.validator);
    });

    evtSource.addEventListener('swarm_ended', () => {
      stopElapsed();
      setRunning(false);
    });

    evtSource.addEventListener('error', (e) => {
      console.error('SSE error', e);
    });
  }

  // ── start/stop swarm ────────
  $('btn-start-swarm').addEventListener('click', () => $('start-modal').style.display = 'flex');
  $('m-cancel').addEventListener('click', () => $('start-modal').style.display = 'none');

  $('m-confirm').addEventListener('click', async () => {
    const body = {
      topic: $('m-topic').value.trim(),
      duration: parseInt($('m-duration').value, 10) || 1,
      writing_style: $('m-style').value,
      n_researchers: parseInt($('m-researchers').value, 10) || 5,
    };
    if (workspace) body.workspace_dir = workspace;
    $('start-modal').style.display = 'none';
    try {
      const res = await fetch('/api/swarm/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.workspace) {
        workspace = data.workspace;
        page.dataset.workspace = workspace;
        const url = new URL(window.location);
        url.searchParams.set('workspace', workspace);
        history.replaceState(null, '', url);
      }
      setRunning(true);
      startElapsed();
      connectSSE();
    } catch (err) {
      alert('swarm 시작 실패: ' + err.message);
    }
  });

  $('btn-stop-swarm').addEventListener('click', async () => {
    if (!workspace) return;
    if (!confirm('swarm을 중지할까요?')) return;
    await fetch(`/api/swarm/stop?workspace=${encodeURIComponent(workspace)}`, { method: 'POST' });
    setRunning(false);
    stopElapsed();
  });

  // ── init ────────────────────
  async function autoDetectRunning() {
    try {
      const res = await fetch('/api/swarm/list');
      const data = await res.json();
      if (data.running && data.running.length > 0) {
        const r = data.running[0];
        workspace = r.workspace;
        page.dataset.workspace = workspace;
        const url = new URL(window.location);
        url.searchParams.set('workspace', workspace);
        history.replaceState(null, '', url);
        if (r.args?.topic) $('swarm-topic').textContent = r.args.topic;
        setRunning(true);
        if (r.started_at) {
          startTs = new Date(r.started_at).getTime();
          if (elapsedTimer) clearInterval(elapsedTimer);
          elapsedTimer = setInterval(() => {
            const sec = Math.floor((Date.now() - startTs) / 1000);
            $('swarm-elapsed').textContent = fmtElapsed(sec);
          }, 1000);
        }
        connectSSE();
        return true;
      }
    } catch (e) { console.error('autoDetect failed', e); }
    return false;
  }

  if (workspace) {
    connectSSE();
  } else {
    autoDetectRunning();
  }
})();
