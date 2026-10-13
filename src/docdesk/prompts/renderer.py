"""The only place a prompt is assembled; retrieved text is escaped and kept out of instructions."""

from __future__ import annotations

import re
from dataclasses import dataclass

from docdesk.prompts.loader import PromptFile

VARIABLE = re.compile(r"\{\{(\w+)\}\}")


class RenderError(ValueError):
    """A prompt that cannot be rendered safely."""


@dataclass(frozen=True)
class RenderedPrompt:
    """The two finished messages that go to the model."""

    system: str
    user: str


def escape_delimiters(value: str, untrusted: tuple[str, ...]) -> str:
    """Neutralise our own tags inside data, so evidence cannot close the block it sits in."""
    if not untrusted:
        return value
    tags = "|".join(re.escape(name) for name in untrusted)
    return re.sub(rf"<(/?)\s*({tags})\s*>", r"&lt;\1\2&gt;", value, flags=re.I)


def check_template(prompt: PromptFile) -> None:
    """Refuse templates that would put data in the instructions or leave it without delimiters."""
    system_names = set(VARIABLE.findall(prompt.system))
    user_side = f"{prompt.user}\n{prompt.repair}"
    for name in prompt.untrusted:
        if name in system_names:
            raise RenderError(f"untrusted variable '{name}' is used in the system section")
        wrapped = rf"<{name}>\s*\{{\{{{name}\}}\}}\s*</{name}>"
        if "{{" + name + "}}" in user_side and not re.search(wrapped, user_side):
            raise RenderError(f"untrusted variable '{name}' is not inside <{name}> delimiters")


def compare(wanted: set[str], given: set[str], where: str) -> None:
    """Fail on a missing or unknown variable, so a typo can never become an empty string."""
    if wanted - given:
        raise RenderError(f"missing {where}variables: {', '.join(sorted(wanted - given))}")
    if given - wanted:
        raise RenderError(f"unknown {where}variables: {', '.join(sorted(given - wanted))}")


def fill_template(template: str, values: dict[str, str], untrusted: tuple[str, ...]) -> str:
    """Substitute in one pass and escape untrusted values, so inserted text is never re-expanded."""

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        return escape_delimiters(values[name], untrusted) if name in untrusted else values[name]

    return VARIABLE.sub(fill, template)


def render(
    prompt: PromptFile, variables: dict[str, str], repair: dict[str, str] | None = None
) -> RenderedPrompt:
    """Build the two messages; with repair values, add the retry text after the user message."""
    check_template(prompt)
    compare(set(VARIABLE.findall(prompt.system + prompt.user)), set(variables), "")
    user = fill_template(prompt.user, variables, prompt.untrusted)
    if repair is not None:
        if not prompt.repair:
            raise RenderError(f"prompt {prompt.name} has no repair section")
        compare(set(VARIABLE.findall(prompt.repair)), set(repair), "repair ")
        user = f"{user}\n\n{fill_template(prompt.repair, repair, prompt.untrusted)}"
    return RenderedPrompt(
        system=fill_template(prompt.system, variables, prompt.untrusted), user=user
    )
