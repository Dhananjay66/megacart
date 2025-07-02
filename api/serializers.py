from rest_framework import serializers
from store.models import Product
from accounts.models import Account, UserProfile
from category.models import Category
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'password']

    def create(self, validated_data):
        username = validated_data['email'].split('@')[0]
        user = Account.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            username=username,
            password=validated_data['password']
        )
        user.phone_number = validated_data['phone_number']
        user.save()

        # Create default profile
        profile = UserProfile()
        profile.user_id = user.id
        profile.profile_picture = 'default/default-user.png'
        profile.save()

        return user