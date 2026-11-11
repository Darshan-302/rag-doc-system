"""Prompt assembly and safety post-processing driven by a DomainProfile.

Prompts are built by plain string concatenation (not str.format) so braces in
retrieved context or YAML text can never raise or be mangled.
"""

from __future__ import annotations

from typing import Optional

from src.domains.profile import DomainProfile

EMERGENCY_RESPONSE = (
    "This may be a medical emergency. Please contact your local emergency "
    "services or seek immediate emergency care now."
)


def _format_examples(profile: DomainProfile) -> str:
    blocks = []
    for i, ex in enumerate(profile.few_shot_examples, 1):
        blocks.append(
            f"Example {i}\n"
            f"Documents:\n{str(ex['context']).strip()}\n\n"
            f"Question: {str(ex['query']).strip()}\n\n"
            f"Answer: {str(ex['answer']).strip()}"
        )
    return "\n\n".join(blocks)


def build_prompt(
    profile: DomainProfile,
    query: str,
    context: str,
    task: Optional[str] = None,
) -> str:
    """Assemble the full prompt: system prompt, optional task prompt,
    few-shot examples, then the retrieved documents and the question."""
    parts = [profile.system_prompt]

    if task:
        task_def = profile.task_prompts.get(task)
        if task_def is None:
            raise KeyError(
                f"Unknown task '{task}' for domain '{profile.name}'. "
                f"Available: {sorted(profile.task_prompts)}"
            )
        task_text = str(task_def.get("prompt", "")).strip()
        if task_text:
            parts.append("Task instructions:\n" + task_text)

    if profile.few_shot_examples:
        parts.append(_format_examples(profile))

    parts.append(f"Documents:\n{context}\n\nQuestion: {query}\n\nAnswer:")
    return "\n\n".join(parts)


def check_escalation(profile: DomainProfile, query: str) -> Optional[str]:
    """Static emergency response if the domain enables escalation and the
    query contains one of its escalation keywords; otherwise None.

    The keyword list is the illustrative starter list from the prompts YAML
    (not medically validated)."""
    if not profile.emergency_escalation_enabled:
        return None
    lowered = query.lower()
    if any(k.lower() in lowered for k in profile.escalation_keywords):
        disclaimer = profile.medical_disclaimer_text
        return EMERGENCY_RESPONSE + (f"\n\n{disclaimer}" if disclaimer else "")
    return None


def finalize_answer(profile: DomainProfile, answer: str) -> str:
    """Append the domain's mandatory disclaimer text when the YAML requires it."""
    if (
        profile.response_format.get("include_medical_disclaimer")
        and profile.retrieval.get("require_medical_disclaimer", True)
        and profile.medical_disclaimer_text
        and profile.medical_disclaimer_text not in answer
    ):
        return f"{answer}\n\n{profile.medical_disclaimer_text}"
    return answer
