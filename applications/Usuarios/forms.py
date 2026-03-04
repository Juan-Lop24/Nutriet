from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator # <-- NUEVA IMPORTACIÓN
import re

User = get_user_model()



# Define un validador simple para el nombre de usuario
# Permite letras, números y guiones bajos (opcional, si quieres solo letras y números, quita el '_')
username_validator = RegexValidator(
    r'^[a-zA-Z0-9_]+$', # Solo letras (mayús/minús), números y guion bajo
    'El nombre de usuario solo puede contener letras, números y guiones bajos.'
)


class RegistroForm(forms.ModelForm):
    # SOBRESCRIBIR USERNAME para quitar la validación estricta por defecto
    username = forms.CharField(
        max_length=150,
        required=True,
        # Aplicamos el validador más simple
        validators=[username_validator],
        # Eliminamos el help_text para que no se muestre
        help_text=None 
    )
    
    password = forms.CharField(widget=forms.PasswordInput)
    confirmar_password = forms.CharField(widget=forms.PasswordInput)
    telefono = forms.CharField(max_length=10)

    class Meta:
        # Asegúrate de que los campos coincidan con los de la clase
        model = User
        fields = ['username', 'email', 'telefono', 'password', 'confirmar_password']

    def clean_password(self):
        password = self.cleaned_data.get('password')

        # ... (Tu validación de contraseña se mantiene igual) ...
        # Validar longitud
        if len(password) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')

        # Validar mayúsculas
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe contener al menos una letra mayúscula.')

        # Validar minúsculas
        if not re.search(r'[a-z]', password):
            raise ValidationError('La contraseña debe contener al menos una letra minúscula.')

        # Validar números
        if not re.search(r'[0-9]', password):
            raise ValidationError('La contraseña debe contener al menos un número.')

        # Validar símbolos especiales
        if not re.search(r'[\W_]', password):
            raise ValidationError('La contraseña debe contener al menos un carácter especial (como !@#$%).')

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar_password = cleaned_data.get('confirmar_password')

        if password and confirmar_password and password != confirmar_password:
            # Este mensaje ahora aparecerá bajo 'No field errors' o como error global.
            raise ValidationError('Las contraseñas no coinciden.')

        # Validar número de teléfono (solo 10 dígitos)
        telefono = cleaned_data.get('telefono')
        if telefono and not re.fullmatch(r'\d{10}', telefono):
            # Este error de validación del campo 'telefono' también aparecerá debajo del campo.
            raise ValidationError('El número de teléfono debe tener exactamente 10 dígitos.')

        return cleaned_data

class LoginForm(forms.Form ):

    email = forms.CharField(
        label='email',
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
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "telefono": forms.TextInput(attrs={"class": "input"}),
        }


class CambiarPasswordForm(forms.Form):
    password_old = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
    password_new = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}))

