from django import forms
from .models import FormularioNutricionGuardado

METAS = [
    ("Aumentar", "Aumentar Masa Muscular"),
    ("Reducir", "Reducir Grasa Corporal"),
    ("Mantener", "Mantener Peso"),
]

FISICO = [
    ("sedentario", "Sedentario (poco o ningún ejercicio)"),
    ("ligero", "Ligero (ejercicio ligero 1-3 días por semana)"),
    ("moderado", "Moderado (ejercicio 3-5 días por semana)"),
    ("intenso", "Intenso (ejercicio intenso 6-7 días por semana)"),
    ("muy_intenso", "Muy intenso (entrenamiento diario o trabajo físico)"),
]

COMIDAS = [
    ("desayuno", "Desayuno"),
    ("almuerzo", "Almuerzo"),
    ("cena", "Cena"),
    ("snack", "Snack"),
]

SEXO = [
    ("M", "Masculino"),
    ("F", "Femenino"),
]

CONDICIONES_MEDICAS = [
    ("", "Sin condición médica"),
    ("diabetes", "Diabetes"),
    ("celiaco", "Celiaco / Sin gluten"),
    ("lactosa", "Intolerancia a la lactosa"),
    ("hipertension", "Hipertensión"),
    ("colesterol", "Colesterol alto"),
    ("dislipidemia", "Dislipidemias / Triglicéridos altos"),
    ("indigestion", "Indigestión / Gastritis / Reflujo"),
    ("hipertiroidismo", "Hipertiroidismo"),
    ("anemia", "Anemia ferropénica"),
    ("gota", "Gota"),
    ("alergia_mani", "Alergia al maní / cacahuate"),
    ("alergia_mariscos", "Alergia a mariscos"),
    ("alergia_huevo", "Alergia al huevo"),
]


class FormularioNutricionForm(forms.ModelForm):
    """
    ModelForm conectado directamente con el modelo FormularioNutricionGuardado.
    IMC y % grasa se calculan automáticamente en el modelo.

    Cambios:
    - Se eliminó tipo_dieta (vegano, keto, etc.)
    - Se agregó condicion_medica: excluye ingredientes automáticamente
    - Se renombró restricciones_alimentarias -> ingredientes_excluidos
    """

    comidas_preferidas = forms.MultipleChoiceField(
        label="¿Qué comidas al día prefieres?",
        choices=COMIDAS,
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    condicion_medica = forms.MultipleChoiceField(
        label="Condición médica o alergia",
        choices=CONDICIONES_MEDICAS,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Si tienes una condición, excluiremos automáticamente los ingredientes no recomendados."
    )

    class Meta:
        model = FormularioNutricionGuardado
        fields = [
            'sexo',
            'edad', 'peso', 'altura',
            'objetivo', 'peso_objetivo', 'plazo_meses',
            'comidas_preferidas', 'nivel_actividad',
            'ingredientes_excluidos',
        ]

        labels = {
            'sexo': 'Sexo',
            'edad': 'Edad',
            'peso': 'Peso actual (kg)',
            'altura': 'Altura (cm)',
            'objetivo': 'Objetivo',
            'peso_objetivo': 'Peso deseado (kg)',
            'plazo_meses': 'Tiempo para alcanzar el objetivo (meses)',
            'nivel_actividad': 'Nivel de actividad física',
            'ingredientes_excluidos': 'Ingredientes que NO quieres en tus recetas',
        }

        widgets = {
            'edad': forms.NumberInput(attrs={"placeholder": "Edad", "class": "form-control"}),
            'peso': forms.NumberInput(attrs={"placeholder": "Peso (kg)", "class": "form-control", "step": "0.01"}),
            'altura': forms.NumberInput(attrs={"placeholder": "Altura (cm)", "class": "form-control", "step": "0.01"}),
            'objetivo': forms.Select(attrs={"class": "form-control"}),
            'peso_objetivo': forms.NumberInput(attrs={"placeholder": "Peso deseado (kg)", "class": "form-control", "step": "0.01"}),
            'plazo_meses': forms.NumberInput(attrs={"placeholder": "Meses", "class": "form-control"}),
            'nivel_actividad': forms.Select(attrs={"class": "form-control"}),
            'ingredientes_excluidos': forms.Textarea(attrs={
                "placeholder": "Ej: arroz, pollo, leche, frijol… separa con comas",
                "rows": 3,
                "class": "form-control"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        edad = cleaned_data.get("edad")
        peso = cleaned_data.get("peso")
        altura = cleaned_data.get("altura")
        objetivo = cleaned_data.get("objetivo")
        peso_objetivo = cleaned_data.get("peso_objetivo")

        errores = []

        if edad and (edad < 10 or edad > 100):
            errores.append("La edad debe estar entre 10 y 100 años.")
        if peso and (peso < 20 or peso > 300):
            errores.append("El peso debe estar entre 20 kg y 300 kg.")
        if altura and (altura < 100 or altura > 250):
            errores.append("La altura debe estar entre 100 cm y 250 cm.")
        if peso_objetivo and (peso_objetivo < 20 or peso_objetivo > 300):
            errores.append("El peso esperado debe estar acorde con tu meta.")

        if peso and peso_objetivo and objetivo:
            if objetivo == 'Reducir' and peso_objetivo >= peso:
                errores.append("Para reducir grasa, el peso objetivo debe ser menor al actual.")
            elif objetivo == 'Aumentar' and peso_objetivo <= peso:
                errores.append("Para aumentar masa, el peso objetivo debe ser mayor al actual.")
            elif objetivo == 'Mantener' and abs(peso_objetivo - peso) > 2:
                errores.append("Para mantener peso, el peso objetivo debe ser muy cercano al actual.")

        if errores:
            raise forms.ValidationError(errores)

        return cleaned_data