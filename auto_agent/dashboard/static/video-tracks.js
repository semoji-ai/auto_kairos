/* Native dialog shared by Tauri and the web dashboard. Files are never split. */
function showVideoTrackBadges(state) {
  document.querySelectorAll('[data-video-track-badge]').forEach(e => e.remove());
  for (const clip of state.resolved?.clips || []) for (const id of clip.sceneIds) {
    const scene = state.scenes.find(s => s.sceneId === id);
    if (!scene) continue;
    const card = document.querySelector('.sb-card[data-scene="' + scene.sceneNumber + '"]');
    if (!card) continue;
    const badge = document.createElement('div');
    badge.dataset.videoTrackBadge = 'true';
    badge.style.cssText = 'color:#8bd5ca;padding:8px;font-size:12px';
    badge.textContent = '🎞 통합 영상 · ' + clip.clipId;
    card.prepend(badge);
  }
}
window.loadVideoTrackBadges = async function (project) {
  try {
    const res = await fetch('/api/p/' + encodeURIComponent(project) + '/video-tracks');
    if (res.ok) showVideoTrackBadges(await res.json());
  } catch (_) { /* The dialog surfaces detailed errors; do not break the storyboard. */ }
};
window.openVideoTracks = async function (project) {
  const endpoint = '/api/p/' + encodeURIComponent(project) + '/video-tracks';
  const dialog = document.createElement('dialog');
  dialog.style.cssText = 'width:min(1000px,95vw);max-height:90vh;overflow:auto;background:#18181b;color:#eee;padding:24px';
  dialog.innerHTML = '<h2>통합 비디오 트랙</h2><p>원본 영상 하나를 연속된 여러 씬에 배치합니다. 기존 이미지·TTS는 유지됩니다. 영상은 무음이며 속도 변경은 지원하지 않습니다.</p>' +
    '<p data-status role="status"></p><div data-list></div><hr><form>' +
    '<label>영상 <select name="file" required></select></label> ' +
    '<label>첫 씬 <select name="first"></select></label> ' +
    '<label>마지막 씬 <select name="last"></select></label><br>' +
    '<label>원본 시작(초) <input name="sin" type="number" min="0" step="0.001" value="0" required></label> ' +
    '<label>원본 종료(초) <input name="sout" type="number" min="0.001" step="0.001" required></label>' +
    '<p>씬 내부 전환과 TTS 동기는 별도 확인하세요. 길이 차이는 경고에 표시됩니다.</p>' +
    '<button type="submit">검증 후 추가·활성화</button></form>' +
    '<video controls muted style="width:100%;max-height:300px"></video>' +
    '<p><label>비활성 초안 JSON 가져오기 <input data-import type="file" accept=".json"></label></p>' +
    '<p><button data-reload>새로고침</button> <button data-rebuild>렌더 매니페스트 갱신</button> <button data-close>닫기</button></p>';
  document.body.append(dialog); dialog.showModal();
  dialog.addEventListener('close', () => dialog.remove());
  dialog.querySelector('[data-close]').onclick = () => dialog.close();
  const status = dialog.querySelector('[data-status]');
  const form = dialog.querySelector('form');
  const video = dialog.querySelector('video');
  let state, busy = false, previewClip, editingId = null;
  async function request(method, body) {
    const res = await fetch(endpoint, {method, headers: {'Content-Type': 'application/json'},
      ...(body ? {body: JSON.stringify(body)} : {})});
    const data = await res.json();
    if (!res.ok) throw Error([data.error, ...(data.errors || [])].join('\n'));
    return data;
  }
  function preview(c) {
    previewClip = c;
    video.src = c.url; video.muted = true;
    video.onloadedmetadata = () => { video.currentTime = c.sourceIn || 0; };
    video.ontimeupdate = () => {
      if (previewClip && video.currentTime >= previewClip.sourceOut) video.pause();
    };
  }
  function render() {
    showVideoTrackBadges(state);
    const box = dialog.querySelector('[data-list]'); box.replaceChildren();
    status.textContent = state.resolved.errors.join('\n') || '현재 매핑 검증 완료. 최종 영상 품질 승인을 의미하지 않습니다.';
    for (const track of state.data.tracks || []) for (const clip of track.clips || []) {
      const row = document.createElement('p');
      const nums = (clip.sceneIds || []).map(id => state.scenes.find(s => s.sceneId === id)?.sceneNumber ?? id);
      row.append(document.createTextNode(clip.clipId + ' · S' + nums.join(', S') + ' · ' +
        (track.enabled !== false && clip.enabled !== false ? '활성' : '비활성') + ' '));
      const button = document.createElement('button');
      button.textContent = clip.enabled === false ? '활성화' : '비활성화';
      button.onclick = () => save(d => {
        const t = d.tracks.find(t => t.trackId === track.trackId);
        t.clips.find(c => c.clipId === clip.clipId).enabled = clip.enabled === false;
      });
      row.append(button);
      const edit = document.createElement('button'); edit.textContent = '구간 수정·재검토';
      edit.onclick = () => {
        editingId = clip.clipId;
        form.elements.file.value = clip.sourcePath;
        form.elements.first.value = clip.sceneIds[0];
        form.elements.last.value = clip.sceneIds[clip.sceneIds.length - 1];
        form.elements.sin.value = clip.sourceInSec;
        form.elements.sout.value = clip.sourceOutSec;
        status.textContent = clip.clipId + ' 수정 중. 현재 씬/TTS와 영상을 확인한 후 저장하세요.';
      };
      row.append(edit);
      const resolved = state.resolved.clips.find(c => c.clipId === clip.clipId);
      if (resolved) {
        const play = document.createElement('button'); play.textContent = '원본 구간 확인';
        play.onclick = () => preview(resolved); row.append(play);
        for (const sid of clip.sceneIds) {
          const s = state.scenes.find(s => s.sceneId === sid);
          const jump = document.createElement('button'); jump.textContent = 'S' + s.sceneNumber;
          jump.onclick = () => preview({...resolved,
            sourceIn: resolved.sourceIn + Math.max(0, s.start - resolved.start)});
          row.append(jump);
        }
        row.append(document.createTextNode(' ' + (resolved.warnings || []).join(' / ')));
      }
      box.append(row);
    }
    for (const name of ['first', 'last']) {
      const sel = form.elements[name]; const previous = sel.value;
      sel.replaceChildren(...state.scenes.map(s => new Option('S' + s.sceneNumber, s.sceneId)));
      if (previous) sel.value = previous;
    }
    const files = form.elements.file; const previous = files.value;
    files.replaceChildren(...state.files.map(p => new Option(p, p)));
    if (previous) files.value = previous;
  }
  async function reload() {
    try { state = await request('GET'); render(); } catch (e) { status.textContent = e.message; }
  }
  async function save(change) {
    if (busy) return; busy = true;
    try {
      const data = JSON.parse(JSON.stringify(state.data)); change(data);
      state = await request('POST', {data, revision: state.data.revision || 0}); editingId = null; render();
      status.textContent += ' 저장됨. 전체 렌더는 매니페스트를 재빌드하세요.';
    } catch (e) { status.textContent = e.message; } finally { busy = false; }
  }
  form.elements.file.onchange = () => {
    if (!state) return;
    previewClip = null;
    video.src = '/output/' + encodeURIComponent(state.projectFolder) + '/' + form.elements.file.value.split('/').map(encodeURIComponent).join('/');
    video.onloadedmetadata = () => { form.elements.sout.value = Math.floor(video.duration * 1000) / 1000; };
  };
  form.onsubmit = e => {
    e.preventDefault();
    if (!state) return;
    const first = state.scenes.findIndex(s => s.sceneId === form.elements.first.value);
    const last = state.scenes.findIndex(s => s.sceneId === form.elements.last.value);
    if (last < first) { status.textContent = '마지막 씬은 첫 씬 이후여야 합니다.'; return; }
    save(data => {
      data.tracks ||= [];
      let track = data.tracks.find(t => t.trackId === 'primary-video');
      if (!track) { track = {trackId: 'primary-video', enabled: true, clips: []}; data.tracks.push(track); }
      if (editingId) {
        for (const t of data.tracks) t.clips = t.clips.filter(c => c.clipId !== editingId);
      }
      track.enabled = true;
      track.clips.push({clipId: editingId || 'clip-' + crypto.randomUUID(), enabled: true,
        sourcePath: form.elements.file.value,
        sceneIds: state.scenes.slice(first, last + 1).map(s => s.sceneId),
        anchor: {sceneId: state.scenes[first].sceneId, offsetFrames: 0},
        sourceInSec: Number(form.elements.sin.value), sourceOutSec: Number(form.elements.sout.value),
        playbackRate: 1, audioPolicy: 'mute'});
    });
  };
  dialog.querySelector('[data-reload]').onclick = reload;
  dialog.querySelector('[data-import]').onchange = async e => {
    try {
      const parsed = JSON.parse(await e.target.files[0].text());
      const imported = parsed.data || parsed;
      if (!Array.isArray(imported.tracks)) throw Error('tracks 배열이 없습니다.');
      await save(data => {
        data.tracks ||= [];
        for (const track of imported.tracks) {
          let target = data.tracks.find(t => t.trackId === track.trackId);
          if (!target) { target = {trackId: track.trackId, enabled: true, clips: []}; data.tracks.push(target); }
          for (const clip of track.clips) target.clips.push({...clip, enabled: false});
        }
      });
    } catch (e) { status.textContent = e.message; }
  };
  dialog.querySelector('[data-rebuild]').onclick = async () => {
    status.textContent = '렌더 매니페스트 갱신 중…';
    try {
      const response = await fetch('/api/p/' + encodeURIComponent(project) + '/rebuild-manifest', {method: 'POST'});
      const data = await response.json();
      status.textContent = data.ok ? '갱신 완료. 스튜디오/미리보기를 새로고침하세요.' : (data.error || '갱신 실패');
    } catch (e) { status.textContent = e.message; }
  };
  await reload();
  if (state) form.elements.file.onchange();
};
