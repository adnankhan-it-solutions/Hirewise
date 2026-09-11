from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import CandidateProfile, Company, PrivacyRequest, User


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
