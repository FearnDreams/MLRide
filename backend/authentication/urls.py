from django.urls import path
from .views import RegisterView, LoginView, LogoutView, CSRFTokenView, UserProfileView, UserUpdateView, UserDeleteView, CurrentUserView

app_name = 'authentication'

urlpatterns = [
    path('csrf-token/', CSRFTokenView.as_view(), name='csrf-token'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/', CurrentUserView.as_view(), name='current-user'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
    path('profile/delete/', UserDeleteView.as_view(), name='profile-delete'),
]