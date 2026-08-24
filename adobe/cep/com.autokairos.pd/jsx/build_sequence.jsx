// auto_kairos — manifest 기반 프리미어 시퀀스 조립 (1단계)
//
// **애프터이펙트와 같은 매니페스트를 읽는다.** 씬마다 `start`·`duration` 이
// 이미 구워져 있으므로(timeline.py 가 프레임 단위로 맞춰 낸다) 여기서는
// 계산하지 않고 그 자리에 놓기만 한다.
//
// 프리미어가 할 수 있는 것과 없는 것이 애프터이펙트와 다르다. 쉐이프·텍스트
// 레이어를 스크립트로 만들고 속성마다 키를 찍는 일은 여기서 안 된다. 그래서
// 이 스크립트는 **거친 편집본을 까는 데까지**만 한다 —
//
//   · V1 씬 그림 · V2 영상(있으면) · A1 나레이션 — 제 자리에 제 길이로
//   · 셋을 다 깐다. 편집하다 한 컷을 정지로 되돌릴 때 밑에 그림이 있어야 한다
//   · 씬 번호·제목으로 마커
//   · 자막 SRT 와 에셋을 빈으로 정리
//
// 연출(레이아웃 글자·레이어 모션)은 애프터이펙트가 맡고, 프리미어는 편집을
// 맡는다. 나중에 MOGRT 로 넘길 자리는 마커가 알려 준다.

function akBuildSequence(manifestPath, opts) {
    var log = [];
    try {
        if (typeof app === "undefined" || !app.project) { return "ERROR: 프로젝트를 여세요"; }
        var f = new File(manifestPath);
        if (!f.exists) { return "ERROR: 매니페스트 없음 " + manifestPath; }
        f.encoding = "UTF-8";
        f.open("r"); var raw = f.read(); f.close();
        var M = JSON.parse(raw);
        var scenes = M.scenes || [];
        if (!scenes.length) { return "ERROR: 씬이 없습니다"; }
        opts = opts || {};

        var proj = app.project;
        var bin = akBin(proj, "auto_kairos");
        var seq = akSequence(proj, opts.name || "auto_kairos Final", scenes, bin, log);
        if (!seq) { return "ERROR: 시퀀스를 만들지 못했습니다 — " + log.join(" / "); }

        // **트랙을 나눈다 — 애프터이펙트와 같은 쌓임이다.**
        //
        //   V2  영상        있으면 이것이 보인다
        //   V1  씬 그림     늘 깐다
        //   A1  나레이션
        //
        // 처음에는 「영상이 있으면 그림은 건너뛴다」로 했는데, 그러면 영상이
        // 있는 29씬(99번부터)에 그림이 아예 안 깔린다. 편집하다 한 컷만 정지로
        // 되돌리고 싶을 때 밑에 그림이 없으면 다시 조립해야 한다. 애프터이펙트
        // 쪽은 이미 셋을 다 올리게 고쳐 두었는데 여기만 안 맞았다.
        var vt = akTrack(seq, "video", 0, log);
        var vt2 = akTrack(seq, "video", 1, log);
        var at = akTrack(seq, "audio", 0, log);
        var placed = 0, vids = 0, noAsset = 0, audio = 0;

        for (var i = 0; i < scenes.length; i++) {
            var s = scenes[i];
            var t0 = Number(s.start || 0);
            var dur = Number(s.duration || 5);
            var pf = s.prefix || ("S" + (i + 1) + "_");

            // 그림은 V1 에 늘 깐다. 정지라 길이를 씬에 맞춰 늘린다.
            if (s.image) {
                var im = akImportOnce(proj, s.image, bin, log);
                if (im && vt && akPlace(vt, im, t0, dur, log, pf)) { placed++; }
                else if (!im) { noAsset++; }
            }
            // 영상은 V2 에 — 있으면 이것이 보인다.
            if (s.video) {
                var vi = akImportOnce(proj, s.video, bin, log);
                if (vi && vt2 && akPlace(vt2, vi, t0, dur, log, pf + "영상 ")) { vids++; }
                else if (!vi) { noAsset++; }
            }
            // 어느 쪽도 없으면 조용히 넘기지 않는다 — 편집자가 빈 자리를 못 찾는다
            if (!s.image && !s.video) {
                noAsset++;
                log.push(pf + "쓸 그림도 영상도 없습니다");
            }

            if (s.audio) {
                var aItem = akImportOnce(proj, s.audio, bin, log);
                if (aItem && akPlace(at, aItem, t0, dur, log, pf + "음성 ")) { audio++; }
            }

            akMarker(seq, t0, pf + (s.title || ""), s.subtitle || "", log);
        }

        // 자막은 빈에 넣어 둔다. 캡션 트랙에 붙이는 것은 프리미어 판마다
        // 달라 손으로 끄는 편이 확실하다 — 어디 있는지만 알려 준다.
        var srt = opts.srt ? akImportOnce(proj, opts.srt, bin, log) : null;

        return "OK: 씬 " + scenes.length + "개 → " + seq.name
             + " (그림 " + placed + " · 영상 " + vids + " · 음성 " + audio
             + (noAsset ? (" · 자산 없음 " + noAsset) : "")
             + (srt ? " · 자막 SRT 빈에 있음" : "")
             + ")" + (log.length ? (" | " + log.join(", ")) : "");
    } catch (e) {
        return "ERROR: " + e.toString() + (log.length ? (" | " + log.join(", ")) : "");
    }
}

/* 트랙 하나를 집는다. 모자라면 만든다.

   새 시퀀스는 보통 V1·A1 만 있다. 영상을 그림 위에 올리려면 V2 가 필요한데,
   없는 트랙을 집으면 그 자리부터 조용히 아무것도 안 깔린다. */
function akTrack(seq, kind, idx, log) {
    var list = (kind === "audio") ? seq.audioTracks : seq.videoTracks;
    try {
        while (list.numTracks <= idx) {
            if (kind === "audio") { seq.audioTracks.addTracks(1); }
            else { seq.videoTracks.addTracks(1); }
            list = (kind === "audio") ? seq.audioTracks : seq.videoTracks;
        }
        return list[idx];
    } catch (e) {
        log.push(kind + " 트랙 " + (idx + 1) + " 을 만들지 못했습니다: " + e.toString());
        return (list.numTracks > idx) ? list[idx] : null;
    }
}

/* 빈 하나를 찾거나 만든다 — 프로젝트 창이 씬 수만큼 어지러워지지 않게. */
function akBin(proj, name) {
    try {
        var root = proj.rootItem;
        for (var i = 0; i < root.children.numItems; i++) {
            var c = root.children[i];
            if (c && c.name === name && c.type === ProjectItemType.BIN) { return c; }
        }
        return root.createBin(name);
    } catch (e) { return proj.rootItem; }
}

/* **같은 파일을 두 번 들여오지 않는다.** 142씬이면 같은 배경이 여러 번
   불리는데, 부를 때마다 들여오면 프로젝트 창이 사본으로 찬다. */
function akImportOnce(proj, path, bin, log) {
    try {
        var f = new File(path);
        if (!f.exists) { log.push("파일 없음 " + f.name); return null; }
        var found = akFindItem(bin, f.fsName, f.name);
        if (found) { return found; }
        proj.importFiles([f.fsName], true, bin, false);
        found = akFindItem(bin, f.fsName, f.name);
        if (!found) { log.push("가져오기 실패 " + f.name); }
        return found;
    } catch (e) { log.push("가져오기 오류 " + e.toString()); return null; }
}

function akFindItem(bin, fsName, name) {
    try {
        for (var i = 0; i < bin.children.numItems; i++) {
            var c = bin.children[i];
            if (!c) { continue; }
            if (c.name === name) { return c; }
            try {
                var p = c.getMediaPath();
                if (p && p === fsName) { return c; }
            } catch (e2) { }
        }
    } catch (e) { }
    return null;
}

/* 시퀀스를 찾거나 만든다.

   프리미어는 **빈 시퀀스를 프리셋 없이 못 만든다.** 프리셋 경로는 설치판마다
   달라 믿을 수 없으므로, 첫 씬의 자산으로 시퀀스를 만들게 한다
   (`createNewSequenceFromClips`) — 그 자산의 규격이 그대로 시퀀스 규격이 된다.
   그다음 그 클립은 지우고 처음부터 다시 깐다. */
function akSequence(proj, name, scenes, bin, log) {
    try {
        for (var i = 0; i < proj.sequences.numSequences; i++) {
            var s = proj.sequences[i];
            if (s && s.name === name) {
                try { proj.openSequence(s.sequenceID); } catch (eO) { }
                akClearTracks(s, log);
                return s;
            }
        }
    } catch (e) { }
    // 첫 자산으로 규격을 잡는다
    var seed = null;
    for (var k = 0; k < scenes.length && !seed; k++) {
        var src = scenes[k].video || scenes[k].image;
        if (src) { seed = akImportOnce(proj, src, bin, log); }
    }
    if (!seed) { log.push("규격을 잡을 자산이 없습니다"); return null; }
    try {
        var seq = proj.createNewSequenceFromClips(name, [seed], bin);
        if (seq) { akClearTracks(seq, log); return seq; }
    } catch (e) { log.push("시퀀스 생성 실패 " + e.toString()); }
    return null;
}

/* 다시 깔기 전에 비운다 — **트랙만 비우고 프로젝트 자산은 건드리지 않는다.**
   자산까지 지우면 사람이 따로 넣어 둔 것까지 날아간다. */
function akClearTracks(seq, log) {
    try {
        var kinds = [seq.videoTracks, seq.audioTracks];
        for (var g = 0; g < kinds.length; g++) {
            for (var t = 0; t < kinds[g].numTracks; t++) {
                var tr = kinds[g][t];
                for (var c = tr.clips.numItems - 1; c >= 0; c--) {
                    try { tr.clips[c].remove(false, false); } catch (eR) { }
                }
            }
        }
    } catch (e) { log.push("트랙 비우기 실패 " + e.toString()); }
}

/* 자산 하나를 제 자리에 제 길이로 놓는다.

   `overwriteClip` 은 초를 받는다. 놓은 뒤 끝을 씬 길이에 맞춘다 — 정지 그림은
   기본 길이(보통 5초)로 들어오고 영상은 제 길이로 들어오므로, 양쪽 다 씬에
   맞춰야 자리가 안 밀린다. */
function akPlace(track, item, t0, dur, log, pf) {
    try {
        // **정지 그림은 기본 길이가 짧다.** 프리미어는 스틸을 환경설정 기본값
        // (보통 5초)으로 들여오는데, 씬이 그보다 길면 뒤가 빈다(이 편에서 9씬).
        // 놓기 전에 쓸 수 있는 길이를 늘려 둔다 — 놓은 뒤에는 못 늘린다.
        try { item.setOutPoint(dur + 1, 4); } catch (eO) { }   // 4 = 비디오 미디어
        track.overwriteClip(item, t0);
        var clip = null;
        for (var i = track.clips.numItems - 1; i >= 0; i--) {
            var c = track.clips[i];
            if (Math.abs(Number(c.start.seconds) - t0) < 0.02) { clip = c; break; }
        }
        if (!clip) { log.push(pf + "놓았으나 클립을 못 찾음"); return true; }
        try {
            var end = clip.end;
            end.seconds = t0 + dur;
            clip.end = end;
        } catch (eE) { log.push(pf + "길이 맞추기 실패"); }
        return true;
    } catch (e) {
        log.push(pf + "배치 실패 " + e.toString());
        return false;
    }
}

/* 씬 머리마다 마커 — 편집자가 씬을 이름으로 찾는다.
   나중에 연출을 얹을 자리도 이것으로 짚는다. */
function akMarker(seq, t0, name, note, log) {
    try {
        var m = seq.markers.createMarker(t0);
        m.name = String(name || "");
        if (note) { m.comments = String(note).substr(0, 200); }
    } catch (e) { log.push("마커 실패 " + e.toString()); }
}
