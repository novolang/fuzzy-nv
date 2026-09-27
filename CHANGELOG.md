# Changelog

All notable changes to fuzzy-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.0 — 2026-09-27

The first implementation of the interface published as 0.0.1: fzf's
query syntax and score, a fast scorer and an exact one, positions on
cluster boundaries, a total ranking, and the classic distances.

### Changed, breaking

- `FuzzyPatternUnclosedQuote` is gone.  fzf's `'wild` is a complete
  exact atom with no closing quote, so the variant could never be
  produced.  A quote with nothing after it is
  `FuzzyPatternDanglingSigil`, like `!`, `^` and `$`.
- `fuzzyscore.positions_into` and `fuzzyrank.rank_into` take their
  first argument as `var out`.  Under 0.13.0's list rule a function
  writes into a caller's list only through a `var` parameter, and the
  caller passes a `var` list.
- `!fire` is a literal negation, as in fzf's table, where the
  interface's tests read it as a fuzzy one.  `!'fire` is the fuzzy
  negation.

### Behaviour the interface left open

- The score is fzf's `calculateScore` with fzf's constants.  The start
  of the text and whitespace earn `first`, a word after `/` earns
  `path`, a word after any other non-word character earns `boundary`,
  and an upper-case letter after a lower-case one, or a digit after a
  non-digit, earns `camel`.  fzf gives its delimiters `, : ; |` the
  path value, and this table gives them `boundary`.
- `FuzzyScorerV2` is fzf's forward and backward scan.
  `FuzzyScorerExact` is a dynamic program over the needle's clusters,
  the candidate's clusters and the length of the current run, and
  answers the best alignment under the same model.
- A term's score is its best-scoring positive atom.  A term satisfied
  only by a negated atom adds nothing.  A pattern that matched without
  scoring answers a score, a start and an end of 0.
- A literal atom keeps its best-scoring occurrence, so `'main` in
  `domain/main.nv` highlights the path component.
- A pattern that is empty or all negated ranks in the input's order
  whatever the tiebreak, which is fzf's rule for a query it cannot
  sort.  `best` answers the first result `rank` would.
- `FuzzyTieLength` compares byte lengths.
- Ignoring case compares the simple lowercase mappings of ASCII,
  Latin-1, Latin Extended-A, Latin Extended Additional, the basic Greek
  letters and the Cyrillic block with its supplement, with no data
  table.  `FuzzyCaseSmart` passed straight to `chars_equal` ignores
  case.
- `fuzzypat` gains `CLASS_WORD`, `CLASS_SEPARATOR` and `CLASS_OTHER`,
  the three answers of `char_class`.
- `max_score` is a ceiling, every cluster matched with the table's
  largest bonus, rather than a score some candidate reaches.
- `jaro_winkler_with` applies the prefix bonus only above a Jaro
  similarity of 0.7, Winkler's threshold.  `jaro` counts half the
  mismatched matches, rounded down, as transpositions.
- `token_set_ratio` answers 0.0 for a string with no tokens, as
  rapidfuzz does.
- `nearest` takes a `limit` of 0 as no limit.

### Tests

- 43 tests in five suites.  Hand-worked scores from fzf's constants; a
  brute force over every alignment of three hundred generated pairs as
  the oracle for the exact scorer; Python's `str.lower` over every
  codepoint of the claimed case ranges; and two hundred generated
  pairs whose distances `tools/gen_dist_vectors.py` computes with the
  textbook algorithms and `difflib`.
- Every line under `src/` is executed by the suites;
  `bash tests/coverage.sh` prints the number.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

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

### Design notes

The consumer the surface was measured against is novim, whose
`src/fuzzy.nv` is 137 lines and three functions driving the picker
overlay for `:files`, `:grep`, `:bufs` and `:pins`. Adopting this
package deletes that file and adds highlight positions, fzf's query
syntax, smart case, a replaceable bonus table, a footer count with no
alignment searched, and a total order with the input index as the final
step. The module names do not collide, so the adoption can go one call
site at a time. A command palette over novoterm or novomux is
`fuzzyrank.rank` over a list of command names, and `std.cli`'s
did-you-mean over subcommand names is `fuzzydist.nearest`.

Two questions in one package. `fuzzyscore` answers whether a short
needle occurs in a longer candidate and how well. `fuzzydist` answers
how far apart two strings of similar length are. They stay together
because a did-you-mean and a completion menu are two halves of one
feature, and the module boundary carries the distinction.

Accent-insensitive matching was considered and left out. `ucase.fold`
and `unorm.normalize` both take the 245 KB table as an argument, so it
would put a `UniData` parameter on `match_at`, `positions_of`, `rank`
and every option constructor. The shape to add later is one
`fuzzypat.compile_folded(needle, d: UniData)` that folds the needle
once, plus a `FuzzyPattern` field saying the candidates must be folded
too, rather than a parameter on the hot path.
