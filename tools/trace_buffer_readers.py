"""Find later bound readers of one shader's placed UAV in a VIctory diagnostic log.

Only compares title addresses on the same frame and strictly later submissions.
Markers show bindings, not actual GPU memory accesses or resource lifetimes.
"""

import argparse
import re
from pathlib import Path


def markers(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    for event in re.split(r'(?m)(?=^\d{4}-\d\d-\d\dT)', text):
        tag = re.search(r'(wait neighbor|writer event): (.*) frame=(\d+) submission=(\d+)', event, re.S)
        if tag:
            yield tag[1], tag[2], int(tag[3]), int(tag[4])


def inputs(op):
    # A placed buffer table entry gives the enclosing resource, not the view's
    # effective FirstElement and element count. An overlap here is a candidate only.
    for shader, slot, width, base in re.findall(
        r'([a-f0-9]{16}) Srv (s\d+\+\d+): placed uav=false dim 1 (\d+)x1 f\d+ layout 0x[0-9a-f]+ at (0x[0-9a-f]+)', op
    ):
        yield int(base, 16), int(width), f'{shader} Srv {slot} (enclosing buffer)'
    for index, base, size in re.findall(
        r'\[heap (\d+): (?:Placed\(false|Shader\()(?:(?!\[heap |\|).)*? title (0x[0-9a-f]+)\+(0x[0-9a-f]+) host', op, re.S
    ):
        yield int(base, 16), int(size, 16), f'heap {index} (possible SRV from user data)'
    for shader, kind, slot, base, size in re.findall(
        r'([a-f0-9]{16}) (Srv|Cbv) (s\d+\+\d+): (?:buffer Some\(\((\d+), (\d+)\)\))', op
    ):
        yield int(base), int(size), f'{shader} {kind} {slot}'
    for shader, slot, base, size in re.findall(
        r'([a-f0-9]{16}) Cbv (s\d+\+\d+): Constant\((0x[0-9a-f]+|\d+), (\d+)\)', op
    ):
        yield int(base, 0), int(size), f'{shader} Cbv {slot}'
    arg = re.match(r'indirect kind \d+ max [1-9]\d* at (0x[0-9a-f]+) (\[[^\]]+\])', op)
    if arg:
        yield int(arg[1], 16), 1, f'{arg[2]} indirect argument start'
    for slot, base in re.findall(r'\broot(\d+)=(0x[0-9a-f]+) host', op):
        yield int(base, 16), 1, f'root {slot} start'


def compare(text, frame, shader):
    events = [(tag, op, sub) for tag, op, f, sub in markers(text) if f == frame]
    readers = [(sub, base, size, label) for tag, op, sub in events if tag == 'writer event'
               for base, size, label in inputs(op)]
    results = []
    for tag, op, sub in events:
        if tag != 'wait neighbor' or not op.startswith('dispatch ') or f'[compute {shader}]' not in op:
            continue
        for base, size in re.findall(r'\[heap \d+: Placed\(true,(?:(?!\[heap |\|).)*? title (0x[0-9a-f]+)\+(0x[0-9a-f]+)', op, re.S):
            lo, length = int(base, 16), int(size, 16)
            hit = next(((s, label, min(lo+length, b+n)-max(lo, b)) for s, b, n, label in readers
                        if s > sub and max(lo, b) < min(lo+length, b+n)), None)
            results.append((sub, lo, length, hit))
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', type=Path)
    p.add_argument('--frame', type=int, required=True)
    p.add_argument('--shader', default='91b10a73e48b2192')
    args = p.parse_args()
    for sub, base, size, hit in compare(args.log.read_text(encoding='utf-8'), args.frame, args.shader):
        print(f'{sub}: {base:#x}+{size:#x}: first recorded overlap: {hit}')
