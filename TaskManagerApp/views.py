from urllib.parse import urlencode

from rest_framework import status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from TaskManagerApp.googleSSOservices import *
from TaskManagerApp.serializers import *
from TaskManagerApp.permissions import *

from django.urls import reverse
from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import urlencode
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password

from oauth2_provider.views.mixins import OAuthLibMixin
from oauth2_provider.models import AccessToken, Application
from oauthlib.common import generate_token

from dateutil.relativedelta import relativedelta


class GoogleLoginApi(OAuthLibMixin, APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        code = serializers.CharField(required=False)
        error = serializers.CharField(required=False)

    def get(self, request, *args, **kwargs):
        input_serializer = self.InputSerializer(data=request.GET)
        input_serializer.is_valid(raise_exception=True)

        validated_data = input_serializer.validated_data

        code = validated_data.get('code')
        error = validated_data.get('error')

        login_url = f'{settings.BASE_FRONTEND_URL}/login'

        if error or not code:
            params = urlencode({'error': error})
            return redirect(f'{login_url}?{params}')

        redirect_uri = 'http://localhost:8000/google/auth/'

        access_token = google_get_access_token(code=code, redirect_uri=redirect_uri)

        user_data = google_get_user_info(access_token=access_token)

        profile_data = {
            'email': user_data['email'],
            'first_name': user_data['given_name'],
            'last_name': user_data['family_name'],
        }

        dj_data = {}
        dj_data['username'] = profile_data['email']
        dj_data['first_name'] = profile_data['first_name']
        dj_data['last_name'] = profile_data['last_name']
        dj_data['is_active'] = True
        dj_data['password'] = User.objects.make_random_password()
        serializer = UserSerializer(data=dj_data)

        if User.objects.filter(username=dj_data['username']).exists():
            pass
        elif serializer.is_valid():
            user = User.objects.create_user(**dj_data)
            user.save()
            customer = Customer.objects.create(user=User.objects.get(
                username=dj_data['username']), confirm_email=True)

        tok = generate_token()
        app = Application.objects.first()
        user = User.objects.get(username=user_data['email'])
        access_token = AccessToken.objects.create(
            user=user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

        final = {"access_token": access_token}

        return redirect(settings.BASE_FRONTEND_URL + '/google?' + urlencode(final))


class VerifyEmail(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        Customer.objects.filter(user__id=request.user.id).update(confirm_email=True)

        return Response({"success": "Email has been successfuly verified."}, status=status.HTTP_202_ACCEPTED)


class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cp = request.data['current_password']
        np = request.data['new_password']

        if cp == np:
            return Response({'error': 'Current and new password are the same'})
        elif check_password(cp, User.objects.get(username=request.user).password):
            User.objects.filter(username=request.user).update(password=make_password(np))
            return Response({'success': 'Password was successfuly changed.'})
        else:
            return Response({'error': 'Wrong current password.'})


class ResetChangePassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        np = request.data['new_password']
        if check_password(np, User.objects.get(username=request.user).password):
            return Response({'success': 'Password successfuly changed.'})
        else:
            User.objects.filter(username=request.user).update(password=make_password(np))


class ResetPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if User.objects.filter(username=request.data['username']).exists():
            user = User.objects.get(username=request.data['username'])

            tok = generate_token()
            app = Application.objects.first()
            access_token = AccessToken.objects.create(
                user=user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

            response = send_mail(
                subject='Ресет на паролата',
                message="" + settings.BASE_FRONTEND_URL + "/reset/password/" + str(access_token),
                from_email='tasskmanager@gmail.com',
                recipient_list=[user.username],
                fail_silently=False,
            )

            return Response({'success': 'Confirmation link has been sent to your email.'})
        else:
            return Response({'error': 'Account does not exist.'})
