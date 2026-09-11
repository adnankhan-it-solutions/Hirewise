from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import CandidateProfile, Company, PrivacyRequest, User
from .models import Application, Job, Requirement, PlatformConfig


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(choices=[('candidate', _('I am looking for a role')), ('recruiter', _('I am hiring'))])
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('Unable to register this email. Try signing in or resetting your password.'))
        return email


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website', 'description', 'country']

    def clean_country(self):
        value = self.cleaned_data['country'].upper()
        if len(value) != 2 or not value.isalpha():
            raise forms.ValidationError(_('Use a two-letter country code.'))
        return value


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['headline', 'location', 'summary', 'profile_url', 'portfolio_url', 'notifications_enabled']


class PrivacyForm(forms.ModelForm):
    class Meta:
        model = PrivacyRequest
        fields = ['kind', 'details']


class MFAForm(forms.Form):
    code = forms.RegexField(regex=r'^\d{6}$', max_length=6, label=_('Six-digit authenticator code'),
                           widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}))


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['company', 'title', 'department', 'location', 'country', 'workplace', 'employment', 'seniority',
                  'openings', 'description', 'responsibilities', 'requirements_text', 'preferred_text', 'salary_min',
                  'salary_max', 'currency', 'deadline', 'screening_question', 'interview_enabled']
        widgets = {'deadline': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        from .security import company_ids
        self.fields['company'].queryset = Company.objects.filter(pk__in=company_ids(user))
        if self.instance.pk and not self.instance._state.adding:
            self.fields['company'].disabled = True

    def clean(self):
        data = super().clean()
        if data.get('salary_min') is not None and data.get('salary_max') is not None and data['salary_min'] > data['salary_max']:
            self.add_error('salary_max', 'Maximum salary must be at least the minimum.')
        if data.get('openings') == 0:
            self.add_error('openings', 'At least one opening is required.')
        return data


class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['label', 'category', 'mandatory', 'weight']

    def clean_weight(self):
        value = self.cleaned_data['weight']
        if not 1 <= value <= 100:
            raise forms.ValidationError('Use a weight from 1 to 100.')
        return value

    def clean_label(self):
        value = self.cleaned_data['label']
        import re
        protected = r'\b(race|ethnicity|religion|gender|pregnant|pregnancy|marital|disability|political|nationality|age|male|female|muslim|christian|hindu|attractive|photograph)\b'
        if re.search(protected, value, re.I):
            raise forms.ValidationError('Use job-related criteria only. This criterion requires human legal review and cannot be scored here.')
        return value


class ApplicationForm(forms.ModelForm):
    cv = forms.FileField(help_text='PDF, DOCX or TXT. Maximum 5 MB. Files remain private and must pass scanning.')
    processing_consent = forms.BooleanField(label='I have read the processing notice and agree to share this application with the hiring company for this vacancy.')
    website_check = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Application
        fields = ['name', 'email', 'cover_letter', 'screening_answer', 'profile_url']

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_cv(self):
        from .documents import validate_upload
        upload = self.cleaned_data['cv']
        validate_upload(upload)
        return upload

    def clean_website_check(self):
        if self.cleaned_data['website_check']:
            raise forms.ValidationError('Unable to accept this submission.')
        return ''


class ConfigForm(forms.ModelForm):
    class Meta:
        model = PlatformConfig
        exclude = ['id', 'production_intake_enabled']

    def clean_retention_days(self):
        days = self.cleaned_data['retention_days']
        if not 1 <= days <= 3650:
            raise forms.ValidationError('Choose 1–3650 days after reviewing your retention obligations.')
        return days
