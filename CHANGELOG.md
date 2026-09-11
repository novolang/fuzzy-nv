# Changelog

All notable changes to fuzzy-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.0.1 — 2026-09-11

The **interface**: every signature and every effect row, and no bodies.
`stability = "draft"`, and the release is recorded `implemented = false`.

### Added

- `fuzzypat` — `FuzzyPattern`, the needle compiled once, with fzf's
  extended search syntax as two levels (alternation inside a term,
  conjunction between them) and smart case resolved at compile time
  into a field a person can be shown.
- `fuzzyscore` — `FuzzyBonus` as a value with three named tables, the
  fzf v2 heuristic and the exact dynamic program as two scorers, and
  the score/positions split.
- `fuzzyrank` — a total order: score, tiebreak, then the input index,
  so `compare` is never zero for two different candidates.
- `fuzzydist` — Levenshtein, the two Damerau distances under their own
  names, Jaro-Winkler with Winkler's constants, and the four rapidfuzz
  ratios — each with a bounded form.

### Known

- **`FuzzyPattern` is the load-bearing interface.** A two-string
  `score(needle, haystack)` redoes the needle's work per candidate and
  has nowhere to put a query language.
- **A score and its positions are two calls.** Folding them makes a
  hundred thousand allocations to paint forty rows.
- **Every position is on a grapheme-cluster boundary**, by
  construction rather than by a check, so a highlight never paints half
  a character.
- **The ranking order is total**, because a picker that reorders equal
  scores between repaints opens the wrong file.
- **Every distance has a bounded form**, which is most of why rapidfuzz
  is fast; the unbounded one alone would be the slow half.
- **`@tier(embedded)` is not claimed** — there is no device consumer,
  and a ranking, a position list and the exact scorer's matrix all
  scale with the input.
- **One dependency**, `unicode-nv`, for the character classes the bonus
  table needs and the cluster boundaries the positions sit on. Full
  case folding is deliberately not taken: it needs the 245 KB case
  table, and fzf's own default is `--literal`.
