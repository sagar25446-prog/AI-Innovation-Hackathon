"""Pre-translate every fixed string into the twelve extended languages.

Run this once (and again whenever curated copy changes); commit the result.

    py -3.12 tools/build_translation_pack.py                # all languages
    py -3.12 tools/build_translation_pack.py tamil bengali  # just these
    py -3.12 tools/build_translation_pack.py --check        # verify, write nothing

Why this exists
---------------
Every string GuruFlow speaks in a curated lesson is fixed at build time:
narration, objectives, checkpoint feedback, repair explanations, flashcards,
report copy. Translating them at *lesson* time meant a learner who picked Tamil
waited on a live API call per string, and got English whenever that call was
rate-limited - which, on Gemini's 20-requests-per-day free tier, was most of
the time. Translating them at *build* time makes those languages instant,
deterministic and completely offline.

Formula safety
--------------
A translation that mangles ``I = V / R`` teaches the wrong physics, so this
tool does not trust the engines: every candidate is checked for the equations,
numbers and unit symbols present in the source, and a translation that dropped
one is rejected and retried with the next engine. Rejections are reported at
the end rather than written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services import translation  # noqa: E402
from services.translation import engines, pack  # noqa: E402

# Tokens that must survive translation byte-for-byte. Anything matching these
# in the source must appear in the translation, or the translation is wrong.
_PROTECTED = re.compile(
    r"""
      [A-Za-z]\s*=\s*[^\s,.;]+       # equations: I = V/R, V = I x R
    | \b\d+(?:\.\d+)?\s*[A-ZΩ]\b     # quantities with units: 12 V, 4 Ω
    | \bI\s*=\s*V\s*/\s*R\b
    """,
    re.VERBOSE,
)


def _protected_tokens(text: str) -> set[str]:
    return {m.group(0).replace(" ", "") for m in _PROTECTED.finditer(text)}


def _preserved(source: str, candidate: str) -> bool:
    """True when every protected token in the source survived translation."""
    wanted = _protected_tokens(source)
    if not wanted:
        return True
    flat = candidate.replace(" ", "")
    return all(token in flat for token in wanted)


# ---------------------------------------------------------------------------
# Collecting the strings
# ---------------------------------------------------------------------------


def collect_source_strings() -> list[str]:
    """Every canonical English string a curated lesson can say.

    Gathered from the live modules rather than a hand-kept list, so new curated
    copy is picked up by re-running the tool instead of being silently missed.
    """
    found: set[str] = set()

    def add(value) -> None:
        if isinstance(value, str):
            clean = value.strip()
            if clean:
                found.add(clean)
        elif isinstance(value, dict):
            # Language-keyed catalogues: only the English member is a source.
            if "english" in value:
                add(value["english"])
            else:
                for item in value.values():
                    add(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)

    # 1. The concept catalogue - narration and objectives for every scene.
    from services.planner.concepts import CONCEPTS_BY_ID

    for concept in CONCEPTS_BY_ID.values():
        add(concept.get("narration"))
        add(concept.get("objective"))
        add(concept.get("checkpointPrompt"))

    # 2. Checkpoint feedback, misconception repairs and their objectives, plus
    #    the revision advice on the final report screen.
    from services import evaluation

    add(evaluation.FEEDBACK)
    add(evaluation.REPAIR_NARRATION)
    add(evaluation.REPAIR_OBJECTIVE)
    add(evaluation._REVISION)

    # 3. Flashcards.
    from services.planner import flashcards

    add(flashcards._FLASH_BANK)

    # 4. Persona framing and tone.
    from services.planner import persona

    add(persona._NARRATION_FRAMING)
    add(persona._FEEDBACK_TONE)

    # 5. Follow-up question copy.
    from services import qa

    add(qa._LEAD_IN)
    add(qa._UNGROUNDED)

    # 6. The end-of-lesson quiz: prompts, options and the explanation attached
    #    to every wrong option, since those are shown to the learner.
    from services import assessment

    for questions in assessment.QUESTION_BANK.values():
        for question in questions:
            add(question.get("prompt"))
            add(question.get("hint"))
            add(question.get("model"))
            add(question.get("working"))
            for option in question.get("options", []):
                add(option.get("text"))
                add(option.get("why"))
    add(assessment._CORRECT_NOTE)
    add(assessment._VERDICTS)

    # 7. Learning-path titles and the "why this module" lines.
    from services.planner.learning_path import AUTHORED_PATHS

    for path in AUTHORED_PATHS.values():
        add(path.get("title"))
        add(path.get("summary"))
        for module in path.get("modules", []):
            add(module.get("title"))
            add(module.get("why"))

    # 8. Planner fallback copy shown when the LLM cannot be reached.
    from services import planner

    add(planner._UPLOADED_OFF_CATALOGUE)
    add(planner._LLM_QUOTA_SPENT)
    add(planner._LLM_UNREACHABLE)
    add(planner._NO_LLM_KEY)

    return sorted(found)


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def build_language(
    language: str,
    sources: list[str],
    *,
    check_only: bool,
    force: bool,
    prune: bool = False,
) -> dict[str, int]:
    existing = pack.load(language)
    stats = {"kept": 0, "added": 0, "rejected": 0, "failed": 0, "pruned": 0}
    rejected: list[str] = []

    chain = [e for e in engines.default_engines() if e.available()]
    if not chain:
        print(f"  no engine available; skipping {language}")
        stats["failed"] = len(sources)
        return stats

    entries = dict(existing)
    if prune:
        # The pack is a write-back cache at runtime, so a deployed copy legitimately
        # accumulates strings from off-catalogue lessons. The *committed* copy
        # should be exactly what this tool regenerates, so it stays reviewable and
        # reproducible - and so a stray string from a test run never ships.
        catalogue = set(sources)
        removed = [key for key in entries if key not in catalogue]
        for key in removed:
            del entries[key]
        stats["pruned"] = len(removed)

    for index, source in enumerate(sources, 1):
        if source in entries and not force:
            stats["kept"] += 1
            continue
        if check_only:
            stats["failed"] += 1
            continue

        translated = None
        for engine in chain:
            try:
                candidate = engine.translate(source, language)
            except Exception as exc:  # noqa: BLE001 - try the next engine
                print(f"    {engine.name} raised: {exc}")
                continue
            if not candidate:
                continue
            if not _preserved(source, candidate):
                stats["rejected"] += 1
                rejected.append(f"[{engine.name}] {source[:60]}")
                continue
            translated = candidate
            break

        if translated:
            entries[source] = translated
            stats["added"] += 1
        else:
            stats["failed"] += 1
        print(f"\r  {language}: {index}/{len(sources)}", end="", flush=True)

    print()
    if not check_only and entries != existing:
        path = pack.pack_path(language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "language": language,
                    "note": (
                        "Generated by tools/build_translation_pack.py and extended "
                        "at runtime. Equations, numbers and unit symbols are "
                        "preserved verbatim; see services/translation/pack.py."
                    ),
                    "entries": dict(sorted(entries.items())),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    for line in rejected:
        print(f"    rejected (formula lost): {line}")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("languages", nargs="*", help="languages to build (default: all)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report coverage without translating or writing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-translate strings the pack already has",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="drop entries that are not in the current catalogue (run before committing)",
    )
    args = parser.parse_args()

    targets = args.languages or [
        language
        for language in translation.SUPPORTED_LANGUAGES
        if language not in translation.CORE_LANGUAGES
    ]
    unknown = [t for t in targets if not translation.is_supported(t)]
    if unknown:
        parser.error(f"unsupported language(s): {', '.join(unknown)}")

    sources = collect_source_strings()
    print(f"{len(sources)} source strings; {len(targets)} language(s)\n")

    incomplete = []
    for language in targets:
        print(f"{language}:")
        stats = build_language(
            language,
            sources,
            check_only=args.check,
            force=args.force,
            prune=args.prune,
        )
        covered = stats["kept"] + stats["added"]
        pruned = f", {stats['pruned']} pruned" if stats["pruned"] else ""
        print(
            f"  {covered}/{len(sources)} covered "
            f"(+{stats['added']} new, {stats['rejected']} rejected, "
            f"{stats['failed']} missing{pruned})\n"
        )
        if covered < len(sources):
            incomplete.append(language)

    if incomplete:
        print(f"Incomplete: {', '.join(incomplete)}")
        return 1
    print("All languages fully covered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
