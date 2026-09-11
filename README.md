# fuzzy-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

Ranked substring matching, sans-IO: the scoring behind fzf and nucleo,
plus the classic string distances, over candidates the caller already
holds.

- `fuzzypat` — the needle compiled once, with fzf's extended search
  syntax and the smart-case rule resolved;
- `fuzzyscore` — the bonus table, the two scorers, a score without
  positions and positions on demand;
- `fuzzyrank` — a candidate list ordered, with a total order and fzf's
  tiebreaks;
- `fuzzydist` — Levenshtein, the two Damerau distances, Jaro-Winkler
  and the rapidfuzz ratios, each with a bounded form.

```
novo pkg add fuzzy-nv
novo pkg build
novo test
```

## The one example that will work

```novo ignore
use fuzzypat
use fuzzyrank

// A picker: one pattern per keystroke, the whole corpus per pattern.
fn pick(query: Str, paths: [Str]) -> [Int]
    let p = fuzzypat.literal(query, FuzzyCaseSmart)
    var out: [Int] = []
    for h in fuzzyrank.rank(p, paths, fuzzyrank.picker_options(40))
        out = list.push(out, h.index)
    out
```

## The load-bearing interface: `FuzzyPattern`

```novo ignore
pub struct FuzzyPattern
    source: Str
    terms: [FuzzyTerm]
    requested_case: FuzzyCase
    effective_case: FuzzyCase
```

The API a completion menu needs is "one needle, a hundred thousand
candidates, recomputed on every keystroke". The obvious signature —
`fn score(needle: Str, haystack: Str) -> Int` — redoes the needle's
work once per candidate: splitting it into terms, resolving smart case,
cutting it into the clusters the matcher advances over. A
`FuzzyPattern` is that done once.

The second thing the type buys is a **place to put fzf's query
language**. `'wild` is exact, `^music` a prefix, `.mp3$` a suffix,
`!fire` a negation, `a | b` an alternation inside one term, and terms
are ANDed. None of that fits in a two-string signature, so a library
shaped that way pushes it into every consumer — and every consumer
implements a different subset.

Smart case is resolved **when the pattern is compiled**, because it is
a property of the needle. That is faster, and it is the only way
`effective_case` can be a field a person can be shown when `Foo` stops
matching `foobar`.

## The second decision worth arguing: a score and its positions are two calls

`match_at` answers a score and the byte range the match covered.
`positions_of` answers where each matched cluster is, and allocates a
list to do it.

A picker over a repository scores every path on every keystroke and
paints forty rows. Folding the positions into the score makes a hundred
thousand allocations to paint forty lines, and that is the whole
difference between a picker that feels instant and one that does not.
fzf makes the same split — it scores in "no backtrace" mode and
recomputes positions for the visible window — and it is the single most
important thing to copy from it. `matches` is the third rung: the
`N of M` footer's denominator, answered by a scan with no alignment
searched for at all.

## Three more decisions the tests are about

**Every position is on a grapheme-cluster boundary.** The matcher
advances with `ugrapheme.next_boundary`, so an offset it answers is a
boundary by construction rather than by a check the caller has to
remember. A UI that inverts the matched bytes therefore never paints
half of a combining sequence or the middle of an emoji ZWJ run — which
is exactly what a byte-at-a-time matcher does, and which is invisible
in every ASCII test.

**The ranking order is total.** Score, then the caller's tiebreak, then
the candidate's index in the input, which is unique — so
`fuzzyrank.compare` is never zero for two different candidates. A
picker repaints on every keystroke, and two rows that swap places
between repaints mean a person presses Enter on the row they were
looking at and opens a different file.

**Every distance has a bounded form, and it is the one to use.**
`levenshtein_within(a, b, max)` stops as soon as the answer is known to
exceed `max`, which fills a band of width `2 * max + 1` instead of the
whole matrix. That is the question a did-you-mean actually asks, and
rapidfuzz's `score_cutoff` is the same idea — most of why rapidfuzz is
fast. Publishing only the unbounded form would be publishing the slow
half.

## Two scorers, and they disagree on purpose

`FuzzyScorerV2` is fzf's heuristic: one forward pass, linear in the
candidate, and it can answer a lower score than the best alignment
would. `FuzzyScorerExact` is the full Smith–Waterman-style dynamic
program: quadratic, always optimal. A picker uses the first; a test
asserting "this is the best possible match" uses the second, and so
does a caller ranking a short list. A package that shipped only the
heuristic could not be checked against the algorithm it approximates,
and `tests/fuzzyscore_tests.nv` asserts the exact scorer is never
worse.

## The bonus table is a value

Almost all of an fzf score is the bonus for **where** a match lands:
after a separator, at a camel-case boundary, at the start of the
basename, consecutive with the last match. Different corpora want
different weights, so `FuzzyBonus` is a struct a caller replaces, and
three named tables ship: `fzf_bonus()` is the reference
implementation's own numbers so a port can be checked rather than
tuned, `path_bonus()` raises the path separator for a file picker, and
`symbol_bonus()` raises camel case for a symbol picker.

`gap_start` and `gap_extend` are two fields rather than one because one
long gap should cost less than several short ones — that is what makes
a match inside one word beat a match scattered across three.

## `fuzzydist` is a different question, which is why it is a module

`fuzzyscore` answers "does this needle occur in this candidate, and how
well" — a subsequence question over a needle much shorter than its
haystack. `fuzzydist` answers "how far apart are these two strings" — a
symmetric question over two strings of similar length. A did-you-mean,
a spell checker's candidate filter and a deduplicator want the second;
a completion menu wants the first. Mixing them is how a picker ends up
ranking by edit distance and feeling wrong.

Both Damerau distances are named. `osa` is the optimal string alignment
distance, which forbids editing a substring twice; `damerau` is the
unrestricted one. `osa("ca", "abc")` is 3 and `damerau("ca", "abc")` is
2, and libraries routinely ship one under the other's name.

## The layer, and why

`core`. A match is arithmetic over two strings the caller already
holds: nothing is read, nothing is written, no clock is consulted, and
a ranking answers **indices** into the caller's own candidate list
rather than copies of the strings. Nothing in this package takes a
stream, so there is no effect-polymorphic function here — the
candidates arrive as a list a host produced.

## `@tier(embedded)` is not claimed

There is no device consumer, and the shape says so. A ranking holds one
result per matching candidate, a position list is allocated per
highlighted row, and the exact scorer fills a matrix the size of the
needle times the candidate. A firmware that wanted to match six command
names would want a fixed-capacity variant with a different surface, not
this one with a tier annotation on it. The honest form is the absence
of the claim.

## The reference implementation

fzf's `src/algo/algo.go` is the reference for the scoring: the bonus
constants, `FuzzyMatchV2`'s forward pass, the no-backtrace mode that
justifies the score/positions split, and the smart-case rule. `man
fzf`'s SEARCH SYNTAX table is the specification for `fuzzypat.parse`,
and fzf's `--tiebreak` is `FuzzyTie`. nucleo is the second reading,
and where the two differ the tests say which one this package follows —
nucleo takes a dangling `|` as a literal and this package refuses it,
because a query is something a person is typing and a silent
reinterpretation is worse than a message under the cursor.

`fuzzydist`'s vectors are the published ones: `kitten`/`sitting` for
Levenshtein, `MARTHA`/`MARHTA` for Jaro-Winkler, `ca`/`abc` for the two
Damerau distances, and rapidfuzz's own values for the four ratios.

## Dependencies

`unicode-nv ^0.0.1`, for two things, and both are correctness rather
than completeness.

The bonus table **classifies characters**, and deciding "the previous
character was lower-case and this one is upper-case" in ASCII gets
German, Greek and Cyrillic camel case wrong — which is exactly where a
symbol picker over a codebase with non-English identifiers shows it.
`uclass`'s predicates take a codepoint and no data table, so the cost
is a branch.

A **position is always on a cluster boundary**, via
`ugrapheme.next_boundary`, and `fuzzyscore.matched_clusters` answers
unicode-nv's own `UniCluster` values so the signature says so rather
than implying it.

Full Unicode case folding is deliberately *not* taken: `ucase.fold`
needs the 245 KB case table, and a completion menu should not carry it
to compare two ASCII paths. A caller who wants it folds its candidates
and its needle itself; fzf's own default is the same (`--literal`).

## The consumers, and what adopting this would take

**novim** (`orbit/novim`) is the consumer this package is measured
against. `src/fuzzy.nv` is 137 lines and three functions — `score`,
`rank`, `match_count` — driven by the picker overlay in `src/main.nv`
for `:files`, `:grep`, `:bufs` and `:pins`. Adopting fuzzy-nv deletes
that file. Four things it would gain, and each is something the
existing code cannot do rather than something it does slowly:

| | novim's `fuzzy.nv` | fuzzy-nv |
| --- | --- | --- |
| highlighting | no positions at all | `positions_of`, on cluster boundaries |
| query syntax | a bare subsequence | fzf's terms, negations and alternations |
| case | ASCII fold, always | smart case, resolved and readable |
| bonuses | five constants in the body | a value, with three named tables |
| `N of M` footer | a second full pass (`match_count`) | `count_matches`, no alignment searched |
| ties | producer order, hard-coded | `FuzzyTie`, with the index as the final step |

The module names do not collide: novim keeps `src/fuzzy.nv` while this
package ships `fuzzypat`, `fuzzyscore`, `fuzzyrank` and `fuzzydist`, so
the adoption can be done one call site at a time. Its ranking semantics
already match — novim's merge sort takes from the left on a tie, which
is `FuzzyTieIndex`, and its comment says so.

**novoterm** and **novomux** have no picker today; a command palette
over either is `fuzzyrank.rank` over a list of command names.

**`std.cli`** is the other consumer, for a different module: a
did-you-mean over subcommand names when a user mistypes one is
`fuzzydist.nearest(typed, names, 2, 3)`, which is the bounded distance
and one call.

## What a row wanted to widen

Nothing. Every function here is `[]`.

Two things the plan's row did not anticipate, both recorded because
they are the redesign input rather than problems:

**The row says "ranked substring matching for command-line
completion", and that is one of the two questions in this package.**
The distances are the other, and they are not substring matching at
all. Keeping them here rather than in a package of their own is the
right call — a did-you-mean and a completion menu are the same
feature's two halves, and splitting them would make the second package
depend on nothing and be imported beside the first every time — but the
module boundary is doing the work the package boundary would have, and
the README says which module answers which question.

**A full-Unicode matcher would need `UniData` in every signature.**
`ucase.fold` and `unorm.normalize` both take the 245 KB table as an
argument, so an accent-insensitive match (nucleo's `--normalize`) would
put a `UniData` parameter on `match_at`, `positions_of`, `rank` and
every option constructor. That is a real cost for a feature fzf itself
does not enable by default, so it is not in this interface; if the
implementation lane wants it, the shape to add is one
`fuzzypat.compile_folded(needle, d: UniData)` that folds the needle
once and a `FuzzyPattern` field saying the candidates must be folded
too — not a parameter on the hot path.

## The surface

| module | `pub fn` | `pub struct` | `pub enum` |
| --- | --- | --- | --- |
| `fuzzypat` | 10 | 3 | 3 |
| `fuzzyscore` | 13 | 2 | 1 |
| `fuzzyrank` | 9 | 2 | 1 |
| `fuzzydist` | 18 | 0 | 0 |
| **total** | **50** | **7** | **5** |
