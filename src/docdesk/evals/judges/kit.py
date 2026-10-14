"""The two judges' prompts, parsers and shared client, built once per run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docdesk.evals.judges.parser import JudgeParser
from docdesk.evals.judges.schemas import CorrectnessJudgement, FaithfulnessJudgement
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile, load_prompt

FAITHFULNESS_FILE = "judge_faithfulness/judge_faithfulness.v2.md"
CORRECTNESS_FILE = "judge_correctness/judge_correctness.v2.md"


@dataclass
class JudgeKit:
    """One run's judges. The parsers keep the parse failure counts for the whole run."""

    faithfulness_prompt: PromptFile
    correctness_prompt: PromptFile
    client: LLMClient
    # The judge model id comes from the pinned eval config, never from code.
    model: str
    faithfulness_parser: JudgeParser[FaithfulnessJudgement] = field(
        default_factory=lambda: JudgeParser(FaithfulnessJudgement)
    )
    correctness_parser: JudgeParser[CorrectnessJudgement] = field(
        default_factory=lambda: JudgeParser(CorrectnessJudgement)
    )

    def prompt_hashes(self) -> dict[str, str]:
        """Name@version to content hash, stored with each result."""
        prompts = (self.faithfulness_prompt, self.correctness_prompt)
        return {f"{p.name}@{p.version}": p.content_hash for p in prompts}


def load_judge_prompts(prompts_dir: Path) -> tuple[PromptFile, PromptFile]:
    """Load the two judge prompt files; the check command uses this without any client."""
    return (
        load_prompt(prompts_dir / FAITHFULNESS_FILE),
        load_prompt(prompts_dir / CORRECTNESS_FILE),
    )


def load_judge_kit(prompts_dir: Path, client: LLMClient, model: str) -> JudgeKit:
    """Attach the client and the config's judge model to the pinned judge prompts."""
    faithfulness, correctness = load_judge_prompts(prompts_dir)
    return JudgeKit(faithfulness, correctness, client, model)
