from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # Fill missing fields with default values
        user.first_name = data.get('first_name') or 'First'
        user.last_name = data.get('last_name') or 'Last'
        user.username = data.get('username') or user.email.split('@')[0]

        return user