# Writing Style Guide

Rules for any agent producing prose on Michael Hemmett’s behalf: research proposals, fellowship statements, abstracts, READMEs, pull request descriptions, commit messages, issues, and docstrings. This guide describes how science is communicated in this voice, not what the science is. Apply it to any topic.

## 1. Voice and document structure

Lead with stakes, then narrow to the specific claim, method, or change. State the thesis once in a clear declarative sentence; bold it in long documents. Quantify wherever a number exists. Define each technical term and acronym once by apposition, then use it freely. State what expected, alternative, and null results mean. Close sections and documents by widening to the broader consequence.

Long documents open with a self-contained summary paragraph of 150–250 words covering stakes, gap, proposed work, and outcome. Order the funnel as stakes, gap, opportunity, proposal, hypothesis and falsifiable prediction, broad consequence. Walk through multi-part plans with ordinal transitions (“First,” “Second,” “Lastly”) rather than bullets. In sectioned proposals, use short run-in labels such as *Volcanic context.* After methods, explain what each outcome would mean, including a useful null result. End by connecting the work to other sites, users, or fields.

Use required headings such as “Intellectual Merit” and “Broader Impacts” when a venue requires them; write their content as prose. Name concrete broader-impact deliverables, audiences, venues, and timing.

## 2. Register

| Setting | Person and tense | Sentence length | Lists |
|---|---|---|---|
| Technical proposal | First person for ownership; present for context, future for plans; future passive is acceptable for formal method mechanics | Usually 18–25 words; longer parallel lists are acceptable | Avoid in body prose |
| Personal or fellowship | First person throughout; past for experience, present for current work, future for goals | Usually about 25 words | Avoid |
| Repository | First person singular or imperative in PRs and commits; impersonal in README and docstrings; present for behavior, past for changes | Short, usually about 15 words | Use for commands, steps, options, and file lists |

When uncertain, choose the more formal setting.

## 3. Paragraphs and sentences

Proposal and personal-statement paragraphs usually run 150–350 words and each carry one movement. The first sentence states the point. Support it with evidence, then connect it to the objective or consequence. In Markdown, separate paragraphs with a blank line and do not indent.

Prefer one main clause with one subordinate clause. Very short sentences are rare and emphatic; 40–50-word sentences are suitable for parallel lists. Concessive openers (“Though,” “While,” “Despite,” “Fortunately”) acknowledge a limitation before turning to the opportunity. Favored transitions include *Additionally*, *Lastly*, *Finally*, *Thus*, *First/Second/Third*, *Alternatively*, and *In either case*. Avoid *Moreover*, repeated sentence-initial *However*, *In conclusion*, and *Overall*.

Use concrete noun or “I” subjects. Prefer active voice. Use firm commitment verbs (*will*, *propose*, *expect*, *anticipate*) and hedge inference only once (*suggest*, *likely*, *may*, *could*). Make comparisons and consequences explicit.

## 4. Word choice and mechanics

Define acronyms on first use: “distributed acoustic sensing (DAS).” Give institutions and programs their full name once. Use at most one or two short vernacular glosses per page. Quantify claims; spell out one through nine when unattached to units, use numerals with units, and use en dashes for ranges. Follow SI spacing, American spelling, and the Oxford comma. Hyphenate compound modifiers consistently; do not hyphenate after adverbs ending in *-ly*.

Use intensifiers sparingly: at most one per paragraph in technical writing and two in personal writing. Avoid *delve*, *crucial role*, *plays a role*, *it is important to note*, *in order to*, filler *robust*, *cutting-edge*, *state-of-the-art*, *unprecedented*, *paradigm*, repeated *novel*, *not only…but also*, *in today’s world*, *groundbreaking*, and *leverage* as a verb outside “leverage these developments.” Avoid rhetorical questions, exclamation marks, contractions, emoji, and sentences beginning “In this proposal/section/PR, I will.”

Use spaced en dashes for asides and glosses, at most one pair per paragraph. Double curly quotes mark glosses or official designations, not emphasis. Parentheses are for acronyms, citations, figure references, and short examples, not full sentences. Keep semicolons rare; use colons to introduce enumerations and definitions. Follow venue citation conventions and cite empirical claims, tools, and prior results. Refer to figures as “(Fig. 1)”; captions should state what is shown, how it was processed, and what the reader should see.

## 5. Personal and narrative writing

Open by locating the writer in the problem, then state the goal and long-term aim. Tell experiences chronologically; close each with the skill gained and an explicit bridge to future work. Name people, programs, and venues in full at first mention. State accomplishments as facts and quantify them where possible. Keep reflection brief and concrete. Show service through what was done, for whom, and how it prepares the writer for future work. Enumerate future plans with ordinals, named venues, and audiences.

## 6. Repository prose

Apply the same funnel: purpose and stakes, what changed or what the software does, how it works, how to verify it, and what follows. Prose carries motivation and interpretation; lists carry commands, options, steps, and inventories.

### README

Use this order, omitting only empty sections:

1. Title and one-sentence purpose, with stakes first.
2. An 80–150-word overview of the problem, approach, and outputs; define acronyms.
3. Installation commands, runtime version, and system dependencies.
4. A minimal quick start and where its output lands.
5. Usage subsections with purpose, code, and argument types, defaults, and descriptions.
6. Input data formats, units, coordinates, sampling, provenance, and size.
7. One to three methods paragraphs connecting implementation and science, with citations.
8. Output schema and validation method or expected range.
9. Repository layout with one-line descriptions.
10. Citation, acknowledgments, funding and award numbers, and license.

Avoid badges beyond build and license status, uncaptained screenshots, and feature lists that repeat the overview.

### Pull requests

Use imperative titles under 70 characters. Include these sections:

```markdown
## Summary
One or two sentences stating the impact and why the change matters.

## Changes
- Three to seven behavior-focused changes, naming relevant modules.

## Validation
Commands run and observed results, quantified where possible.

## Notes
Limitations, follow-ups, and reviewer guidance; explain fallback outcomes.
```

Reference issues by number. Do not say “This PR aims to” or merely list changed files. Include figures for visual changes.

### Commits and issues

Commit subjects are imperative, capitalized, 50–70 characters, and have no period. Name behavior, not a file. When explanation is needed, add a blank line and a two-to-five-sentence prose body explaining why, approach, and verification; wrap at 72 characters. Reference issues in the body or a trailer. Avoid “fix,” “updates,” “wip,” “misc changes,” and emoji.

An issue opens with one impact sentence, then gives reproduction or context, expected behavior, and a proposed direction. Quantify failures. For proposals, state what each plausible cause would imply.

### Docstrings and comments

Write NumPy-style docstrings. The first line states what the function does or returns, with units. Follow with `Parameters`, `Returns`, `Notes` (method and citation), and `Examples` as applicable. Define acronyms once in the module docstring. Comments explain why, not what. Put physical units in names or docstrings (for example, `delay_time_s` and `depth_km`).

## 7. Anti-patterns and final review

Revise drafts that lead with a technique instead of stakes, imply rather than state the thesis, omit outcome interpretations, use adjectives where numbers exist, stack hedges, pair intensifiers, or leave an experience or change without its consequence. Avoid bullets in proposal prose, unspaced em dashes, repeated dash pairs, rhetorical questions, contractions, and summary-only endings. Repository prose should describe behavior rather than narrate a diff.

Before submitting, check that the opening states stakes; the thesis is unmistakable; acronyms are defined once; claims have citations or numbers; plans include expected, alternative, and null outcomes; paragraphs connect forward; spelling, punctuation, and intensifiers follow this guide; and the ending widens to the broader consequence. For repository text, also check the README order, PR sections, and imperative behavior-focused commit subject.
