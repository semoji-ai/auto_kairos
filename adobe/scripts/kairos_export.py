#!/usr/bin/env python3
"""애프터이펙트 매니페스트 → 카이로스 편집기(cut.semoji.dev) 타임라인.

편의 output 폴더에 있는 manifest.json(씬·레이어·카메라·움직임)을 읽어, 카이로스 MCP 로
올릴 파일 묶음과 타임라인 JSON 을 만든다. MCP 호출(파일 올리기·타임라인 저장) 자체는
클로드 세션이 한다 — 이 스크립트는 그 앞뒤의 계산만 맡는다. 절차는 adobe/docs/kairos_export.md.

  1) plan     : 올릴 파일을 <out>/files 에 모으고 <out>/plan.json 을 쓴다.
                타임라인의 에셋 자리는 "@file:<파일 이름>" 으로 비워 둔다.
  2) (세션)   : plan.json 의 files 를 create_upload → PUT → complete_upload 로 올리고,
                "<파일 이름> <timeline_asset>" 줄을 <out>/map.txt 에 적는다.
  3) finalize : map.txt 로 자리를 채워 <out>/timeline.json 을 쓴다 → save_timeline 에 넣는다.

옮기는 것: 레이어 배치(위치·배율), 카메라 줌(레이어마다 위치·배율 키로 구워 넣음),
강조(zoom_emphasis), 까딱임(bob — 발을 축으로 왕복), 흔들기(wiggle), 음성, 말자막, 제목.
규칙: 효과 키프레임(까딱임·강조·흔들기)은 모두 이지 이즈를 건다. 카메라는 애펙 70:30.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

CAM_EASE = [0.7, 0, 0.7, 1]    # 애펙 70:30
SMOOTH = [0.33, 0, 0.67, 1]    # 이지 이즈
MAX_PHOTO_EDGE = 2560          # 큰 사진은 줄여서 올린다(편집기 디코드 부담)
CONTENT_TYPES = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp',
                 'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'm4a': 'audio/mp4'}
PLACEHOLDER = '@file:'


class ExportError(Exception):
    pass


def _r(v, d=5):
    return round(v, d)


def bezier(ease, u):
    """cubic-bezier(x1, y1, x2, y2) 의 진행 비율."""
    x1, y1, x2, y2 = ease
    lo, hi = 0.0, 1.0
    for _ in range(50):
        s = (lo + hi) / 2
        x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3
        if x < u:
            lo = s
        else:
            hi = s
    s = (lo + hi) / 2
    return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3


def localize(path, project_dir):
    """매니페스트의 절대 경로(NAS 등)를 이 기기의 편 폴더 기준으로 바꾼다."""
    p = Path(path)
    if p.is_file():
        return p
    marker = f'/{Path(project_dir).name}/'
    s = str(path)
    if marker in s:
        q = Path(project_dir) / s.split(marker, 1)[1]
        if q.is_file():
            return q
    raise ExportError(f'파일 없음: {path}')


def parse_scenes(text, total):
    """'1-6' · '3' · 'all' → (첫 씬, 끝 씬 다음) 0부터 세는 범위."""
    if text in (None, '', 'all'):
        return 0, total
    m = re.fullmatch(r'(\d+)(?:-(\d+))?', text.strip())
    if not m:
        raise ExportError(f"씬 범위는 '1-6' 꼴로 적는다: {text}")
    a = int(m.group(1))
    b = int(m.group(2) or a)
    if not (1 <= a <= b <= total):
        raise ExportError(f'씬 범위가 1~{total} 을 벗어남: {text}')
    return a - 1, b


def _fit(value):
    return json.loads(value.replace("'", '"')) if isinstance(value, str) else value


class Plan:
    def __init__(self, project_dir, out_dir, width, height):
        self.project_dir = Path(project_dir)
        self.out_dir = Path(out_dir)
        self.W, self.H = width, height
        self.files = {}

    def add_file(self, src, kind):
        src = localize(src, self.project_dir)
        name = src.name
        if name in self.files:
            if self.files[name]['source'] != str(src):
                raise ExportError(f'같은 이름의 다른 파일: {name}')
            return name
        ext = name.rsplit('.', 1)[-1].lower()
        if ext not in CONTENT_TYPES:
            raise ExportError(f'올릴 수 없는 형식: {name}')
        dst = self.out_dir / 'files' / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        size = None
        if kind == 'image':
            with Image.open(src) as im:
                size = im.size
                if ext in ('jpg', 'jpeg') and max(size) > MAX_PHOTO_EDGE:
                    im = im.convert('RGB')
                    im.thumbnail((MAX_PHOTO_EDGE, MAX_PHOTO_EDGE))
                    im.save(dst, quality=92)
                    size = im.size
                else:
                    shutil.copy(src, dst)
        else:
            shutil.copy(src, dst)
        self.files[name] = {'path': str(dst), 'source': str(src), 'kind': kind,
                            'content_type': CONTENT_TYPES[ext], 'bytes': dst.stat().st_size,
                            **({'width': size[0], 'height': size[1]} if size else {})}
        return name


def _frames(mv, fps, dur):
    a = round(mv['start'] * fps)
    b = min(dur - 1, round((mv['start'] + mv['duration']) * fps))
    return a, b


def scene_clips(plan, scene, index, start, dur, fps):
    """한 씬의 클립들. (clips, 쓴 레이어 수)"""
    W, H = plan.W, plan.H
    sid = scene['ae_comp_name'].split('_', 1)[1] if '_' in scene.get('ae_comp_name', '') else f'scene{index + 1}'
    cam = scene.get('camera')
    k0, k1 = (cam[0]['scale'] / 100, cam[-1]['scale'] / 100) if cam else (1.0, 1.0)

    def kat(fr):
        if not cam:
            return 1.0
        return k0 + (k1 - k0) * bezier(CAM_EASE, min(1, max(0, fr / max(1, dur - 1))))

    layers = scene.get('layers') or []
    # 강조가 하나라도 있으면 모든 레이어가 같은 시각에 키를 둔다 — 카메라 줌이 레이어끼리 어긋나지 않게
    pulses, wiggles = {}, []
    for L in layers:
        for mv in L.get('moves') or []:
            if mv.get('type') == 'zoom_emphasis':
                a, b = _frames(mv, fps, dur)
                if b - a >= 4:
                    pulses[L['name']] = (a, (a + b) // 2, b)
    motion_file = plan.project_dir / f'motion_{sid}.json'
    if motion_file.is_file():
        for mv in json.loads(motion_file.read_text()).get('motions') or []:
            if mv.get('preset') == 'zoom_emphasis':
                a, b = _frames(mv, fps, dur)
                pulses[mv['layer']] = (a, (a + b) // 2, b)
            if mv.get('preset') == 'wiggle':
                wiggles.append(mv)
    times = sorted({0, dur - 1} | {t for p in pulses.values() for t in p})
    eased = len(times) == 2
    clips = []

    if not layers and scene.get('image'):  # 사진 한 장
        name = plan.add_file(scene['image'], 'image')
        w, h = plan.files[name]['width'], plan.files[name]['height']
        fit = _fit(scene.get('imageFit')) or {'scale': 100, 'position': [W / 2, H / 2]}
        drawn_w = float(scene.get('width') or w) * fit['scale'] / 100
        sc = drawn_w / (w * min(W / w, H / h))
        clips.append({'id': f'{sid}_photo', 'track_id': 'V1', 'kind': 'image', 'start': start, 'dur': dur,
                      'asset': PLACEHOLDER + name, 'label': f'S{index + 1:02d} 사진',
                      'transform': {'x': _r((fit['position'][0] - W / 2) / W), 'y': _r((fit['position'][1] - H / 2) / H),
                                    'scale_x': _r(sc), 'scale_y': _r(sc)}})

    for li, L in enumerate(layers):
        name = plan.add_file(L['path'], 'image')
        w, h = plan.files[name]['width'], plan.files[name]['height']
        s0 = L['scale'] / 100
        f = min(W / w, H / h)
        bw, bh = w * f, h * f      # 편집기의 배율 1 크기
        dw, dh = w * s0, h * s0    # 애펙에서 그려진 크기
        cx, cy = L['position']
        bob = next((mv for mv in (L.get('moves') or []) if mv.get('type') == 'bob'), None)
        ax, ay = 0.5, 0.5
        if bob and L.get('foot'):
            ay = min(1.0, max(0.0, (L['foot'][1] - (cy - dh / 2)) / dh))
        Ax, Ay = cx + (ax - 0.5) * dw, cy + (ay - 0.5) * dh  # 기준점의 화면 자리(카메라 1)

        def pos(k):
            px, py = W / 2 + (Ax - W / 2) * k, H / 2 + (Ay - H / 2) * k
            c0x, c0y = px - (ax - 0.5) * bw, py - (ay - 0.5) * bh  # 배율 1 인 그림의 가운데
            return [_r((c0x - W / 2) / W), _r((c0y - H / 2) / H)]

        pulse = pulses.get(L['name'])

        def scl(fr):
            k = kat(fr) * s0 / f
            if pulse and fr == pulse[1]:
                k *= 1.08
            return [_r(k), _r(k)]

        kf = {}
        if cam or pulse:
            cam_ease = {'ease': CAM_EASE} if eased else {}
            kf['position'] = [{'t': t, 'v': pos(kat(t)), **(cam_ease if t == 0 else {})} for t in times]
            kf['scale'] = [{'t': t, 'v': scl(t),
                            **(cam_ease if t == 0 else ({'ease': SMOOTH} if pulse and t in pulse[:2] else {}))}
                           for t in times]
        clip = {'id': f'{sid}_{li}', 'track_id': f'V{li + 1}', 'kind': 'image', 'start': start, 'dur': dur,
                'asset': PLACEHOLDER + name, 'label': L.get('aeName') or L['name']}
        if kf:
            clip['keyframes'] = kf
        else:
            clip['transform'] = {'x': pos(1)[0], 'y': pos(1)[1], 'scale_x': _r(s0 / f), 'scale_y': _r(s0 / f)}
        if (ax, ay) != (0.5, 0.5):
            clip['anchor'] = [_r(ax, 4), _r(ay, 4)]
        if bob:  # 까딱임: 발을 축으로 좌우로 아주 조금, 왕복 반복
            amp = 0.5 if bob.get('intensity') == 'subtle' else 0.9
            half = int(bob.get('half_frames', 12))
            clip.setdefault('keyframes', {})['rotation'] = [{'t': 0, 'v': -amp, 'ease': SMOOTH},
                                                            {'t': half, 'v': amp, 'ease': SMOOTH}]
            clip['motion'] = {'rotation': {'loop': 'pingpong'}}
        for mv in wiggles:
            if mv['layer'] == L['name']:  # 흔들기: 그 구간에만 좌우로 떨기
                a, b = _frames(mv, fps, dur)
                step = max(2, (b - a) // 6)
                vals = [0, 3, -3, 2, -2, 1, 0]
                clip.setdefault('keyframes', {})['rotation'] = [
                    {'t': min(b, a + j * step), 'v': v, **({'ease': SMOOTH} if j < len(vals) - 1 else {})}
                    for j, v in enumerate(vals)]
        clips.append(clip)

    audio = scene.get('audio')
    if audio and audio != 'None':
        name = plan.add_file(audio, 'audio')
        clips.append({'id': f'{sid}_vo', 'track_id': 'A1', 'kind': 'audio', 'start': start, 'dur': dur,
                      'asset': PLACEHOLDER + name, 'src_dur': dur, 'label': f'S{index + 1:02d} 음성'})
    if scene.get('subtitle'):
        clips.append({'id': f'{sid}_sub', 'track_id': 'T1', 'kind': 'subtitle', 'start': start, 'dur': dur,
                      'text': scene['subtitle']})
    if scene.get('title') and dur > 24:
        clips.append({'id': f'{sid}_title', 'track_id': 'T2', 'kind': 'subtitle', 'start': start + 6, 'dur': dur - 12,
                      'text': scene['title'].replace('\\n', '\n'),
                      'style': {'y': 0.24, 'size': 0.075, 'background': 'none'}})
    return clips, max(1, len(layers))


def build_plan(project_dir, out_dir, scenes='all', width=1920, height=1080):
    """매니페스트 → {'files': {...}, 'timeline': {...}} (plan.json 으로도 쓴다)."""
    project_dir = Path(project_dir)
    manifest = json.loads((project_dir / 'manifest.json').read_text())
    all_scenes = manifest.get('scenes') or []
    if not all_scenes:
        raise ExportError('매니페스트에 씬이 없음')
    fps = int(manifest.get('fps') or 30)
    first, end = parse_scenes(scenes, len(all_scenes))
    plan = Plan(project_dir, out_dir, width, height)
    picked = all_scenes[first:end]
    t0 = float(picked[0]['start'])
    # 씬 경계: 다음 씬의 시작(마지막 씬은 자기 길이)
    bounds = [round((float(s['start']) - t0) * fps) for s in picked]
    last = picked[-1]
    after = all_scenes[end]['start'] if end < len(all_scenes) else float(last['start']) + float(last['duration'])
    bounds.append(round((float(after) - t0) * fps))

    clips, max_layers = [], 1
    for i, s in enumerate(picked):
        got, used = scene_clips(plan, s, first + i, bounds[i], bounds[i + 1] - bounds[i], fps)
        clips += got
        max_layers = max(max_layers, used)
    tracks = [{'id': 'T2', 'kind': 'subtitle', 'name': '제목'}, {'id': 'T1', 'kind': 'subtitle', 'name': '자막'}]
    tracks += [{'id': f'V{n}', 'kind': 'video'} for n in range(max_layers, 0, -1)]
    tracks += [{'id': 'A1', 'kind': 'audio', 'name': '음성'}]
    background = (manifest.get('themeColors') or {}).get('bg') or '#000000'
    timeline = {'fps': fps, 'sequence': {'width': width, 'height': height, 'background': background},
                'tracks': tracks, 'clips': clips}
    result = {'project': project_dir.name, 'scenes': [first + 1, end], 'frames': bounds[-1],
              'files': plan.files, 'timeline': timeline}
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / 'plan.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def read_map(path):
    """'<파일 이름> <timeline_asset>' 줄들 → dict. 빈 줄·# 줄은 건너뛴다."""
    out = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.rsplit(None, 1)
        if len(parts) != 2:
            raise ExportError(f'map 줄을 읽을 수 없음: {line}')
        out[parts[0]] = parts[1]
    return out


def finalize(out_dir, map_path=None):
    """plan.json 의 '@file:' 자리를 map 으로 채워 timeline.json 을 쓴다."""
    out_dir = Path(out_dir)
    plan = json.loads((out_dir / 'plan.json').read_text())
    mapping = read_map(map_path or out_dir / 'map.txt')
    missing = sorted(n for n in plan['files'] if n not in mapping)
    if missing:
        raise ExportError('map 에 없는 파일: ' + ', '.join(missing))
    timeline = plan['timeline']
    for clip in timeline['clips']:
        asset = clip.get('asset')
        if isinstance(asset, str) and asset.startswith(PLACEHOLDER):
            clip['asset'] = mapping[asset[len(PLACEHOLDER):]]
    (out_dir / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False))
    return timeline


def main(argv=None):
    ap = argparse.ArgumentParser(description='애프터이펙트 매니페스트 → 카이로스 타임라인')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='올릴 파일과 타임라인 초안(plan.json)을 만든다')
    p.add_argument('project_dir', help='편의 output 폴더(manifest.json 이 있는 곳)')
    p.add_argument('--out', required=True, help='결과를 쓸 폴더')
    p.add_argument('--scenes', default='all', help="씬 범위 '1-6'(1부터 셈) 또는 all")
    p.add_argument('--size', default='1920x1080', help='화면 크기 (기본 1920x1080)')
    f = sub.add_parser('finalize', help='map.txt 로 에셋 자리를 채워 timeline.json 을 쓴다')
    f.add_argument('out', help='plan 이 쓴 폴더')
    f.add_argument('--map', help='기본 <out>/map.txt')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'plan':
            w, h = (int(x) for x in a.size.lower().split('x'))
            res = build_plan(a.project_dir, a.out, a.scenes, w, h)
            tl = res['timeline']
            print(f"씬 {res['scenes'][0]}~{res['scenes'][1]}  {res['frames']}프레임({res['frames'] / tl['fps']:.1f}초)  "
                  f"파일 {len(res['files'])}개 {sum(x['bytes'] for x in res['files'].values()) / 1e6:.1f}MB  "
                  f"클립 {len(tl['clips'])}개  트랙 {len(tl['tracks'])}개")
            print(f"타임라인 JSON {len(json.dumps(tl, ensure_ascii=False)) / 1024:.0f}KB → {Path(a.out) / 'plan.json'}")
        else:
            tl = finalize(a.out, a.map)
            print(f"클립 {len(tl['clips'])}개 → {Path(a.out) / 'timeline.json'}")
    except ExportError as e:
        print(f'오류: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
