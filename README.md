# fuzzy-nv

Fuzzy matching is what a completion menu does when it accepts `mn` for
`src/main.nv`: the letters of the needle appear in the candidate in
order, but not next to each other. The reference implementation is
[fzf](https://github.com/junegunn/fzf), whose scoring and query syntax
this package follows.
The package also carries the classic string distances, which answer a
different question, in a module of their own. It is built on
[unicode-nv](https://novo-lang.org/packages/unicode-nv).

## What it is

The **needle** is what the user typed. A **candidate** is one of the
strings being searched, and the whole list of them is the **corpus**. A
match is a **subsequence**: every cluster of the needle occurs in the
candidate, in order, with anything in between.

Many alignments usually satisfy that, so a match is **scored** and the
best alignment wins. Almost all of the score is about where the matched
clusters land. A cluster that continues the previous match, that starts
a word, that begins a path component, or that is the capital letter of
a camel-case name is worth more than one in the middle of a word. The
unmatched clusters between matches are a **gap**, and a gap costs.

The **positions** of a match are the byte offsets of the matched
clusters. A user interface needs them to highlight; a ranking pass does
not.

A **pattern** is a needle compiled. fzf's query language puts several
demands in one query, and the pattern holds them: `'wild` must occur
literally, `^music` at the start, `.mp3$` at the end, `!fire` must not
occur literally, and `png | jpg` is satisfied by either. Terms separated by
spaces must all be satisfied.

**Smart case** means ignore case unless the needle contains an
uppercase letter. It is a property of the needle, so it is decided once
when the pattern is compiled.

A **string distance** is the other question. It is how many single-
character edits turn one string into the other, and it is symmetric
over two strings of similar length. Levenshtein counts insertions,
deletions and substitutions. The two Damerau variants also count the
transposition of two adjacent characters. Jaro and Jaro-Winkler answer
a similarity between 0.0 and 1.0 instead of a count. A "did you mean"
wants these; a completion menu wants the scoring above.

## Install

```
novo pkg add fuzzy-nv
```

## Example

```novo
use fuzzypat
use fuzzyscore
use fuzzyrank

fn main() [io]
    let paths = ["src/main.nv", "docs/manual.md", "src/internal/io.nv"]

    // Compile the needle once. Every candidate is matched against
    // this one value, so a keystroke costs one compile and not one
    // per candidate.
    let pattern = fuzzypat.literal("mn", FuzzyCaseSmart)

    // Score the whole list and keep the best ten, already ordered.
    for hit in fuzzyrank.rank(pattern, paths, fuzzyrank.picker_options(10))
        // `index` points back into the caller's own candidate list.
        println(str.from_int(hit.index))

    // Ask for the highlight offsets only for the row being painted.
    // Every offset is a grapheme-cluster boundary.
    for at in fuzzyscore.positions_of(pattern, "src/main.nv",
                                      fuzzyscore.path_bonus(), FuzzyScorerV2)
        println(str.from_int(at))
```

## What the package contains

| Module | Contents |
| --- | --- |
| `fuzzypat` | The needle compiled into a pattern, fzf's query syntax, and the case rule resolved. |
| `fuzzyscore` | The bonus table, the two scorers, a score without positions, and the positions on demand. |
| `fuzzyrank` | A candidate list ordered by score, with the tiebreaks and a limit. |
| `fuzzydist` | Levenshtein, the two Damerau distances, Jaro-Winkler and the rapidfuzz ratios, each with a bounded form. |

## How to choose an entry point

**`fuzzypat.literal` compiles a plain needle and cannot fail.**
`fuzzypat.parse` compiles a query in fzf's syntax and answers a
`Result`, because a query is something a person is typing and a
malformed one has a position to report.

**`fuzzyrank.rank` is the whole of what a picker needs.** It scores
every candidate, drops the ones below the cutoff, orders the rest and
returns at most `limit` of them. `rank_into` appends to a list you
already hold, for a picker that repaints on every keystroke.

**`fuzzyscore.match_at` scores one candidate and keeps no positions.**
It answers a score and the byte range the match covered.

**`fuzzyscore.positions_of` allocates, and is for the visible rows
only.** See rule 2.

**`fuzzyscore.matches` searches for no alignment at all.** It answers
only whether the candidate satisfies the pattern. `fuzzyrank.count_matches`
is the same scan over a whole corpus, which is the denominator of an
`N of M` footer.

**`fuzzydist.nearest` is a "did you mean" in one call.** It takes the
mistyped word, the candidate names, the largest distance worth
reporting and how many to return.

**Use the bounded distance functions.** `levenshtein_within` and
`osa_within` answer `None` as soon as the distance is known to exceed
the bound, filling a band rather than the whole matrix. The unbounded
forms are there for a caller that genuinely wants the number.

## The rules a user needs

1. **Compile the pattern once per needle, not once per candidate.**
   `FuzzyPattern` holds the terms, the atoms and the resolved case
   rule. A picker over a hundred thousand paths compiles one pattern
   per keystroke.
2. **A score and its positions are two calls.** `match_at` builds no
   position list. `positions_of` allocates one. fzf makes the same split,
   scoring in its no-backtrace mode and recomputing positions for the
   visible window only. Folding them together means a hundred thousand
   allocations to paint forty rows.
3. **A score is comparable only between matches of the same pattern
   against the same bonus table.** Nothing normalises it to a 0 to 1
   range, because a normalised number would look comparable across
   patterns and would not be.
4. **Every position is on a grapheme-cluster boundary.** The matcher
   advances by [UAX #29](https://www.unicode.org/reports/tr29/) cluster
   boundaries, so inverting the bytes from one offset to the next
   boundary paints exactly one character. A byte-at-a-time matcher
   paints half a combining sequence, and no ASCII test shows it.
   `fuzzyscore.matched_clusters` answers unicode-nv's own `UniCluster`
   values.
5. **The ranking order is total.** `fuzzyrank.compare` breaks a tie on
   the chosen `FuzzyTie` and then on the candidate's index in the input
   list, which is unique. It is therefore never zero for two different
   candidates. A picker whose equal scores reorder between repaints
   makes a person press Enter on the wrong row.
6. **`FuzzyBonus` is a value you can replace.** `fzf_bonus()` is the
   reference implementation's own numbers, so a port can be checked
   rather than tuned. `path_bonus()` raises the path separator for a
   file picker. `symbol_bonus()` raises camel case for a symbol picker.
7. **`gap_start` and `gap_extend` are two fields, and both are
   negative.** One long gap costs less than several short ones, which
   is what makes a match inside one word beat a match scattered across
   three.
8. **The two scorers disagree, and that is what they are for.**
   `FuzzyScorerV2` is fzf's fast algorithm: a forward scan and a
   backward scan, linear in the candidate, and it can answer less than
   the best alignment would. For `fzy` in `src/fuzzy.nv` it matches the
   first `z` and scores 60, where the best alignment takes the second
   and scores 66. `FuzzyScorerExact` searches every alignment and always
   answers the best. Its table grows with the needle's length squared
   times the candidate's. A picker uses the first. A test asserting that
   something is the best possible match uses the second.
9. **A negated atom contributes no score and no positions.** `!fire` is
   a filter, and it is literal: a candidate is dropped when it contains
   `fire`. `!'fire` drops a candidate that contains it as a
   subsequence. A pattern whose atoms are all negated highlights
   nothing, scores every candidate 0, and ranks them in the order they
   were given. `fuzzypat.is_filter_only` reports that case.
10. **Alternation is inside a term and conjunction is between terms.**
    fzf writes them `a | b` and `a b`. Two levels rather than one,
    because `(png | jpg) !thumb` is a query people type and a flat list
    cannot hold it.
11. **`smart_case` never appears in `effective_case`.** The resolved
    value is readable, so an interface can tell a person why `Foo`
    stopped matching `foobar`.
12. **Ignoring case compares simple lowercase mappings, and only for
    the Latin, Greek and Cyrillic letters.** The mappings held are those
    of ASCII, Latin-1, Latin Extended-A, Latin Extended Additional, the
    basic Greek letters and the Cyrillic block with its supplement. Every
    other codepoint compares as itself. Full case folding needs the
    245 KB case table, and a completion menu should not carry it to
    compare two paths. A caller who wants it folds both the needle and
    the candidates with unicode-nv's `ucase.fold` first.
13. **`osa` and `damerau` are different functions.** `osa` is the
    optimal string alignment distance, which forbids editing a
    substring twice. `damerau` is the unrestricted one.
    `osa("ca", "abc")` is 3 and `damerau("ca", "abc")` is 2. Libraries
    routinely ship one under the other's name.
14. **`hamming` answers `None` for strings of different lengths.** It
    is defined only between strings of equal length.
15. **A ranking answers indices, not strings.** `FuzzyRanked.index`
    points into the candidate list the caller passed in, and nothing is
    copied.
16. **A score is fzf's `calculateScore`.** Every matched cluster earns
    16 and a bonus for where it lands, and the first cluster's bonus
    counts twice. A cluster continuing a run earns at least the bonus
    the run started with. A gap between two matches costs 3 for its
    first cluster and 1 for each further one. The module comment of
    `fuzzyscore` lists which bonus applies where.

## What is not included

- **Reading candidates from anywhere.** Every function takes the
  candidates as a list the caller already holds. Walking a directory or
  draining a pipe is the program's business.
- **Accent-insensitive matching.** nucleo's `--normalize` would put a
  `UniData` parameter on `match_at`, `positions_of`, `rank` and every
  option constructor, for a feature fzf does not enable by default.
- **Running on a microcontroller.** The package makes no such claim and
  carries no device probe. A ranking holds one result per matching
  candidate, a position list is allocated per highlighted row, and the
  exact scorer fills a matrix the size of the needle times the
  candidate. A device matching six command names needs a
  fixed-capacity surface, which would be a different set of functions.
- **Regular expressions.** fzf's syntax is five atom kinds and no more.
  [regex-core-nv](https://novo-lang.org/packages/regex-core-nv) is the
  package for patterns.
- **A terminal user interface.** This package answers scores, positions
  and indices. Painting them is the caller's.
- **Sorting a corpus that does not fit in memory.** Every entry point
  takes a list.

## Related packages

- [unicode-nv](https://novo-lang.org/packages/unicode-nv) is the only
  dependency. Its `uclass` predicates decide the camel-case and
  separator bonuses, which an ASCII range gets wrong for German, Greek
  and Cyrillic identifiers. Its `ugrapheme.next_boundary` is what keeps
  every reported position on a cluster boundary.
- [spellcheck-nv](https://novo-lang.org/packages/spellcheck-nv) is
  built on this package's `fuzzydist`. It adds a dictionary, affix
  rules and a deletes index, which is the part a distance function
  cannot do.
- [diff-nv](https://novo-lang.org/packages/diff-nv) describes how one
  text becomes another as an edit script. This package answers how well
  a short needle fits a candidate. A diff is for showing a change; a
  fuzzy match is for ranking a list.
- `std.str` in the standard library has exact substring search, which
  is what to use when the match is not fuzzy.

## Tests

The reference for the scoring is fzf's `src/algo/algo.go`: the bonus
constants, the `FuzzyMatchV2` forward pass, the no-backtrace mode that
justifies the score and positions split, and the smart-case rule. The
`SEARCH SYNTAX` table in `man fzf` and fzf's `parseTerms` are the
specification for `fuzzypat.parse`, and fzf's `--tiebreak` is
`FuzzyTie`. [nucleo](https://github.com/helix-editor/nucleo) reads a
dangling `|` as a literal, and this package refuses it with the offset
of the `|`.

The scores in `fuzzyscore_tests.nv` are worked by hand from fzf's
constants, each with the sum it expects. The exact scorer is checked
against a brute force that enumerates every alignment of three hundred
generated needles and candidates. The fast scorer must never beat it,
and the positions each scorer reports must score what it answered.

The case mappings are checked against Python's `str.lower` over every
codepoint of the ranges rule 12 names.

The distance vectors are the published ones: `kitten` and `sitting` for
Levenshtein, `MARTHA` and `MARHTA` for Jaro-Winkler, `ca` and `abc` for
the two Damerau distances, and rapidfuzz's definitions for the four
ratios. `tools/gen_dist_vectors.py` computes Levenshtein, OSA,
Damerau, the longest common subsequence, Jaro, Jaro-Winkler and `ratio`
for two hundred generated pairs with the textbook algorithms, and
`difflib.SequenceMatcher`'s ratio beside them.
`fuzzydist_vectors_tests.nv` asserts that every one agrees, and that
difflib's ratio is never above `ratio`.

```bash
novo test tests/fuzzypat_tests.nv            # the query syntax and the case rule
novo test tests/fuzzyscore_tests.nv          # the bonus model and the two scorers
novo test tests/fuzzyrank_tests.nv           # the total order and the tiebreaks
novo test tests/fuzzydist_tests.nv           # the published distance vectors
novo test tests/fuzzydist_vectors_tests.nv   # the generated comparison
bash tests/coverage.sh                        # line coverage over src/
```

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
