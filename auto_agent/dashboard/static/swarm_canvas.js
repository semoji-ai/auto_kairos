// Swarm Canvas — 실시간 스트리밍 + 종이비행기 motion
(() => {
  const page = document.querySelector('.swarm-canvas-page');
  if (!page) return;

  let workspace = page.dataset.workspace || "";
  let evtSource = null;
  let startTs = null;
  let elapsedTimer = null;

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

  // ── snapshot apply ──────────
  function applySnapshot(snap) {
    if (snap.outline?.topic) $('swarm-topic').textContent = snap.outline.topic;
    if (snap.meta?.status) $('swarm-phase').textContent = snap.meta.status;
    if (snap.manuscript) {
      $('manuscript-text').textContent = stripTags(snap.manuscript);
      $('manuscript-chars').textContent = `${snap.manuscript.length} chars`;
    }
    if (snap.outline_state) {
      $('manuscript-iter').textContent = `iter ${snap.outline_state.iteration || 0}`;
      $('manuscript-status').textContent = snap.outline_state.status || 'drafting';
    }
    // researcher cards
    (snap.researchers || []).forEach(r => updateResearcher(r.id, { claims: r.claims, last_q: r.last_q }));
    // validator
    if (snap.status?.validator) applyValidator(snap.status.validator);
    // tag counts
    countTags(snap.manuscript || '');
    setRunning(!!snap.running);
  }

  function stripTags(text) {
    return text
      .replace(/\[claim:[^\]]+\]/g, '')
      .replace(/\[char:[^\]]+\]/g, '')
      .replace(/\[TODO:[^\]]+\]/g, '')
      .replace(/  +/g, ' ');
  }

  function countTags(text) {
    const claims = (text.match(/\[claim:[^\]]+\]/g) || []).length;
    const chars = (text.match(/\[char:[^\]]+\]/g) || []).length;
    $('claim-tags').textContent = `claim tags: ${claims}`;
    $('char-tags').textContent = `char tags: ${chars}`;
  }

  // ── researcher card ─────────
  function updateResearcher(rid, patch) {
    const card = document.querySelector(`.researcher-card[data-rid="${rid}"]`);
    if (!card) return;
    if (patch.status) card.querySelector('.r-status').textContent = patch.status;
    if (patch.claims !== undefined) card.querySelector('.r-claims').textContent = `${patch.claims} claims`;
    if (patch.last_q !== undefined) card.querySelector('.r-last-q').textContent = patch.last_q || '';
    if (patch.active !== undefined) card.classList.toggle('active', !!patch.active);
  }
  function bumpResearcherClaims(rid) {
    const el = document.querySelector(`.researcher-card[data-rid="${rid}"] .r-claims`);
    if (!el) return;
    const cur = parseInt(el.textContent, 10) || 0;
    el.textContent = `${cur + 1} claims`;
  }

  // ── validator ───────────────
  function applyValidator(v) {
    $('v-citation').textContent = (v.citation_rate ?? '—');
    $('v-claims-invalid').textContent = (v.claims_invalid ?? '—');
    $('v-chars-invalid').textContent = (v.chars_invalid ?? '—');
    $('v-uncited-char').textContent = (v.uncited_char_paragraphs ?? '—');
    const passes = !!v.passes;
    const card = $('validator-card');
    const pe = $('v-passes');
    pe.textContent = passes ? '✓' : '○';
    pe.classList.toggle('passes', passes);
    card.querySelector('.v-status').textContent = passes ? 'passes' : 'checking';
  }

  // ── log feed ────────────────
  function appendLog(entry) {
    const list = $('log-feed-list');
    const div = document.createElement('div');
    div.className = `log-entry level-${entry.level || 'info'}`;
    const time = (entry.ts || '').slice(11, 19);
    const payload = entry.payload ? JSON.stringify(entry.payload).slice(0, 80) : '';
    div.innerHTML = `<span class="l-time">${time}</span><span class="l-agent">${escapeHtml(entry.agent || '?')}</span><span class="l-event">${escapeHtml(entry.event || '')}</span><span class="l-payload">${escapeHtml(payload)}</span>`;
    list.prepend(div);
    while (list.children.length > 100) list.lastChild.remove();
  }

  // ── paper plane animation ──
  function flyPaperPlane(fromEl, toEl, color) {
    if (!fromEl || !toEl) return;
    const fr = fromEl.getBoundingClientRect();
    const tr = toEl.getBoundingClientRect();
    const x1 = fr.left + fr.width / 2;
    const y1 = fr.top + fr.height / 2;
    const x2 = tr.left + tr.width / 2;
    const y2 = tr.top + tr.height / 2;
    const svg = $('plane-layer');
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M 0 0 L 18 -6 L 12 0 L 18 6 Z');
    path.setAttribute('class', 'plane');
    if (color) path.setAttribute('fill', color);
    g.appendChild(path);
    g.setAttribute('transform', `translate(${x1},${y1})`);
    svg.appendChild(g);
    const dur = 700;
    const t0 = performance.now();
    function step(now) {
      const t = Math.min(1, (now - t0) / dur);
      // ease-out
      const e = 1 - Math.pow(1 - t, 3);
      const x = x1 + (x2 - x1) * e;
      const y = y1 + (y2 - y1) * e;
      const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
      g.setAttribute('transform', `translate(${x},${y}) rotate(${angle})`);
      g.style.opacity = (1 - t * 0.3).toString();
      if (t < 1) requestAnimationFrame(step);
      else {
        // 도착 후 페이드 아웃
        g.style.transition = 'opacity 0.3s';
        g.style.opacity = '0';
        setTimeout(() => svg.removeChild(g), 300);
        // canvas highlight
        const text = $('manuscript-text');
        text.style.background = '#FCD34D33';
        setTimeout(() => { text.style.background = ''; }, 600);
      }
    }
    requestAnimationFrame(step);
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
      // researcher activity 표시
      const m = (ev.agent || '').match(/^R\d+$/);
      if (m) {
        if (ev.event === 'claimed_query') {
          updateResearcher(ev.agent, { status: 'searching', last_q: ev.payload?.target || '', active: true });
        } else if (ev.event === 'research_completed') {
          updateResearcher(ev.agent, { status: 'idle', active: false });
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
      bumpResearcherClaims(c.researcher);
      // 종이비행기 — researcher card → manuscript canvas
      const fromCard = document.querySelector(`.researcher-card[data-rid="${c.researcher}"]`);
      const toCanvas = document.querySelector('.manuscript-canvas');
      flyPaperPlane(fromCard, toCanvas);
    });

    evtSource.addEventListener('manuscript_updated', (e) => {
      const m = JSON.parse(e.data);
      const stripped = stripTags(m.full_text);
      $('manuscript-text').textContent = stripped;
      $('manuscript-chars').textContent = `${m.chars} chars`;
      countTags(m.full_text);
    });

    evtSource.addEventListener('writer_state', (e) => {
      const s = JSON.parse(e.data);
      $('manuscript-iter').textContent = `iter ${s.iteration || 0}`;
      $('manuscript-status').textContent = s.status || 'drafting';
    });

    evtSource.addEventListener('validator_status', (e) => {
      const s = JSON.parse(e.data);
      if (s.validator) applyValidator(s.validator);
    });

    evtSource.addEventListener('register_updated', (e) => {
      // (선택) 캐릭터 카드 표시. 일단 로그에만.
      const r = JSON.parse(e.data);
      appendLog({ agent: 'register', event: 'updated', payload: { count: (r.characters || []).length } });
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
        // URL에 workspace 반영
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
        // 가장 최근 running swarm 자동 연결
        const r = data.running[0];
        workspace = r.workspace;
        page.dataset.workspace = workspace;
        const url = new URL(window.location);
        url.searchParams.set('workspace', workspace);
        history.replaceState(null, '', url);
        if (r.args?.topic) $('swarm-topic').textContent = r.args.topic;
        setRunning(true);
        // started_at 기준 elapsed 시작
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
    // workspace 파라미터 없으면 running swarm 자동 감지
    autoDetectRunning();
  }
})();
