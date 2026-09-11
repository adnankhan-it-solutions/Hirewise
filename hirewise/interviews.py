from datetime import timedelta
from typing import Protocol

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (Consent, Interview, InterviewAnswer, InterviewAssessment, InterviewQuestion,
                     InterviewSlot, Notification, StatusEvent)
from .recruitment import authorized_application, configuration
from .security import audit, company_ids, require_role


class InterviewProvider(Protocol):
    def assess(self, rubric: str, questions: list[dict], answers: list[dict]) -> dict: ...


class InterviewForm(forms.Form):
    questions = forms.CharField(widget=forms.Textarea, max_length=10000, help_text='One recruiter-approved, job-related question per line; 1–10 questions.')
    rubric = forms.CharField(widget=forms.Textarea, max_length=5000, help_text='Define competencies, expected evidence and scoring anchors before inviting the candidate.')
    expiry_days = forms.IntegerField(min_value=1, max_value=30, initial=7)

    def clean_questions(self):
        values = [q.strip() for q in self.cleaned_data['questions'].splitlines() if q.strip()]
        if not 1 <= len(values) <= 10 or any(len(q) > 1000 for q in values):
            raise forms.ValidationError('Provide 1–10 questions, each under 1,000 characters.')
        return values


class SlotForm(forms.Form):
    starts_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}), help_text='Time displayed in Asia/Qatar unless the deployment timezone is configured otherwise.')
    duration_minutes = forms.IntegerField(min_value=15, max_value=120, initial=30)

    def clean_starts_at(self):
        start = self.cleaned_data['starts_at']
        if start <= timezone.now():
            raise forms.ValidationError('Choose a future time.')
        return start


@require_role('recruiter')
def interview_create(request, pk):
    application, _ = authorized_application(request, pk)
    if not configuration().interviews_enabled or not application.job.interview_enabled or application.stage in ('withdrawn', 'archived'):
        return HttpResponse('Interviews are not enabled for this application.', status=409)
    form = InterviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            interview = Interview.objects.create(application=application, created_by=request.user, rubric=form.cleaned_data['rubric'], expires_at=timezone.now() + timedelta(days=form.cleaned_data['expiry_days']))
            for index, question in enumerate(form.cleaned_data['questions']):
                InterviewQuestion.objects.create(interview=interview, text=question, position=index)
            previous = application.stage
            application.stage = 'interview_requested'
            application.save(update_fields=['stage'])
            StatusEvent.objects.create(application=application, actor=request.user, previous=previous, current=application.stage, reason='Recruiter invited a text interview')
            audit(request, 'interview.invited', interview, application.job.company)
            Notification.objects.create(user=application.candidate, recipient=application.email, subject='Text interview invitation', body=f'You have been invited to a text interview for {application.job.title}. Sign in or recover your guest application to view the disclosure and choose an available slot. Application: {application.reference}.')
        return redirect('interview_detail', pk=interview.pk)
    return render(request, 'form.html', {'form': form, 'title': 'Invite a text interview', 'subtitle': 'Approve each question and scoring rubric. No automatic employment decision will be made.', 'button': 'Send invitation'})


def interview_detail(request, pk):
    interview = get_object_or_404(Interview.objects.select_related('application__job__company'), pk=pk)
    application, recruiter = authorized_application(request, interview.application_id)
    if request.method == 'POST':
        if recruiter:
            raise PermissionDenied
        with transaction.atomic():
            interview = Interview.objects.select_for_update().get(pk=pk)
            if interview.expires_at <= timezone.now() or interview.status in ('completed', 'reviewed') or application.stage in ('withdrawn', 'archived'):
                return HttpResponse('This interview is no longer accepting responses.', status=409)
            action = request.POST.get('action')
            if action == 'consent':
                if not request.POST.get('consent'):
                    return HttpResponse('Please acknowledge the interview disclosure.', status=400)
                interview.consented_at = timezone.now()
                interview.save(update_fields=['consented_at'])
                Consent.objects.create(application=application, purpose='text_interview', notice_version=configuration().notice_version)
                audit(request, 'interview.consented', interview, application.job.company)
            elif action == 'schedule':
                if not interview.consented_at:
                    raise PermissionDenied
                # Lock interview then slot consistently; bookings are unique in the DB.
                slot = get_object_or_404(InterviewSlot.objects.select_for_update(), pk=request.POST.get('slot'), company=application.job.company, interview=None, starts_at__gt=timezone.now(), starts_at__lt=interview.expires_at)
                InterviewSlot.objects.filter(interview=interview).update(interview=None)
                slot.interview = interview
                slot.save(update_fields=['interview'])
                interview.status = 'scheduled'
                interview.save(update_fields=['status'])
                StatusEvent.objects.create(application=application, actor=request.user if request.user.is_authenticated else None, previous=application.stage, current='interview_scheduled', reason='Candidate reserved an interview slot')
                application.stage = 'interview_scheduled'
                application.save(update_fields=['stage'])
                audit(request, 'interview.scheduled', interview, application.job.company)
                Notification.objects.create(user=application.candidate, recipient=application.email, subject='Interview scheduled', body=f'Text interview scheduled: {timezone.localtime(slot.starts_at)}. Application: {application.reference}.')
            elif action in ('save', 'complete'):
                if not interview.consented_at or not InterviewSlot.objects.filter(interview=interview, starts_at__lte=timezone.now()).exists():
                    return HttpResponse('Consent and a started interview slot are required.', status=409)
                answers = []
                for question in interview.questions.all():
                    answer = request.POST.get(str(question.pk), '').strip()
                    if len(answer) > 10000:
                        return HttpResponse('An answer exceeds 10,000 characters.', status=400)
                    answers.append((question, answer))
                for question, answer in answers:
                    InterviewAnswer.objects.update_or_create(question=question, defaults={'text': answer})
                interview.status = 'completed' if action == 'complete' else 'in_progress'
                if action == 'complete':
                    interview.completed_at = timezone.now()
                    StatusEvent.objects.create(application=application, actor=request.user if request.user.is_authenticated else None, previous=application.stage, current='interview_completed', reason='Text interview submitted; human review required')
                    application.stage = 'interview_completed'
                    application.save(update_fields=['stage'])
                interview.save(update_fields=['status', 'completed_at'])
                audit(request, f'interview.{action}', interview, application.job.company)
            else:
                return HttpResponse('Invalid action.', status=400)
        return redirect('interview_detail', pk=pk)
    return render(request, 'interview.html', {'interview': interview, 'recruiter': recruiter, 'questions': interview.questions.select_related('answer'),
                  'slots': InterviewSlot.objects.filter(company=application.job.company, interview=None, starts_at__gt=timezone.now(), starts_at__lt=interview.expires_at).order_by('starts_at')[:100],
                  'title': 'Text interview'})


@require_role('recruiter')
def slot_create(request, pk):
    from .models import Company
    company = get_object_or_404(Company, pk=pk, pk__in=company_ids(request.user))
    form = SlotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if InterviewSlot.objects.filter(company=company, starts_at=form.cleaned_data['starts_at']).exists():
            form.add_error('starts_at', 'A slot already exists at this time.')
        else:
            with transaction.atomic():
                slot = InterviewSlot.objects.create(company=company, **form.cleaned_data)
                audit(request, 'interview.slot_created', slot, company)
            messages.success(request, 'Interview slot added.')
            return redirect('dashboard')
    return render(request, 'form.html', {'form': form, 'title': 'Offer an interview slot', 'button': 'Add slot'})


@require_role('recruiter')
@require_POST
def assess_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    application, _ = authorized_application(request, interview.application_id)
    try:
        score = int(request.POST.get('score', ''))
    except ValueError:
        return HttpResponse('A score from 0 to 100 is required.', status=400)
    explanation = request.POST.get('explanation', '').strip()
    if not 0 <= score <= 100 or not explanation or len(explanation) > 10000 or interview.status not in ('completed', 'reviewed'):
        return HttpResponse('Completed interview, score and evidence-based explanation are required.', status=400)
    evidence = [{'question': answer.question.text, 'answer': answer.text, 'answer_id': str(answer.pk)} for answer in InterviewAnswer.objects.filter(question__interview=interview).select_related('question')]
    with transaction.atomic():
        assessment = InterviewAssessment.objects.create(interview=interview, reviewer=request.user, score=score, explanation=explanation, evidence=evidence, rubric_snapshot=interview.rubric)
        interview.status = 'reviewed'
        interview.save(update_fields=['status'])
        audit(request, 'interview.human_assessment', assessment, application.job.company)
    return redirect('interview_detail', pk=pk)
