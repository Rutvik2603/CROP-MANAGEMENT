
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('new-crop/', views.new_crop, name='new_crop'),
    path('crop/<int:crop_id>/edit/', views.edit_crop, name='edit_crop'),
    path('crop/<int:crop_id>/delete/', views.delete_crop, name='delete_crop'),

    # Forgot Password
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),

    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'
    ),

    path(
    'analyze-crop/',
    views.analyze_crop,
    name='analyze_crop'
),

    path(
        'weather/',
        views.weather_view,
        name='weather'
    ),

]

