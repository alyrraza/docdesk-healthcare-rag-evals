"""Reading a prompt file: front matter, sections and a content hash (T063)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docdesk.prompts.loader import PromptError, load_prompt, parse_prompt

ROOT = Path(__file__).resolve().parents[2]


def file_name_problem(path: Path, prompt) -> str | None:
    """Say how a file name disagrees with its front matter, or None when they agree."""
    name, _, suffix = path.stem.rpartition(".v")
    if name != prompt.name:
        return f"file name says name {name!r}, front matter says {prompt.name!r}"
    if suffix != prompt.version.split(".")[0]:
        return f"file name says v{suffix}, front matter version is {prompt.version}"
    return None

SAMPLE = """---
name: demo
version: 1.2.0
schema: AnswerOutput@1
params:
  temperature: 0
  top_p: 0.5
  mode: strict
untrusted:
  - evidence
status: released
changelog: a note # trailing comment
---
## system
Rules here.

## user
Q: {{question}}
<evidence>
{{evidence}}
</evidence>
"""


def test_ac_prm_01_front_matter_fields_are_read_with_their_types() -> None:
    prompt = parse_prompt(SAMPLE)
    assert (prompt.name, prompt.version, prompt.schema, prompt.status) == (
        "demo",
        "1.2.0",
        "AnswerOutput@1",
        "released",
    )
    assert prompt.params == {"temperature": 0, "top_p": 0.5, "mode": "strict"}
    assert prompt.untrusted == ("evidence",)
    assert prompt.changelog == "a note"


def test_ac_prm_01_the_system_and_user_sections_are_split() -> None:
    prompt = parse_prompt(SAMPLE)
    assert prompt.system == "Rules here."
    assert prompt.user.startswith("Q: {{question}}")
    assert prompt.user.endswith("</evidence>")


def test_ac_prm_01_an_empty_untrusted_list_is_allowed() -> None:
    assert parse_prompt(SAMPLE.replace("untrusted:\n  - evidence", "untrusted: []")).untrusted == ()


def test_ac_prm_01_the_hash_ignores_windows_line_endings_but_not_real_edits() -> None:
    same = parse_prompt(SAMPLE.replace("\n", "\r\n"))
    assert same.content_hash == parse_prompt(SAMPLE).content_hash
    assert parse_prompt(SAMPLE.replace("Rules here.", "Rules here!")).content_hash != (
        same.content_hash
    )


@pytest.mark.parametrize(
    ("broken", "message"),
    [
        (SAMPLE.replace("name: demo\n", ""), "name"),
        (SAMPLE.replace("status: released", "status: final"), "status"),
        (SAMPLE.replace("## user", "## other"), "user"),
        (SAMPLE.replace("---\nname", "name", 1), "front matter"),
    ],
)
def test_ac_prm_01_a_malformed_file_is_refused_with_a_reason(broken: str, message: str) -> None:
    with pytest.raises(PromptError, match=message):
        parse_prompt(broken)


def test_ac_prm_01_the_shipped_answer_prompt_loads() -> None:
    prompt = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
    assert (prompt.name, prompt.schema, prompt.untrusted) == (
        "answer",
        "AnswerOutput@1",
        ("evidence", "previous_output", "validation_error"),
    )


def test_ac_prm_01_every_shipped_prompt_loads_and_file_names_match_front_matter() -> None:
    paths = sorted((ROOT / "prompts").glob("*/*.md"))
    prompts = [load_prompt(path) for path in paths]
    assert {p.name for p in prompts} >= {"answer", "router", "text2sql"}
    for path, prompt in zip(paths, prompts, strict=True):
        assert file_name_problem(path, prompt) is None, path.name


def test_ac_prm_01_a_v2_file_with_version_1_front_matter_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "demo" / "demo.v2.md"
    path.parent.mkdir()
    path.write_text(SAMPLE, encoding="utf-8")  # SAMPLE is demo, version 1.2.0
    problem = file_name_problem(path, load_prompt(path))
    assert problem is not None and "v2" in problem
    other = tmp_path / "demo" / "other.v1.md"
    other.write_text(SAMPLE, encoding="utf-8")
    assert "name" in file_name_problem(other, load_prompt(other))
