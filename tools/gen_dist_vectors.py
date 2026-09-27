#!/usr/bin/env python3
"""Write the distance vectors in tests/fuzzydist_vectors_tests.nv.

Every distance is computed here by the textbook algorithm, over ASCII
strings drawn from a small alphabet so that repeats and transpositions
are common, and the difflib ratio comes from Python's standard library.
Run it from the package root:  python3 tools/gen_dist_vectors.py
The output is the same on every run, since the generator is seeded.
"""
import difflib, random

def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j - 1] + (x != y), prev[j] + 1, cur[j - 1] + 1))
        prev = cur
    return prev[-1]

def osa(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1): d[i][0] = i
    for j in range(len(b) + 1): d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]

def damerau(a, b):
    # Lowrance and Wagner, as on Wikipedia's "Damerau-Levenshtein distance".
    da = {}
    maxdist = len(a) + len(b)
    d = [[0] * (len(b) + 2) for _ in range(len(a) + 2)]
    d[0][0] = maxdist
    for i in range(len(a) + 1):
        d[i + 1][0] = maxdist; d[i + 1][1] = i
    for j in range(len(b) + 1):
        d[0][j + 1] = maxdist; d[1][j + 1] = j
    for i in range(1, len(a) + 1):
        db = 0
        for j in range(1, len(b) + 1):
            k = da.get(b[j - 1], 0); l = db
            cost = 0 if a[i - 1] == b[j - 1] else 1
            if cost == 0: db = j
            d[i + 1][j + 1] = min(d[i][j] + cost, d[i + 1][j] + 1, d[i][j + 1] + 1,
                                  d[k][l] + (i - k - 1) + 1 + (j - l - 1))
        da[a[i - 1]] = i
    return d[-1][-1]

def lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]

def jaro(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    w = max(max(len(a), len(b)) // 2 - 1, 0)
    taken = [False] * len(b); ma = []
    for i, x in enumerate(a):
        for j in range(max(0, i - w), min(len(b), i + w + 1)):
            if not taken[j] and b[j] == x:
                taken[j] = True; ma.append(x); break
    m = len(ma)
    if m == 0: return 0.0
    mb = [b[j] for j in range(len(b)) if taken[j]]
    t = sum(1 for x, y in zip(ma, mb) if x != y) // 2
    return (m / len(a) + m / len(b) + (m - t) / m) / 3

def jw(a, b):
    j = jaro(a, b)
    if j <= 0.7: return j
    p = 0
    while p < 4 and p < len(a) and p < len(b) and a[p] == b[p]: p += 1
    return j + p * 0.1 * (1 - j)

def ratio(a, b):
    t = len(a) + len(b)
    return 1.0 if t == 0 else 1 - (t - 2 * lcs(a, b)) / t

rng = random.Random(20260927)
rows = []
for _ in range(200):
    a = "".join(rng.choice("abcab ") for _ in range(rng.randint(0, 9)))
    b = "".join(rng.choice("abcab ") for _ in range(rng.randint(0, 9)))
    dl = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    rows.append((a, b, lev(a, b), osa(a, b), damerau(a, b), lcs(a, b),
                 jaro(a, b), jw(a, b), ratio(a, b), dl))

out = []
for r in rows:
    out.append('        "%s|%s|%d|%d|%d|%d|%.17g|%.17g|%.17g|%.17g",' % r)
out[-1] = out[-1].rstrip(',')
# The list is written the way `novo fmt` lays it out, closing bracket on
# the last line, so a regenerated file is already canonical.
marker = 'fn vectors() -> [Str]\n    [\n'
body = open('tests/fuzzydist_vectors_tests.nv').read()
start = body.index(marker) + len(marker)
end = body.index(']\n\n@test', start)
open('tests/fuzzydist_vectors_tests.nv', 'w').write(body[:start] + "\n".join(out) + body[end:])
