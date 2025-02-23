from django.urls import path
from .views import RegisterView, LoginView, LogoutView, CSRFTokenView

app_name = 'authentication'

urlpatterns = [
    path('csrf-token/', CSRFTokenView.as_view(), name='csrf-token'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]