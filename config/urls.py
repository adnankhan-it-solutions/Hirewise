from django.contrib.auth import views as auth_views
from django.urls import path
from hirewise import views

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health, name='health'),
    path('robots.txt', views.robots),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.sign_in, name='login'),
    path('accounts/logout/', views.sign_out, name='logout'),
    path('accounts/verification/', views.verification_pending, name='verification_pending'),
    path('accounts/verify/<str:token>/', views.verify_email, name='verify_email'),
    path('accounts/mfa/', views.mfa, name='mfa'),
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('accounts/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('portal/company/new/', views.company_create, name='company_create'),
    path('portal/company/<uuid:pk>/', views.company_detail, name='company_detail'),
    path('portal/admin/company/<uuid:pk>/', views.company_moderate, name='company_moderate'),
    path('portal/profile/', views.profile, name='profile'),
    path('portal/privacy/', views.privacy, name='privacy_centre'),
    path('pages/<slug:page>/', views.info, name='info'),
]
