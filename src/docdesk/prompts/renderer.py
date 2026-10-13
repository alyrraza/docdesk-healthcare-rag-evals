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
    for name in prompt.untrusted:
        if name in system_names:
            raise RenderError(f"untrusted variable '{name}' is used in the system section")
        wrapped = rf"<{name}>\s*\{{\{{{name}\}}\}}\s*</{name}>"
        if not re.search(wrapped, prompt.user):
            raise RenderError(f"untrusted variable '{name}' is not inside <{name}> delimiters")


def render(prompt: PromptFile, variables: dict[str, str]) -> RenderedPrompt:
    """Fill the template in one pass, so a value that looks like {{x}} is never expanded."""
    check_template(prompt)
    wanted = set(VARIABLE.findall(prompt.system)) | set(VARIABLE.findall(prompt.user))
    missing, extra = wanted - variables.keys(), variables.keys() - wanted
    if missing:
        raise RenderError(f"missing variables: {', '.join(sorted(missing))}")
    if extra:
        raise RenderError(f"unknown variables: {', '.join(sorted(extra))}")

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        value = variables[name]
        return escape_delimiters(value, prompt.untrusted) if name in prompt.untrusted else value

    return RenderedPrompt(
        system=VARIABLE.sub(fill, prompt.system), user=VARIABLE.sub(fill, prompt.user)
    )
