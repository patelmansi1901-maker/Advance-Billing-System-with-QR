from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import (
    SessionAuthentication,
    BasicAuthentication
)

from .serializers import AdminRegistrationSerializer


class AdminRegistrationAPIView(generics.CreateAPIView):

    serializer_class = AdminRegistrationSerializer

    permission_classes = [IsAdminUser]

    authentication_classes = [
        SessionAuthentication,
        BasicAuthentication
    ]