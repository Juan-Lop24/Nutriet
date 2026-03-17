from django import forms
from .models import MedicionFisica
class FormularioMedicion(forms.ModelForm):

    class Meta:
        model = MedicionFisica
        fields = ['peso']
        widgets = {
            'peso': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Peso en kg'
            }),
        }
        labels = {
            'peso': 'Peso (kg)',
        }

    def clean_peso(self):
        peso = self.cleaned_data.get("peso")

        if peso > 200:
            raise forms.ValidationError(
                "El peso no puede ser mayor a 200 kg."
            )

        if peso <= 0:
            raise forms.ValidationError(
                "El peso debe ser mayor que 0."
            )
        if peso < 40:
            raise forms.ValidationError("El peso no puede ser menor a 40 kg.")

        return peso
