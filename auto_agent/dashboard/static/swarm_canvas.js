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
  // v3: 인라인 문서 모드
  // q_id → 쿼리 라인 DOM, target_id → 섹션 DOM, claim_id → q_id
  const linesByQid = new Map();
  const sectionsByTid = new Map();
  const qidByClaimId = new Map();
  // 이미지 dedupe (target_id → { urls, fnames, captionTokenSets })
  // 3-단계: (1) URL 정확 일치 (2) 정규화 파일명 일치 (Wikimedia 썸네일/리사이즈 흡수)
  // (3) 캡션 토큰 Jaccard ≥ 0.55 (다른 언어/다른 해상도 흡수)
  const seenImagesByTid = new Map();
  function getSeen(tid) {
    let s = seenImagesByTid.get(tid);
    if (!s) {
      s = { urls: new Set(), fnames: new Set(), captionSets: [] };
      seenImagesByTid.set(tid, s);
    }
    return s;
  }
  function imageFingerprint(url) {
    try {
      const u = new URL(url);
      const parts = u.pathname.split('/').filter(Boolean);
      let last = parts[parts.length - 1] || '';
      // Wikimedia 썸네일: /thumb/.../base.jpg/NNNpx-base.jpg → "base.jpg"
      last = last.replace(/^\d+px-/, '');
      return decodeURIComponent(last).toLowerCase();
    } catch { return ''; }
  }
  function captionTokens(caption) {
    if (!caption) return new Set();
    const norm = caption.toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 2);
    return new Set(norm);
  }
  function jaccard(a, b) {
    if (a.size === 0 || b.size === 0) return 0;
    let inter = 0;
    for (const t of a) if (b.has(t)) inter++;
    return inter / (a.size + b.size - inter);
  }
  function isDuplicateImage(seen, url, caption) {
    if (seen.urls.has(url)) return true;
    const fp = imageFingerprint(url);
    if (fp && seen.fnames.has(fp)) return true;
    const tokens = captionTokens(caption);
    if (tokens.size >= 2) {
      for (const ct of seen.captionSets) {
        if (jaccard(tokens, ct) >= 0.4) return true;
      }
    }
    return false;
  }
  function rememberImage(seen, url, caption) {
    seen.urls.add(url);
    const fp = imageFingerprint(url);
    if (fp) seen.fnames.add(fp);
    const tokens = captionTokens(caption);
    if (tokens.size > 0) seen.captionSets.push(tokens);
  }

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

  // ── v3: 인라인 문서 모드 ───────
  // q_id 패턴: "t001_q03" → target_id "t001"
  function parseTid(qid) {
    if (!qid) return "?";
    const m = String(qid).match(/^(t\d+|[^_]+)_q\d+/);
    return m ? m[1] : qid;
  }

  function ensureSection(tid, targetText) {
    let section = sectionsByTid.get(tid);
    if (!section) {
      const doc = $('research-doc');
      if (!doc) return null;
      doc.classList.add('has-content');
      section = document.createElement('div');
      section.className = 'target-section';
      section.dataset.tid = tid;
      section.innerHTML = `<div class="target-header">${escapeHtml(targetText || tid)}</div>`;
      sectionsByTid.set(tid, section);
      doc.appendChild(section);
    }
    // target text hoist: 더 풍부한 헤더로 업그레이드 (tid가 fallback이었던 경우)
    if (targetText && targetText !== tid) {
      const header = section.querySelector('.target-header');
      if (header && (header.textContent === tid || !section.dataset.headerHoisted)) {
        header.textContent = targetText;
        section.dataset.headerHoisted = "1";
      }
    }
    return section;
  }

  function spawnQueryLine(qid, targetText, rid) {
    if (!qid) return null;
    if (linesByQid.has(qid)) return linesByQid.get(qid);
    const tid = parseTid(qid);
    const section = ensureSection(tid, targetText);
    if (!section) return null;
    const line = document.createElement('div');
    line.className = 'qline active';
    line.dataset.qid = qid;
    line.innerHTML = `
      <span class="qline-bullet"></span>
      <span class="qline-text"><span class="placeholder">${escapeHtml(rid || '·')} researching...</span></span>
    `;
    section.appendChild(line);
    linesByQid.set(qid, line);
    return line;
  }

  function moveCursorToLine(rid, line) {
    const cursor = document.querySelector(`.researcher-cursor[data-rid="${rid}"]`);
    if (!cursor || !line) return;
    cursor.classList.remove('idle');
    cursor.classList.add('active');
    const canvas = document.getElementById('research-canvas');
    if (!canvas) return;
    const cRect = canvas.getBoundingClientRect();
    const lineRect = line.getBoundingClientRect();
    // canvas 좌표계 (cursor는 canvas의 직접 자식)
    const x = (lineRect.left - cRect.left) + 4;
    const y = (lineRect.top - cRect.top) + (lineRect.height / 2) - 11;
    cursor.style.right = 'auto';
    cursor.style.left = `${x}px`;
    cursor.style.top = `${y}px`;
  }

  function setCursorIdle(rid) {
    const cursor = document.querySelector(`.researcher-cursor[data-rid="${rid}"]`);
    if (!cursor) return;
    cursor.classList.remove('active');
    cursor.classList.add('idle');
    // dock 위치는 CSS .idle[data-rid] 규칙이 처리, 인라인 스타일 제거
    cursor.style.left = '';
    cursor.style.top = '';
    cursor.style.right = '';
  }

  function fillLineWithFact(line, factText, rid) {
    if (!line) return;
    const textEl = line.querySelector('.qline-text');
    if (!textEl) return;
    textEl.innerHTML = '';
    const trimmed = (factText || '').trim().slice(0, 200);
    const words = splitWords(trimmed);
    words.forEach((w, i) => {
      const span = document.createElement('span');
      span.className = 'word';
      span.textContent = w;
      span.style.animationDelay = `${Math.min(i * 0.03, 0.9)}s`;
      textEl.appendChild(span);
    });
    if (rid) {
      const ridEl = document.createElement('span');
      ridEl.className = 'qline-rid';
      ridEl.textContent = rid;
      textEl.appendChild(ridEl);
    }
    line.classList.remove('active');
    line.classList.add('completed');
  }

  function ensureMarkers(line) {
    let m = line.querySelector('.qline-markers');
    if (!m) {
      m = document.createElement('span');
      m.className = 'qline-markers';
      line.appendChild(m);
    }
    return m;
  }

  function applyClaimToLine(claim) {
    const rid = claim.researcher || "R1";
    researcherClaimCount[rid] = (researcherClaimCount[rid] || 0) + 1;
    if (claim.cross_checked) crossCount += 1;
    const imgs = Array.isArray(claim.image_candidates) ? claim.image_candidates.length : 0;
    if (imgs) imageCount += imgs;
    updateResearchStats();

    const qid = claim.q_id || claim.query_id || claim.id;
    if (!qid) return;
    let line = linesByQid.get(qid);
    if (!line) line = spawnQueryLine(qid, claim.target || qid, rid);
    if (!line) return;

    if (claim.id) qidByClaimId.set(claim.id, qid);

    // 첫 claim의 text로 라인 채움
    if (!line.dataset.filled && claim.text) {
      line.dataset.filled = "1";
      fillLineWithFact(line, claim.text, rid);
    }
    // 인라인 마커 (cross_checked만 텍스트, 이미지는 실제 inline render)
    const markers = ensureMarkers(line);
    let crossN = parseInt(line.dataset.crossN || '0', 10);
    if (claim.cross_checked) crossN += 1;
    line.dataset.crossN = String(crossN);
    let inner = '';
    if (crossN > 0) inner += `<span class="m-cross">✓✓${crossN > 1 ? '×' + crossN : ''}</span>`;
    markers.innerHTML = inner;

    // 인라인 이미지 — 이제 target(섹션) 단위로 통합 갤러리에 렌더
    // dedupe: target 단위 3-단계 (URL/파일명/캡션 Jaccard)
    if (Array.isArray(claim.image_candidates) && claim.image_candidates.length > 0) {
      const tid = parseTid(qid);
      const seen = getSeen(tid);
      const section = sectionsByTid.get(tid);
      if (!section) return;
      let strip = section.querySelector('.target-images');
      if (!strip) {
        strip = document.createElement('div');
        strip.className = 'target-images';
        // 헤더 바로 아래에 삽입
        const header = section.querySelector('.target-header');
        if (header && header.nextSibling) section.insertBefore(strip, header.nextSibling);
        else section.appendChild(strip);
      }
      claim.image_candidates.forEach(img => {
        if (!img || !img.url) return;
        if (isDuplicateImage(seen, img.url, img.caption)) return;
        rememberImage(seen, img.url, img.caption);
        const wrap = document.createElement('a');
        wrap.className = 'qline-img';
        wrap.dataset.imgUrl = img.url;
        wrap.href = img.source || img.url;
        wrap.target = '_blank';
        wrap.rel = 'noopener noreferrer';
        wrap.title = (img.caption || '') + (img.license ? ' — ' + img.license : '');
        const im = document.createElement('img');
        im.src = img.url;
        im.alt = img.caption || '';
        im.loading = 'lazy';
        im.referrerPolicy = 'no-referrer';
        // 깨진 이미지는 wrap 자체를 숨김 + dedupe set에서 빼지 않음 (재시도 방지)
        im.addEventListener('error', () => { wrap.style.display = 'none'; }, { once: true });
        wrap.appendChild(im);
        if (img.caption) {
          const cap = document.createElement('span');
          cap.className = 'qline-img-cap';
          cap.textContent = img.caption.slice(0, 60);
          wrap.appendChild(cap);
        }
        strip.appendChild(wrap);
      });
    }
  }

  function setResearcherActive(rid, active, qid, target) {
    if (active) {
      let line = qid ? linesByQid.get(qid) : null;
      if (!line && qid) line = spawnQueryLine(qid, target || qid, rid);
      if (line) moveCursorToLine(rid, line);
    } else {
      setCursorIdle(rid);
    }
  }

  function updateResearchStats() {
    const total = Object.values(researcherClaimCount).reduce((a, b) => a + b, 0);
    $('research-claim-total').textContent = `claims: ${total}`;
    $('research-cross').textContent = `cross: ${crossCount}`;
    $('research-images').textContent = `images: ${imageCount}`;
  }

  // ── energy particle flow (card → manuscript) ─────
  // SVG 곡선을 따라 작은 원 입자를 0.1s 간격으로 보내고, 도착 시 원고 위치에서 burst
  function flowEnergyToManuscript(srcEl, color) {
    if (!srcEl) return;
    srcEl.classList.add('cited');
    const fr = srcEl.getBoundingClientRect();
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

    // manuscript 우선, 없으면 draft fallback
    const manuscriptContent = snap.manuscript || snap.draft || '';
    const isDraft = !snap.manuscript && !!snap.draft;
    if (manuscriptContent) {
      const stripped = stripTags(manuscriptContent);
      lastManuscriptStripped = "";
      applyManuscript(stripped);
      const label = isDraft ? '(초고)' : '';
      $('manuscript-chars').textContent = `${manuscriptContent.length} chars ${label}`.trim();
      if (isDraft) $('manuscript-status').textContent = 'draft';
    }

    if (snap.outline_state) {
      $('manuscript-iter').textContent = `iter ${snap.outline_state.iteration || 0}`;
      if (!isDraft) $('manuscript-status').textContent = snap.outline_state.status || 'drafting';
      updateBeats(snap.outline_state);
    }
    if (snap.status?.validator) applyValidator(snap.status.validator);
    countTags(manuscriptContent);
    setRunning(!!snap.running);

    // 기존 claims 복원 — 리서치 캔버스 섹션/라인 재구성
    if (Array.isArray(snap.claims) && snap.claims.length > 0) {
      snap.claims.forEach(c => applyClaimToLine(c));
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
      // R1..R5 또는 E_R1..E_R5 (Phase 4 targeted researchers) 모두 처리
      // E_R1 → 커서 슬롯 R1 재사용
      const agentId = ev.agent || '';
      const rMatch = agentId.match(/^(?:E_)?(R\d+)$/);
      if (rMatch) {
        const cursorSlot = rMatch[1]; // E_R1 → "R1", R2 → "R2"
        if (ev.event === 'claimed_query') {
          const p = ev.payload || {};
          const qid = p.q_id || p.query_id || p.qid;
          const target = p.target || p.query || qid;
          setResearcherActive(cursorSlot, true, qid, target);
        } else if (ev.event === 'research_completed') {
          setResearcherActive(cursorSlot, false);
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
      applyClaimToLine(c);
    });

    evtSource.addEventListener('manuscript_updated', (e) => {
      const m = JSON.parse(e.data);
      const stripped = stripTags(m.full_text);
      // 새로 등장한 claim id가 있으면 → 해당 라인에서 에너지 흐름 발사
      const newIds = extractClaimIds(m.full_text);
      newIds.forEach(id => {
        const qid = qidByClaimId.get(id);
        if (!qid) return;
        const line = linesByQid.get(qid);
        if (line && !line.dataset.flowed) {
          line.dataset.flowed = "1";
          const ridEl = line.querySelector('.qline-rid');
          const rid = ridEl ? ridEl.textContent.trim() : 'R1';
          const cursor = document.querySelector(`.researcher-cursor[data-rid="${rid}"]`);
          const color = cursor ? getComputedStyle(cursor).getPropertyValue('--cursor-color').trim() : '#00d4ff';
          flowEnergyToManuscript(line, color || '#00d4ff');
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
