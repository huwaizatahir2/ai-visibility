from __future__ import annotations

from decimal import Decimal
from decimal import InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseGone
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from ai_visibility.surveys.models import Answer
from ai_visibility.surveys.models import Question
from ai_visibility.surveys.models import Response
from ai_visibility.surveys.models import SurveyRun
from ai_visibility.surveys.models import SurveyToken

LIKERT_MIN, LIKERT_MAX = Decimal(1), Decimal(5)
PERCENT_MIN, PERCENT_MAX = Decimal(0), Decimal(100)


def _clean(qtype: str, raw: str) -> Decimal | None:
    try:
        value = Decimal(raw)
    except InvalidOperation, TypeError:
        return None
    if qtype == Question.QType.LIKERT and not (LIKERT_MIN <= value <= LIKERT_MAX):
        return None
    if qtype == Question.QType.PERCENT and not (PERCENT_MIN <= value <= PERCENT_MAX):
        return None
    return value


def answer(request, token) -> HttpResponse:
    survey_token = get_object_or_404(
        SurveyToken.objects.select_related("run", "run__template"),
        token=token,
    )
    run = survey_token.run
    if survey_token.consumed:
        return render(request, "surveys/already.html")
    if run.status == SurveyRun.Status.CLOSED or run.closes_at < timezone.now():
        return HttpResponseGone("This survey has closed.")

    questions = list(run.template.questions.all())
    if request.method == "POST":
        return _submit(request, survey_token, questions)
    return render(
        request,
        "surveys/answer.html",
        {"run": run, "questions": questions, "token": token},
    )


def _submit(
    request, survey_token: SurveyToken, questions: list[Question]
) -> HttpResponse:
    with transaction.atomic():
        locked = SurveyToken.objects.select_for_update().get(pk=survey_token.pk)
        if locked.consumed:
            return render(request, "surveys/already.html")
        response = Response.objects.create(run=locked.run)
        answers = []
        for question in questions:
            value = _clean(question.qtype, request.POST.get(f"q_{question.id}"))
            if value is not None:
                answers.append(
                    Answer(response=response, question=question, value=value)
                )
        Answer.objects.bulk_create(answers)
        locked.consumed = True
        locked.save(update_fields=["consumed"])
    return redirect("surveys:done")


def done(request) -> HttpResponse:
    return render(request, "surveys/done.html")
