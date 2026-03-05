# /tu_app_de_usuarios/adapters.py (Usando django-allauth)

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # La información del número de teléfono suele estar en el 'extra_data'
        phone_number = sociallogin.account.extra_data.get('phone_number') 

        if phone_number:
            # Asumiendo que tu modelo tiene un campo llamado 'telefono'
            user.telefono = phone_number
            user.save()
            
        return user