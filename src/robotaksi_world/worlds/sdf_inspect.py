#!/usr/bin/env python3
"""
sdf_inspect.py — turn a flat SDF world file into something queryable.

Usage:
    python3 sdf_inspect.py world.sdf summary
    python3 sdf_inspect.py world.sdf list [name_substring]
    python3 sdf_inspect.py world.sdf overlaps
    python3 sdf_inspect.py world.sdf near X Y [radius]
    python3 sdf_inspect.py world.sdf bbox name1 [name2 ...]

Design notes:
- Every <model> with a <pose> and a box/cylinder geometry becomes one row.
- Rows are grouped by a "category" guessed from the name prefix
  (durak_, B, edge_, dc/dh, rot_, park_, arr_, perim_, conn_, stub_...).
  This is the single biggest troubleshooting lever: most bugs are
  "category A collided with category B" (e.g. road vs bus stop).
"""
import re, sys, math
from dataclasses import dataclass, field

@dataclass
class Obj:
    name: str
    x: float; y: float; z: float
    shape: str           # "box" or "cylinder"
    sx: float = 0; sy: float = 0; sz: float = 0   # for box
    radius: float = 0; length: float = 0          # for cylinder
    category: str = ""

    @property
    def bbox(self):
        if self.shape == "box":
            return (self.x - self.sx/2, self.x + self.sx/2,
                    self.y - self.sy/2, self.y + self.sy/2)
        else:  # cylinder -> square bbox approximation
            return (self.x - self.radius, self.x + self.radius,
                    self.y - self.radius, self.y + self.radius)

MODEL_RE = re.compile(
    r'<model name="([^"]+)">.*?<pose>([\d.\-eE]+)\s+([\d.\-eE]+)\s+([\d.\-eE]+)[^<]*</pose>.*?'
    r'<geometry>\s*<(box|cylinder)>(.*?)</\5>',
    re.DOTALL
)
BOX_SIZE_RE = re.compile(r'<size>([\d.\-eE]+)\s+([\d.\-eE]+)\s+([\d.\-eE]+)</size>')
CYL_RE = re.compile(r'<radius>([\d.\-eE]+)</radius>.*?<length>([\d.\-eE]+)</length>', re.DOTALL)

CATEGORY_RULES = [
    (r'^durak', 'bus_stop'),
    (r'^B\d', 'building'),
    (r'^park_', 'parking'),
    (r'^rotonda|^rot_', 'roundabout'),
    (r'^tunel_', 'tunnel'),
    (r'^edge_', 'road_edge_line'),
    (r'^dc\d|^dh\d', 'lane_centerline'),
    (r'^arr_', 'lane_arrow'),
    (r'^stop_', 'stop_line'),
    (r'^perim_', 'perimeter_road'),
    (r'^conn_', 'connector_road'),
    (r'^stub_', 'connector_road'),
    (r'^gorev_|^statik_engel', 'gameplay_marker'),
    (r'^ana_zemin', 'ground'),
    (r'^sokak_l_', 'streetlight'),
]

def categorize(name):
    for pat, cat in CATEGORY_RULES:
        if re.match(pat, name):
            return cat
    return 'other'

def parse(path):
    text = open(path, encoding='utf-8').read()
    objs = []
    for m in MODEL_RE.finditer(text):
        name, x, y, z, shape, body = m.groups()
        o = Obj(name=name, x=float(x), y=float(y), z=float(z), shape=shape)
        if shape == 'box':
            bm = BOX_SIZE_RE.search(body)
            if not bm:
                continue
            o.sx, o.sy, o.sz = (float(v) for v in bm.groups())
        else:
            cm = CYL_RE.search(body)
            if not cm:
                continue
            o.radius, o.length = (float(v) for v in cm.groups())
        o.category = categorize(name)
        objs.append(o)
    return objs

def overlap_1d(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1

def boxes_overlap(b1, b2):
    return overlap_1d(b1[0], b1[1], b2[0], b2[1]) and overlap_1d(b1[2], b1[3], b2[2], b2[3])

def cmd_summary(objs):
    from collections import Counter
    c = Counter(o.category for o in objs)
    print(f"{'CATEGORY':<20}{'COUNT':>6}")
    print("-" * 26)
    for cat, n in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"{cat:<20}{n:>6}")
    print("-" * 26)
    print(f"{'TOTAL':<20}{len(objs):>6}")

def cmd_list(objs, substr=None):
    rows = [o for o in objs if not substr or substr.lower() in o.name.lower()]
    for o in rows:
        bb = o.bbox
        print(f"{o.name:<22} [{o.category:<16}] x[{bb[0]:7.2f},{bb[1]:7.2f}] y[{bb[2]:7.2f},{bb[3]:7.2f}]")
    print(f"\n{len(rows)} matching rows")

def cmd_overlaps(objs, only_cross_category=True, ignore_pairs=None):
    """Report every pair of objects whose footprints overlap.
    Skips same-category pairs by default (e.g. two lane-line dashes
    overlapping is expected/harmless); flip only_cross_category=False
    to check everything."""
    ignore_pairs = ignore_pairs or set()
    n = len(objs)
    found = []
    for i in range(n):
        for j in range(i+1, n):
            a, b = objs[i], objs[j]
            if only_cross_category and a.category == b.category:
                continue
            if (a.category, b.category) in ignore_pairs or (b.category, a.category) in ignore_pairs:
                continue
            if boxes_overlap(a.bbox, b.bbox):
                found.append((a, b))
    if not found:
        print("No cross-category overlaps found.")
        return
    print(f"{len(found)} overlap(s) found:\n")
    for a, b in found:
        print(f"  {a.name} [{a.category}]  <-->  {b.name} [{b.category}]")

def cmd_near(objs, x, y, radius):
    hits = []
    for o in objs:
        d = math.hypot(o.x - x, o.y - y)
        if d <= radius:
            hits.append((d, o))
    hits.sort(key=lambda t: t[0])
    for d, o in hits:
        print(f"{d:6.2f}m  {o.name:<22} [{o.category}]  pose=({o.x:.2f},{o.y:.2f})")
    print(f"\n{len(hits)} objects within {radius}m of ({x},{y})")

def cmd_bbox(objs, names):
    found = [o for o in objs if o.name in names]
    if not found:
        print("none of those names matched")
        return
    x0 = min(o.bbox[0] for o in found)
    x1 = max(o.bbox[1] for o in found)
    y0 = min(o.bbox[2] for o in found)
    y1 = max(o.bbox[3] for o in found)
    print(f"Combined bounding box of {len(found)} object(s):")
    print(f"  x[{x0:.3f}, {x1:.3f}]  y[{y0:.3f}, {y1:.3f}]")
    print(f"  width={x1-x0:.3f}  height={y1-y0:.3f}  center=({(x0+x1)/2:.3f},{(y0+y1)/2:.3f})")

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    path, cmd = sys.argv[1], sys.argv[2]
    objs = parse(path)
    if cmd == 'summary':
        cmd_summary(objs)
    elif cmd == 'list':
        cmd_list(objs, sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == 'overlaps':
        cmd_overlaps(objs)
    elif cmd == 'near':
        x, y = float(sys.argv[3]), float(sys.argv[4])
        r = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
        cmd_near(objs, x, y, r)
    elif cmd == 'bbox':
        cmd_bbox(objs, sys.argv[3:])
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
