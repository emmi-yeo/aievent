from fastapi import APIRouter, Depends, HTTPException

from models.schemas import OnboardingChatMessage, OnboardingChatResponse, OnboardingStatusResponse
from gcloud.sheets import (
    save_onboarding_answer, get_onboarding_answers,
    update_engagement_field, get_engagement_by_id,
)
from auth.utils import require_client

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Fixed list of questions asked one by one
QUESTIONS = [
    "What is your company name and what does your business do?",
    "What industry are you in, and roughly how large is your company (team size or revenue range)?",
    "Is there anything else you would like the consultant to know before the strategy meeting?",
]

COMPLETION_MESSAGE = (
    "Thank you! That's everything I need for now. "
    "Your answers have been saved and your consultant will review them before the meeting. "
    "Please proceed to upload your business documents."
)


def _get_answered_count(answers: list) -> int:
    """Count how many questions have a non-empty answer."""
    return len([a for a in answers if a.get("answer", "").strip()])


@router.get("/{engagement_id}/start", response_model=OnboardingChatResponse)
async def start_onboarding(
    engagement_id: str,
    client: dict = Depends(require_client),
):
    """Return the current state — either the next unanswered question or completion."""
    if client.get("engagement_id") != engagement_id:
        raise HTTPException(status_code=403, detail="Access denied")

    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if str(eng.get("onboarding_complete", "")).upper() == "TRUE":
        return OnboardingChatResponse(
            reply=COMPLETION_MESSAGE,
            is_complete=True,
        )

    answers = get_onboarding_answers(engagement_id)
    answered_count = _get_answered_count(answers)

    if answered_count >= len(QUESTIONS):
        update_engagement_field(engagement_id, "onboarding_complete", "TRUE")
        return OnboardingChatResponse(reply=COMPLETION_MESSAGE, is_complete=True)

    # Return greeting + first question
    company = eng.get("company", "your company")
    greeting = (
        f"Welcome! I'll ask you {len(QUESTIONS)} quick questions about {company} "
        f"so your consultant can prepare for the strategy meeting.\n\n"
        f"Question 1 of {len(QUESTIONS)}: {QUESTIONS[0]}"
    )
    return OnboardingChatResponse(reply=greeting, is_complete=False)


@router.post("/{engagement_id}/chat", response_model=OnboardingChatResponse)
async def chat(
    engagement_id: str,
    body: OnboardingChatMessage,
    client: dict = Depends(require_client),
):
    """Save the user's answer and return the next question."""
    if client.get("engagement_id") != engagement_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    eng = get_engagement_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if str(eng.get("onboarding_complete", "")).upper() == "TRUE":
        return OnboardingChatResponse(reply=COMPLETION_MESSAGE, is_complete=True)

    answers = get_onboarding_answers(engagement_id)
    answered_count = _get_answered_count(answers)

    if answered_count >= len(QUESTIONS):
        update_engagement_field(engagement_id, "onboarding_complete", "TRUE")
        return OnboardingChatResponse(reply=COMPLETION_MESSAGE, is_complete=True)

    # Save the answer for the current question
    current_question = QUESTIONS[answered_count]
    save_onboarding_answer(engagement_id, current_question, body.message.strip())

    next_index = answered_count + 1

    # All questions answered
    if next_index >= len(QUESTIONS):
        update_engagement_field(engagement_id, "onboarding_complete", "TRUE")
        return OnboardingChatResponse(reply=COMPLETION_MESSAGE, is_complete=True)

    # Return the next question
    next_question = QUESTIONS[next_index]
    reply = (
        f"Got it, thank you!\n\n"
        f"Question {next_index + 1} of {len(QUESTIONS)}: {next_question}"
    )
    return OnboardingChatResponse(reply=reply, is_complete=False)


@router.get("/{engagement_id}/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    engagement_id: str,
    client: dict = Depends(require_client),
):
    if client.get("engagement_id") != engagement_id:
        raise HTTPException(status_code=403, detail="Access denied")

    eng = get_engagement_by_id(engagement_id)
    answers = get_onboarding_answers(engagement_id)
    return OnboardingStatusResponse(
        is_complete=str(eng.get("onboarding_complete", "")).upper() == "TRUE",
        answers_count=_get_answered_count(answers),
    )
