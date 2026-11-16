from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class AdminRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8
    )

    class Meta:
        model = User

        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email address is already registered."
            )

        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):

        password = validated_data.pop('password')

        admin_user = User.objects.create_user(
            password=password,
            is_staff=True,
            is_superuser=False,
            **validated_data
        )

        return admin_user


from rest_framework import serializers
from .models import Customer


class CustomerRegistrationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer

        fields = [
            'id',
            'name',
            'email',
            'phone',
            'address',
        ]

        read_only_fields = ['id']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Customer name is required."
            )

        return value.strip()

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain digits only."
            )

        if len(value) != 10:
            raise serializers.ValidationError(
                "Phone number must be exactly 10 digits."
            )

        return value
