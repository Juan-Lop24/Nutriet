from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
import re

User = get_user_model()

# Validador simple para el nombre de usuario (letras, números y guión bajo)
username_validator = RegexValidator(
    r'^[a-zA-Z0-9_]+$',
    'El nombre de usuario solo puede contener letras, números y guiones bajos.'
)


class RegistroForm(forms.ModelForm):
    # Sobrescribimos username para quitar la validación estricta por defecto de Django
    username = forms.CharField(
        max_length=150,
        required=True,
        validators=[username_validator],
        help_text=None,
        label='Nombre de usuario',
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Contraseña',
    )
    confirmar_password = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirmar contraseña',
    )
    telefono = forms.CharField(
        max_length=10,
        label='Teléfono',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'telefono', 'password', 'confirmar_password']

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe contener al menos una letra mayúscula.')

        if not re.search(r'[a-z]', password):
            raise ValidationError('La contraseña debe contener al menos una letra minúscula.')

        if not re.search(r'[0-9]', password):
            raise ValidationError('La contraseña debe contener al menos un número.')

        if not re.search(r'[\W_]', password):
            raise ValidationError('La contraseña debe contener al menos un carácter especial (como !@#$%).')

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar_password = cleaned_data.get('confirmar_password')

        if password and confirmar_password and password != confirmar_password:
            raise ValidationError('Las contraseñas no coinciden.')

        # Validar número de teléfono (solo 10 dígitos)
        telefono = cleaned_data.get('telefono')
        if telefono and not re.fullmatch(r'\d{10}', telefono):
            raise ValidationError('El número de teléfono debe tener exactamente 10 dígitos.')

        return cleaned_data


class LoginForm(forms.Form):
    email = forms.CharField(
        label='Correo electrónico',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "telefono", "foto_perfil"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name":  forms.TextInput(attrs={"class": "input"}),
            "email":      forms.EmailInput(attrs={"class": "input"}),
            "telefono":   forms.TextInput(attrs={"class": "input"}),
        }


class CambiarPasswordForm(forms.Form):
    password_old     = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
    password_new     = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
