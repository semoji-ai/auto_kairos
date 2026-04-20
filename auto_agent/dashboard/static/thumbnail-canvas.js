/**
 * Thumbnail Canvas — 레이어 기반 YouTube 썸네일 편집기
 * Canvas size: 1280×720 (display: 900×506)
 */

// ── 상수 ──────────────────────────────────────────────────────────────────
const TC_W = 1280, TC_H = 720;
const TC_DISPLAY_W = 900;
const TC_SCALE = TC_DISPLAY_W / TC_W;  // 0.703125

// ── 전역 상태 ──────────────────────────────────────────────────────────────
let tcSlug = '';
let tcLayers = [];
let tcSelectedId = null;
let tcDragState = null;
// { type: 'layer'|'gradient_dir', layerId, startX, startY, origX, origY,
//   curX?, curY? }
let tcCanvas = null;
let tcCtx = null;
let tcImageCache = {};
let tcSpecs = [];
let tcProjectFonts = [];  // [{ role, family, files }]

// ── 초기화 ────────────────────────────────────────────────────────────────
function tcInit(slug) {
  tcSlug = slug;
  tcCanvas = document.getElementById('tc-canvas');
  if (!tcCanvas) return;
  tcCtx = tcCanvas.getContext('2d');
  tcLayers = [];
  tcSelectedId = null;
  tcDragState = null;

  const specEl = document.getElementById('tc-specs-data');
  try { tcSpecs = specEl ? JSON.parse(specEl.textContent) : []; } catch(e) { tcSpecs = []; }

  const fontEl = document.getElementById('tc-fonts-data');
  if (fontEl) {
    try { tcProjectFonts = JSON.parse(fontEl.textContent) || []; } catch(e) {}
    tcLoadProjectFonts(tcProjectFonts);
  }

  // 저장된 캔버스 상태 복원 → 없으면 spec A 자동 로드 → 그것도 없으면 빈 캔버스
  const stateEl = document.getElementById('tc-canvas-state');
  let savedState = null;
  try { savedState = stateEl ? JSON.parse(stateEl.textContent) : null; } catch(e) {}

  if (savedState && savedState.layers && savedState.layers.length > 0) {
    tcRestoreState(savedState);
  } else if (tcSpecs.length > 0) {
    tcLoadSpec(0);
  } else {
    tcRender();
    tcRenderLayerPanel();
    tcRenderProps();
  }
}

// ── 프로젝트 폰트 로드 ────────────────────────────────────────────────────
function tcLoadProjectFonts(fonts) {
  if (!fonts || !fonts.length) return;
  let css = '';
  for (const f of fonts) {
    for (const file of (f.files || [])) {
      const ext = file.file.split('.').pop().toLowerCase();
      const fmt = ext === 'woff2' ? 'woff2' : ext === 'woff' ? 'woff' : ext === 'otf' ? 'opentype' : 'truetype';
      css += `@font-face { font-family: '${f.family}'; src: url('/fonts/${file.file.split('/').pop()}') format('${fmt}'); font-weight: ${file.weight || '400'}; font-style: normal; }\n`;
    }
  }
  if (css) {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }
}

function tcFontLabel(role) {
  const map = { body: '본문', headline: '헤드라인', value: '숫자/강조', mono: '모노', subtitle: '자막' };
  return map[role] || role;
}

// ── 레이어 생성 헬퍼 ──────────────────────────────────────────────────────
function tcMakeId() { return 'L' + Math.random().toString(36).slice(2, 8); }

function tcAddImageLayer(url, filename) {
  const layer = {
    id: tcMakeId(), type: 'image', visible: true, locked: false,
    blendMode: 'normal', opacity: 100,
    src: url, filename: filename || url.split('/').pop(),
    x: 0, y: 0, width: TC_W, height: TC_H,
    brightness: 0, contrast: 0,
  };
  tcLayers.unshift(layer);
  tcSelectedId = layer.id;
  tcLoadImage(url, () => { tcRender(); tcRenderLayerPanel(); tcRenderProps(); });
}

function tcAddGradientLayer() {
  const layer = {
    id: tcMakeId(), type: 'gradient', visible: true, locked: false,
    blendMode: 'normal', opacity: 85,
    gradientType: 'linear',
    // 시작점→끝점 (캔버스 좌표). 기본: 위→아래
    x0: TC_W / 2, y0: 0, x1: TC_W / 2, y1: TC_H,
    stops: [
      { offset: 0, color: 'rgba(0,0,0,0)' },
      { offset: 0.5, color: 'rgba(0,0,0,0.4)' },
      { offset: 1, color: 'rgba(0,0,0,0.85)' },
    ],
  };
  tcLayers.unshift(layer);
  tcSelectedId = layer.id;
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

function tcAddVignetteLayer() {
  const layer = {
    id: tcMakeId(), type: 'vignette', visible: true, locked: false,
    blendMode: 'multiply', opacity: 80,
    intensity: 70, spread: 50,
  };
  tcLayers.unshift(layer);
  tcSelectedId = layer.id;
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

function tcAddTextLayer(text) {
  // 기본 폰트: 아트스타일 headline > body > fallback
  const headlineFont = tcProjectFonts.find(f => f.role === 'headline');
  const bodyFont = tcProjectFonts.find(f => f.role === 'body');
  const defaultFont = headlineFont || bodyFont;
  const fontFamily = defaultFont
    ? `'${defaultFont.family}', sans-serif`
    : 'Pretendard, Apple SD Gothic Neo, sans-serif';

  const layer = {
    id: tcMakeId(), type: 'text', visible: true, locked: false,
    blendMode: 'normal', opacity: 100,
    text: text || '텍스트를 입력하세요',
    x: TC_W / 2, y: TC_H - 150,
    fontFamily: fontFamily,
    fontRole: defaultFont ? defaultFont.role : '',
    fontSize: 96, fontWeight: '700',
    color: '#FFFFFF',
    align: 'center',
    shadowColor: 'rgba(0,0,0,0.9)',
    shadowBlur: 16, shadowOffsetX: 2, shadowOffsetY: 4,
    strokeColor: '', strokeWidth: 0,
  };
  tcLayers.unshift(layer);
  tcSelectedId = layer.id;
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

// ── 이미지 캐시 ───────────────────────────────────────────────────────────
function tcLoadImage(url, cb) {
  if (tcImageCache[url]) { if (cb) cb(tcImageCache[url]); return; }
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => { tcImageCache[url] = img; if (cb) cb(img); };
  img.onerror = () => { console.warn('이미지 로드 실패:', url); if (cb) cb(null); };
  img.src = url;
}

// ── 렌더링 ────────────────────────────────────────────────────────────────
function tcRender() {
  if (!tcCtx) return;
  const ctx = tcCtx;
  ctx.clearRect(0, 0, TC_W, TC_H);
  tcDrawCheckerboard(ctx);

  const ordered = [...tcLayers].reverse();
  for (const layer of ordered) {
    if (!layer.visible) continue;
    ctx.save();
    ctx.globalAlpha = layer.opacity / 100;
    ctx.globalCompositeOperation = layer.blendMode || 'source-over';
    if (layer.type === 'image') tcRenderImageLayer(ctx, layer);
    else if (layer.type === 'gradient') tcRenderGradientLayer(ctx, layer);
    else if (layer.type === 'vignette') tcRenderVignetteLayer(ctx, layer);
    else if (layer.type === 'text') tcRenderTextLayer(ctx, layer);
    ctx.restore();
  }

  if (tcSelectedId) {
    const sel = tcLayers.find(l => l.id === tcSelectedId);
    if (sel) tcDrawSelectionHandle(ctx, sel);
  }

  // 그라데이션 드래그 방향선 오버레이
  if (tcDragState && tcDragState.type === 'gradient_dir') {
    tcDrawGradientDirectionLine(ctx, tcDragState);
  }
}

function tcDrawCheckerboard(ctx) {
  const size = 20;
  for (let y = 0; y < TC_H; y += size) {
    for (let x = 0; x < TC_W; x += size) {
      ctx.fillStyle = ((x / size + y / size) % 2 === 0) ? '#1a1a1a' : '#222';
      ctx.fillRect(x, y, size, size);
    }
  }
}

function tcRenderImageLayer(ctx, layer) {
  const img = tcImageCache[layer.src];
  if (!img) { tcLoadImage(layer.src, () => tcRender()); return; }
  const b = layer.brightness || 0;
  const c = layer.contrast || 0;
  if (b !== 0 || c !== 0) {
    ctx.filter = `brightness(${100 + b}%) contrast(${100 + c}%)`;
  }
  ctx.drawImage(img, layer.x, layer.y, layer.width, layer.height);
  ctx.filter = 'none';
}

function tcRenderGradientLayer(ctx, layer) {
  let grad;
  if (layer.gradientType === 'linear') {
    grad = ctx.createLinearGradient(layer.x0, layer.y0, layer.x1, layer.y1);
  } else {
    grad = ctx.createRadialGradient(TC_W/2, TC_H/2, 0, TC_W/2, TC_H/2, Math.max(TC_W, TC_H)/2);
  }
  for (const stop of layer.stops) {
    try { grad.addColorStop(stop.offset, stop.color); } catch(e) {}
  }
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, TC_W, TC_H);
}

function tcRenderVignetteLayer(ctx, layer) {
  const intensity = (layer.intensity || 70) / 100;
  const spread = 1 - (layer.spread || 50) / 100;
  const grad = ctx.createRadialGradient(
    TC_W/2, TC_H/2, Math.min(TC_W, TC_H) * spread * 0.5,
    TC_W/2, TC_H/2, Math.max(TC_W, TC_H) * 0.75
  );
  grad.addColorStop(0, 'rgba(0,0,0,0)');
  grad.addColorStop(1, `rgba(0,0,0,${intensity})`);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, TC_W, TC_H);
}

function tcRenderTextLayer(ctx, layer) {
  ctx.font = `${layer.fontWeight || '700'} ${layer.fontSize}px ${layer.fontFamily}`;
  ctx.textAlign = layer.align || 'center';
  ctx.textBaseline = 'middle';
  if (layer.shadowBlur || layer.shadowOffsetX || layer.shadowOffsetY) {
    ctx.shadowColor = layer.shadowColor || 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = layer.shadowBlur || 0;
    ctx.shadowOffsetX = layer.shadowOffsetX || 0;
    ctx.shadowOffsetY = layer.shadowOffsetY || 0;
  }
  if (layer.strokeWidth > 0 && layer.strokeColor) {
    ctx.strokeStyle = layer.strokeColor;
    ctx.lineWidth = layer.strokeWidth;
    ctx.lineJoin = 'round';
    ctx.shadowColor = 'transparent';
    ctx.strokeText(layer.text, layer.x, layer.y);
    ctx.shadowColor = layer.shadowColor || 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = layer.shadowBlur || 0;
    ctx.shadowOffsetX = layer.shadowOffsetX || 0;
    ctx.shadowOffsetY = layer.shadowOffsetY || 0;
  }
  ctx.fillStyle = layer.color || '#FFFFFF';
  ctx.fillText(layer.text, layer.x, layer.y);
  ctx.shadowColor = 'transparent';
  ctx.shadowBlur = 0; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0;
}

function tcDrawSelectionHandle(ctx, layer) {
  ctx.save();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
  ctx.strokeStyle = '#F7D94C';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 3]);
  if (layer.type === 'image') {
    ctx.strokeRect(layer.x + 1, layer.y + 1, layer.width - 2, layer.height - 2);
  } else if (layer.type === 'text') {
    tcCtx.font = `${layer.fontWeight || '700'} ${layer.fontSize}px ${layer.fontFamily}`;
    const w = tcCtx.measureText(layer.text).width;
    const h = layer.fontSize * 1.4;
    const tx = layer.align === 'center' ? layer.x - w/2 : layer.x;
    ctx.strokeRect(tx - 8, layer.y - h/2 - 4, w + 16, h + 8);
  } else if (layer.type === 'gradient') {
    // 그라데이션 레이어: 방향선 표시 + 힌트
    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(247,217,76,0.4)';
    ctx.strokeRect(1, 1, TC_W - 2, TC_H - 2);
    // 방향선
    tcDrawGradientDirectionLine(ctx, { x0: layer.x0, y0: layer.y0, x1: layer.x1, y1: layer.y1 });
  } else {
    ctx.strokeRect(1, 1, TC_W - 2, TC_H - 2);
  }
  ctx.restore();
}

// 그라데이션 방향선 (캔버스 오버레이)
function tcDrawGradientDirectionLine(ctx, state) {
  const x0 = state.x0 !== undefined ? state.x0 : state.startX;
  const y0 = state.y0 !== undefined ? state.y0 : state.startY;
  const x1 = state.x1 !== undefined ? state.x1 : (state.curX || state.startX);
  const y1 = state.y1 !== undefined ? state.y1 : (state.curY || state.startY);

  ctx.save();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
  ctx.setLineDash([]);

  // 선
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.strokeStyle = '#F7D94C';
  ctx.lineWidth = 2;
  ctx.stroke();

  // 시작점 원
  ctx.beginPath();
  ctx.arc(x0, y0, 8, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.strokeStyle = '#F7D94C';
  ctx.lineWidth = 2;
  ctx.fill(); ctx.stroke();

  // 끝점 화살표
  const angle = Math.atan2(y1 - y0, x1 - x0);
  const aw = 14;
  ctx.beginPath();
  ctx.arc(x1, y1, 8, 0, Math.PI * 2);
  ctx.fillStyle = '#F7D94C';
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x1 - aw * Math.cos(angle - 0.4), y1 - aw * Math.sin(angle - 0.4));
  ctx.lineTo(x1 - aw * Math.cos(angle + 0.4), y1 - aw * Math.sin(angle + 0.4));
  ctx.closePath();
  ctx.fillStyle = '#fff';
  ctx.fill();

  ctx.restore();
}

// ── 레이어 패널 ──────────────────────────────────────────────────────────
function tcRenderLayerPanel() {
  const el = document.getElementById('tc-layer-list');
  if (!el) return;
  const typeIcon = { image: '🖼', gradient: '🌈', vignette: '🔘', text: '✏️' };
  el.innerHTML = tcLayers.map((l, i) => `
    <div class="tc-layer-item${l.id === tcSelectedId ? ' selected' : ''}"
      onclick="tcSelectLayer('${l.id}')"
      draggable="true"
      ondragstart="tcLayerDragStart(event, ${i})"
      ondragover="tcLayerDragOver(event, ${i})"
      ondrop="tcLayerDrop(event, ${i})"
    >
      <span class="tc-layer-vis" onclick="tcToggleVisibility('${l.id}');event.stopPropagation();">${l.visible ? '👁' : '🚫'}</span>
      <span style="font-size:14px; flex-shrink:0;">${typeIcon[l.type] || '◻'}</span>
      <span class="tc-layer-name">${l.type === 'text' ? (l.text.slice(0, 14) + (l.text.length > 14 ? '…' : '')) : (l.filename || l.type)}</span>
      <span class="tc-layer-del" onclick="tcDeleteLayer('${l.id}');event.stopPropagation();">✕</span>
    </div>
  `).join('');
}

function tcSelectLayer(id) {
  tcSelectedId = id;
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

function tcToggleVisibility(id) {
  const l = tcLayers.find(x => x.id === id);
  if (l) { l.visible = !l.visible; tcRender(); tcRenderLayerPanel(); }
}

function tcDeleteLayer(id) {
  tcLayers = tcLayers.filter(x => x.id !== id);
  if (tcSelectedId === id) tcSelectedId = tcLayers[0]?.id || null;
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

let _tcDragLayerIdx = -1;
function tcLayerDragStart(e, idx) { _tcDragLayerIdx = idx; e.dataTransfer.effectAllowed = 'move'; }
function tcLayerDragOver(e, idx) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
function tcLayerDrop(e, targetIdx) {
  e.preventDefault();
  if (_tcDragLayerIdx < 0 || _tcDragLayerIdx === targetIdx) return;
  const moved = tcLayers.splice(_tcDragLayerIdx, 1)[0];
  tcLayers.splice(targetIdx, 0, moved);
  _tcDragLayerIdx = -1;
  tcRender(); tcRenderLayerPanel();
}

// ── 속성 패널 ────────────────────────────────────────────────────────────
function tcRenderProps() {
  const el = document.getElementById('tc-props-panel');
  if (!el) return;
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer) { el.innerHTML = '<div style="color:#555; font-size:12px;">레이어를 선택하세요</div>'; return; }

  const common = `
    <div class="tc-section-title">공통</div>
    ${tcPropRange('불투명도', 'opacity', layer.opacity, 0, 100, 1)}
    ${tcPropSelect('블렌드', 'blendMode', layer.blendMode, ['normal','multiply','screen','overlay','darken','lighten','color-dodge','color-burn','hard-light','soft-light'])}
  `;

  let specific = '';

  if (layer.type === 'image') {
    specific = `
      <div class="tc-section-title">이미지</div>
      ${tcPropRange('밝기', 'brightness', layer.brightness, -100, 100, 1)}
      ${tcPropRange('대비', 'contrast', layer.contrast, -100, 100, 1)}
      <div class="tc-section-title">위치/크기</div>
      ${tcPropNumber('X', 'x', layer.x)}
      ${tcPropNumber('Y', 'y', layer.y)}
      ${tcPropNumber('너비', 'width', layer.width)}
      ${tcPropNumber('높이', 'height', layer.height)}
    `;
  } else if (layer.type === 'gradient') {
    const hint = layer.gradientType === 'linear'
      ? '<div style="font-size:11px;color:#888;margin-bottom:8px;line-height:1.5;">💡 캔버스에서 드래그해서<br>그라데이션 방향을 설정하세요</div>'
      : '';
    specific = `
      <div class="tc-section-title">그라데이션</div>
      ${hint}
      ${tcPropSelect('종류', 'gradientType', layer.gradientType, ['linear','radial'])}
      <div class="tc-section-title">색상 스톱</div>
      ${layer.stops.map((s, i) => `
        <div class="tc-gradient-stop">
          <input type="color" value="${tcRgbaToHex(s.color)}" style="width:28px;height:22px;border:none;padding:0;background:none;cursor:pointer;" onchange="tcGradientStopColor(${i}, this.value)">
          <input type="range" min="0" max="1" step="0.05" value="${s.offset}" class="tc-prop-range" style="flex:1;" oninput="tcGradientStopOffset(${i}, parseFloat(this.value))">
          <span style="font-size:10px;color:#666;min-width:24px;text-align:right;">${Math.round(s.offset * 100)}%</span>
          <input type="range" min="0" max="1" step="0.05" value="${tcGetAlpha(s.color)}" class="tc-prop-range" style="flex:0.6;" title="투명도" oninput="tcGradientStopAlpha(${i}, parseFloat(this.value))">
          <span style="font-size:10px;color:#666;min-width:24px;text-align:right;">${Math.round(tcGetAlpha(s.color) * 100)}%</span>
        </div>
      `).join('')}
      <button class="btn btn-sm" onclick="tcAddGradientStop()" style="font-size:11px;padding:3px 8px;margin-top:4px;">＋ 스톱 추가</button>
    `;
  } else if (layer.type === 'vignette') {
    specific = `
      <div class="tc-section-title">비네트</div>
      ${tcPropRange('강도', 'intensity', layer.intensity, 0, 100, 1)}
      ${tcPropRange('확산', 'spread', layer.spread, 0, 100, 1)}
    `;
  } else if (layer.type === 'text') {
    const fontOpts = tcProjectFonts.length > 0
      ? tcProjectFonts.map(f => `<option value="${f.role}"${layer.fontRole === f.role ? ' selected' : ''}>${tcFontLabel(f.role)} — ${f.family}</option>`).join('')
      : `<option value="">기본 (Pretendard)</option>`;
    specific = `
      <div class="tc-section-title">텍스트</div>
      <div class="tc-prop-row">
        <label class="tc-prop-label">내용</label>
        <textarea class="tc-prop-input" rows="2" style="min-height:50px;resize:vertical;" oninput="tcSetProp('text', this.value)">${layer.text}</textarea>
      </div>
      ${tcPropNumber('X', 'x', layer.x)}
      ${tcPropNumber('Y', 'y', layer.y)}
      ${tcPropRange('크기', 'fontSize', layer.fontSize, 16, 300, 2)}
      ${tcPropSelect('정렬', 'align', layer.align, ['left','center','right'])}
      <div class="tc-section-title">폰트</div>
      <div class="tc-prop-row">
        <label class="tc-prop-label">폰트</label>
        <select class="tc-prop-input" onchange="tcSetFontRole(this.value)">${fontOpts}</select>
      </div>
      ${tcPropSelect('굵기', 'fontWeight', layer.fontWeight, ['400','700','900'])}
      <div class="tc-prop-row">
        <label class="tc-prop-label">색상</label>
        <input type="color" value="${layer.color}" class="tc-prop-input" style="height:28px;padding:2px 4px;" oninput="tcSetProp('color', this.value)">
      </div>
      <div class="tc-section-title">그림자</div>
      ${tcPropRange('흐림', 'shadowBlur', layer.shadowBlur, 0, 60, 1)}
      ${tcPropNumber('X', 'shadowOffsetX', layer.shadowOffsetX)}
      ${tcPropNumber('Y', 'shadowOffsetY', layer.shadowOffsetY)}
      <div class="tc-prop-row">
        <label class="tc-prop-label">그림자색</label>
        <input type="color" value="${tcRgbaToHex(layer.shadowColor)}" class="tc-prop-input" style="height:28px;padding:2px 4px;" oninput="tcSetShadowColor(this.value, ${tcGetAlpha(layer.shadowColor)})">
      </div>
      <div class="tc-section-title">외곽선</div>
      ${tcPropRange('두께', 'strokeWidth', layer.strokeWidth, 0, 20, 1)}
      <div class="tc-prop-row">
        <label class="tc-prop-label">색상</label>
        <input type="color" value="${layer.strokeColor || '#000000'}" class="tc-prop-input" style="height:28px;padding:2px 4px;" oninput="tcSetProp('strokeColor', this.value)">
      </div>
    `;
  }

  el.innerHTML = common + specific;
}

// 속성 헬퍼 빌더
function tcPropRange(label, key, value, min, max, step) {
  return `<div class="tc-prop-row">
    <label class="tc-prop-label">${label}</label>
    <input type="range" min="${min}" max="${max}" step="${step}" value="${value}" class="tc-prop-range"
      oninput="tcSetProp('${key}', ${step < 1 ? 'parseFloat' : 'parseInt'}(this.value)); document.getElementById('tc-${key}-val')&&(document.getElementById('tc-${key}-val').textContent=this.value);">
    <span id="tc-${key}-val" style="font-size:11px;color:#666;min-width:28px;text-align:right;">${value}</span>
  </div>`;
}
function tcPropNumber(label, key, value) {
  return `<div class="tc-prop-row">
    <label class="tc-prop-label">${label}</label>
    <input type="number" value="${value}" class="tc-prop-input" style="width:70px;" oninput="tcSetProp('${key}', parseInt(this.value)||0)">
  </div>`;
}
function tcPropSelect(label, key, value, opts) {
  return `<div class="tc-prop-row">
    <label class="tc-prop-label">${label}</label>
    <select class="tc-prop-input" onchange="tcSetProp('${key}', this.value)">
      ${opts.map(o => `<option value="${o}"${o === value ? ' selected' : ''}>${o}</option>`).join('')}
    </select>
  </div>`;
}

function tcSetProp(key, value) {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer) return;
  layer[key] = value;
  tcRender();
  if (key === 'text') tcRenderLayerPanel();
  // gradientType 변경 시 props 재렌더
  if (key === 'gradientType') tcRenderProps();
}

function tcSetFontRole(role) {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer) return;
  const font = tcProjectFonts.find(f => f.role === role);
  layer.fontRole = role;
  if (font) {
    layer.fontFamily = `'${font.family}', sans-serif`;
  }
  tcRender();
}

function tcSetShadowColor(hexColor, alpha) {
  const r = parseInt(hexColor.slice(1,3),16);
  const g = parseInt(hexColor.slice(3,5),16);
  const b = parseInt(hexColor.slice(5,7),16);
  tcSetProp('shadowColor', `rgba(${r},${g},${b},${alpha})`);
}

function tcGradientStopColor(idx, hex) {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer?.stops?.[idx]) return;
  const a = tcGetAlpha(layer.stops[idx].color);
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  layer.stops[idx].color = `rgba(${r},${g},${b},${a})`;
  tcRender();
}

function tcGradientStopOffset(idx, val) {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer?.stops?.[idx]) return;
  layer.stops[idx].offset = Math.max(0, Math.min(1, val));
  tcRender(); tcRenderProps();
}

function tcGradientStopAlpha(idx, val) {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer?.stops?.[idx]) return;
  const col = layer.stops[idx].color;
  const m = col.match(/[\d.]+/g) || [];
  const r = m[0]||0, g = m[1]||0, b = m[2]||0;
  layer.stops[idx].color = `rgba(${r},${g},${b},${val})`;
  tcRender(); tcRenderProps();
}

function tcAddGradientStop() {
  const layer = tcLayers.find(l => l.id === tcSelectedId);
  if (!layer) return;
  layer.stops.push({ offset: 0.5, color: 'rgba(0,0,0,0.5)' });
  tcRenderProps(); tcRender();
}

// ── 색상 유틸 ─────────────────────────────────────────────────────────────
function tcRgbaToHex(color) {
  if (!color) return '#000000';
  if (color.startsWith('#')) return color.slice(0,7);
  const m = color.match(/[\d.]+/g);
  if (!m) return '#000000';
  return '#' + [m[0],m[1],m[2]].map(v => parseInt(v).toString(16).padStart(2,'0')).join('');
}
function tcGetAlpha(color) {
  if (!color) return 1;
  const m = color.match(/rgba?\([\d.,\s]+\)/);
  if (!m) return 1;
  const parts = m[0].match(/[\d.]+/g);
  return parts && parts.length >= 4 ? parseFloat(parts[3]) : 1;
}

// ── 스펙 로드 ────────────────────────────────────────────────────────────
function tcLoadSpec(idx) {
  const spec = tcSpecs[idx];
  if (!spec) return;
  tcLayers = [];
  if (spec.image_path) {
    const url = '/output/' + tcSlug.replace(/^.*\//, '') + '/' + spec.image_path.replace(/^.*\/images\//, 'images/');
    tcAddImageLayer(url, spec.image_path.split('/').pop());
  }
  tcAddGradientLayer();
  if (spec.overlay_text) tcAddTextLayer(spec.overlay_text);
  tcRender(); tcRenderLayerPanel(); tcRenderProps();
}

// ── 드래그&드롭 (이미지 패널 → 캔버스) ───────────────────────────────────
function tcDragStart(e, url) {
  e.dataTransfer.setData('text/plain', url);
  e.dataTransfer.effectAllowed = 'copy';
}

function tcDrop(e) {
  e.preventDefault();
  const url = e.dataTransfer.getData('text/plain');
  if (url && url.startsWith('/')) {
    tcAddImageLayer(url, url.split('/').pop());
  }
}

// ── 파일 업로드 ───────────────────────────────────────────────────────────
function tcUploadFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => tcAddImageLayer(ev.target.result, file.name);
  reader.readAsDataURL(file);
}

// ── 마우스 이벤트 ─────────────────────────────────────────────────────────
function tcMouseDown(e) {
  if (!tcCanvas) return;
  const { cx, cy } = tcClientToCanvas(e);
  const selLayer = tcLayers.find(l => l.id === tcSelectedId);

  // 그라데이션 레이어 선택 상태: 드래그 = 방향 설정
  if (selLayer && selLayer.type === 'gradient' && selLayer.gradientType === 'linear') {
    tcDragState = {
      type: 'gradient_dir',
      layerId: selLayer.id,
      startX: cx, startY: cy,
      x0: cx, y0: cy, x1: cx, y1: cy,
      curX: cx, curY: cy,
    };
    return;
  }

  // 일반 레이어 히트테스트
  const layer = tcHitTest(cx, cy);
  if (layer) {
    tcSelectedId = layer.id;
    tcDragState = {
      type: 'layer',
      layerId: layer.id,
      startX: cx, startY: cy,
      origX: layer.x !== undefined ? layer.x : 0,
      origY: layer.y !== undefined ? layer.y : 0,
    };
    tcRender(); tcRenderLayerPanel(); tcRenderProps();
  }
}

function tcMouseMove(e) {
  if (!tcDragState) return;
  const { cx, cy } = tcClientToCanvas(e);

  if (tcDragState.type === 'gradient_dir') {
    tcDragState.x1 = cx; tcDragState.y1 = cy;
    tcDragState.curX = cx; tcDragState.curY = cy;
    tcRender();
    return;
  }

  if (tcDragState.type === 'layer') {
    const dx = cx - tcDragState.startX;
    const dy = cy - tcDragState.startY;
    const layer = tcLayers.find(l => l.id === tcDragState.layerId);
    if (!layer) return;
    if (layer.type === 'image' || layer.type === 'text') {
      layer.x = tcDragState.origX + dx;
      layer.y = tcDragState.origY + dy;
      tcRender();
    }
  }
}

function tcMouseUp(e) {
  if (!tcDragState) return;

  if (tcDragState.type === 'gradient_dir') {
    const layer = tcLayers.find(l => l.id === tcDragState.layerId);
    if (layer) {
      layer.x0 = tcDragState.x0;
      layer.y0 = tcDragState.y0;
      layer.x1 = tcDragState.x1;
      layer.y1 = tcDragState.y1;
    }
    tcDragState = null;
    tcRender(); tcRenderProps();
    return;
  }

  tcDragState = null;
  tcRenderProps();
}

function tcClientToCanvas(e) {
  if (!tcCanvas) return { cx: 0, cy: 0 };
  const rect = tcCanvas.getBoundingClientRect();
  return {
    cx: Math.round((e.clientX - rect.left) / TC_SCALE),
    cy: Math.round((e.clientY - rect.top) / TC_SCALE),
  };
}

function tcHitTest(cx, cy) {
  for (const layer of tcLayers) {
    if (!layer.visible) continue;
    if (layer.type === 'image') {
      if (cx >= layer.x && cx <= layer.x + layer.width && cy >= layer.y && cy <= layer.y + layer.height)
        return layer;
    } else if (layer.type === 'text') {
      tcCtx.font = `${layer.fontWeight||'700'} ${layer.fontSize}px ${layer.fontFamily}`;
      const w = tcCtx.measureText(layer.text).width;
      const h = layer.fontSize * 1.4;
      const tx = layer.align === 'center' ? layer.x - w/2 : layer.x;
      if (cx >= tx - 12 && cx <= tx + w + 12 && cy >= layer.y - h/2 - 8 && cy <= layer.y + h/2 + 8)
        return layer;
    }
  }
  return null;
}

// ── 캔버스 커서 힌트 ─────────────────────────────────────────────────────
function tcMouseEnter(e) {
  if (!tcCanvas) return;
  const selLayer = tcLayers.find(l => l.id === tcSelectedId);
  if (selLayer && selLayer.type === 'gradient' && selLayer.gradientType === 'linear') {
    tcCanvas.style.cursor = 'crosshair';
  } else {
    tcCanvas.style.cursor = 'default';
  }
}

// ── 상태 저장/복원 ───────────────────────────────────────────────────────
async function tcSaveState() {
  const statusEl = document.getElementById('tc-export-status');
  try {
    const res = await fetch(`/api/p/${tcSlug}/thumbnail-canvas/state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ layers: tcLayers }),
    });
    const data = await res.json();
    if (data.ok) {
      if (statusEl) { statusEl.textContent = '💾 저장됨'; setTimeout(() => { if (statusEl) statusEl.textContent = ''; }, 2000); }
    }
  } catch(e) {
    if (statusEl) statusEl.textContent = '❌ 저장 실패';
  }
}

function tcRestoreState(state) {
  tcLayers = state.layers || [];
  // 이미지 레이어 캐시 워밍업
  for (const layer of tcLayers) {
    if (layer.type === 'image' && layer.src) {
      tcLoadImage(layer.src, () => tcRender());
    }
  }
  tcSelectedId = tcLayers[0]?.id || null;
  tcRender();
  tcRenderLayerPanel();
  tcRenderProps();
}

// ── 내보내기 ─────────────────────────────────────────────────────────────
async function tcExport() {
  const statusEl = document.getElementById('tc-export-status');
  if (statusEl) statusEl.textContent = '내보내는 중...';

  const prevSelected = tcSelectedId;
  tcSelectedId = null;
  tcRender();

  const dataUrl = tcCanvas.toDataURL('image/png');
  tcSelectedId = prevSelected;
  tcRender();

  try {
    const res = await fetch(`/api/p/${tcSlug}/thumbnail-canvas/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_data: dataUrl, filename: `thumbnail_${Date.now()}.png` }),
    });
    const data = await res.json();
    if (data.ok) {
      if (statusEl) statusEl.textContent = `✅ 저장됨: ${data.filename}`;
      setTimeout(() => { if (statusEl) statusEl.textContent = ''; }, 4000);
    } else {
      if (statusEl) statusEl.textContent = '❌ 저장 실패';
    }
  } catch(err) {
    if (statusEl) statusEl.textContent = '❌ 오류: ' + err.message;
  }
}
