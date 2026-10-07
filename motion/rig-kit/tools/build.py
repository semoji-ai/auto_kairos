#!/usr/bin/env python3
"""Concatenate the engine and one story file into a single self-contained HTML page.
   python3 tools/build.py my_story.js [out.html]      -> page with step(dt) / renderAt(t) / DUR / NARR
   python3 tools/build.py --engine-only out.html      -> engine without a story (sheets, probes)"""
import sys, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: open(os.path.join(root, p), encoding='utf-8').read()
HEAD = '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#F3EFE6}canvas{display:block}</style></head><body>\n<canvas id="cv"></canvas>\n<script>\n'
parts = [rd('engine/base.js'), rd('engine/rig360.js'), rd('engine/stage.js'), rd('engine/look.js'), rd('engine/ctl.js'), rd('engine/props.js')]
if sys.argv[1] == '--engine-only':
    out = sys.argv[2]
else:
    story = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(story)[0] + '.html'
    parts += [open(story, encoding='utf-8').read(), rd('engine/seq.js')]
open(out, 'w', encoding='utf-8').write(HEAD + '\n'.join(parts) + '\n</script></body></html>\n')
print('built', out)
