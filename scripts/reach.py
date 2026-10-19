"""usage: python3 -I scripts/reach.py <graph.json> <root_comp_id> [t0 t1] > reach.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.graph import reach_items

g = json.load(open(sys.argv[1]))
root = sys.argv[2]
t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else tuple(g["comps"][root]["wa"])
json.dump(reach_items(g, root, t0, t1), sys.stdout, ensure_ascii=False, indent=1)
