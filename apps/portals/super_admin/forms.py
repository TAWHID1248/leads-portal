import secrets

from django import forms
from django.contrib.auth import get_user_model

from apps.agents.models import Agent
from apps.clients.models import Client

User = get_user_model()


def generate_temp_password():
    return secrets.token_urlsafe(12)


class _BootstrapMixin:
    """Tack Bootstrap classes onto every widget so the templates can stay terse."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class ClientCreateForm(_BootstrapMixin, forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Leave blank to auto-generate.',
    )
    company_name = forms.CharField(max_length=255)
    country = forms.CharField(max_length=2, required=False)
    timezone = forms.CharField(max_length=50, initial='UTC')
    billing_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    tax_id = forms.CharField(max_length=50, required=False)
    webhook_url = forms.URLField(required=False)
    notify_email = forms.BooleanField(initial=True, required=False)
    notify_sms = forms.BooleanField(initial=False, required=False)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email


class ClientUpdateForm(_BootstrapMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Client
        fields = ['company_name', 'country', 'timezone', 'billing_address',
                  'tax_id', 'webhook_url', 'notify_email', 'notify_sms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            u = self.instance.user
            self.fields['first_name'].initial = u.first_name
            self.fields['last_name'].initial = u.last_name
            self.fields['phone'].initial = u.phone

    def save(self, commit=True):
        client = super().save(commit=commit)
        u = client.user
        u.first_name = self.cleaned_data.get('first_name', '') or u.first_name
        u.last_name = self.cleaned_data.get('last_name', '') or u.last_name
        u.phone = self.cleaned_data.get('phone', '') or u.phone
        if commit:
            u.save(update_fields=['first_name', 'last_name', 'phone'])
        return client


class CreditWalletForm(_BootstrapMixin, forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    note = forms.CharField(max_length=255, required=False)


class AgentCreateForm(_BootstrapMixin, forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Leave blank to auto-generate.',
    )
    target_leads = forms.IntegerField(min_value=0, initial=20)
    target_revenue = forms.DecimalField(max_digits=10, decimal_places=2, initial=1000)
    commission = forms.DecimalField(max_digits=5, decimal_places=3, initial=0.1,
                                    help_text='Fraction of revenue (0.1 = 10%).')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email


class AgentUpdateForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['target_leads', 'target_revenue', 'commission']
