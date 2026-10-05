from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User

class UserCreateForm(BaseUserCreationForm):
    """Форма создания пользователя в админке"""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('personnel_number', 'full_name', 'position', 'department')

class UserEditForm(UserChangeForm):
    """Форма редактирования пользователя"""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
        