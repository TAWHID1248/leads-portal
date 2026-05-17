from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.forms import ForgotPasswordForm, LoginForm, ResetPasswordForm

User = get_user_model()

_ROLE_DASHBOARD = {
    'SUPER_ADMIN': '/super/dashboard/',
    'ADMIN': '/admin/dashboard/',
    'AGENT': '/agent/dashboard/',
    'CLIENT': '/client/dashboard/',
}
_RESET_SALT = 'password-reset'
_RESET_MAX_AGE = 60 * 60 * 24  # 24 hours


def _dashboard_url(user):
    return _ROLE_DASHBOARD.get(user.role, '/login/')


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_url(request.user))

    form = LoginForm(request.POST or None)
    error = None

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])
            return redirect(request.GET.get('next') or _dashboard_url(user))
        error = 'Invalid email or password.'

    return render(request, 'accounts/login.html', {'form': form, 'error': error})


def logout_view(request):
    logout(request)
    return redirect('/login/')


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    success = False

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email, status='ACTIVE')
            token = signing.dumps({'pk': user.pk}, salt=_RESET_SALT)
            reset_url = request.build_absolute_uri(f'/reset-password/{token}/')
            send_mail(
                subject='Reset your LeadPortal password',
                message=(
                    f'Hi {user.first_name or user.email},\n\n'
                    f'Click the link below to reset your password:\n\n'
                    f'{reset_url}\n\n'
                    f'This link expires in 24 hours. If you did not request this, ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass  # Never reveal whether the email exists
        success = True  # Always show success to prevent user enumeration

    return render(request, 'accounts/forgot_password.html', {'form': form, 'success': success})


def reset_password_view(request, token):
    user = None
    invalid = False

    try:
        data = signing.loads(token, salt=_RESET_SALT, max_age=_RESET_MAX_AGE)
        user = User.objects.get(pk=data['pk'])
    except (signing.SignatureExpired, signing.BadSignature, User.DoesNotExist, KeyError):
        invalid = True

    if invalid:
        return render(request, 'accounts/reset_password.html', {'invalid': True})

    form = ResetPasswordForm(request.POST or None)
    success = False

    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['new_password'])
        user.save()
        # set_password() changes the password hash, which Django uses to invalidate
        # all existing sessions automatically via SessionAuthenticationMiddleware
        success = True

    return render(request, 'accounts/reset_password.html', {
        'form': form,
        'success': success,
        'invalid': False,
        'token': token,
    })
