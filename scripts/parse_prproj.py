"""usage: python3 -I scripts/parse_prproj.py <file.prproj> > timeline.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.prproj import parse

json.dump(parse(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=1)
