import django_filters
from django import forms
from django.db.models import Q

from apps.leads.models import Lead, Niche


class LeadFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Search')
    niche = django_filters.MultipleChoiceFilter(
        field_name='niche',
        choices=Niche.choices,
        widget=forms.SelectMultiple(attrs={'class': 'form-select form-select-sm'}),
    )
    status = django_filters.ChoiceFilter(
        choices=Lead.Status.choices,
        empty_label='All statuses',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    source_type = django_filters.ChoiceFilter(
        choices=[('SOLAR', 'Solar'), ('SWEEPSTAKES', 'Sweepstakes')],
        empty_label='All sources',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    state = django_filters.CharFilter(
        field_name='state',
        lookup_expr='iexact',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'TX'}),
    )
    created_from = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    created_to = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    quality_min = django_filters.NumberFilter(
        field_name='quality_score',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1, 'max': 10, 'placeholder': '1'}),
    )
    quality_max = django_filters.NumberFilter(
        field_name='quality_score',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1, 'max': 10, 'placeholder': '10'}),
    )

    class Meta:
        model = Lead
        fields = ['niche', 'status', 'source_type', 'state']

    def filter_search(self, queryset, name, value):
        v = (value or '').strip()
        if not v:
            return queryset
        return queryset.filter(
            Q(first_name__icontains=v)
            | Q(last_name__icontains=v)
            | Q(email__icontains=v)
            | Q(phone__icontains=v)
        )
