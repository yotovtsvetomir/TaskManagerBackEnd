from TaskManagerApp.serializers import *
from TaskManagerApp.permissions import *

from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from urllib.parse import urlencode
from oauthlib.common import generate_token
from oauth2_provider.models import AccessToken, Application
from oauth2_provider.views.mixins import OAuthLibMixin

from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django_filters.rest_framework import DjangoFilterBackend

from dateutil.relativedelta import relativedelta

from validate_email import validate_email


class CustomerPaginations(PageNumberPagination):
    def get_paginated_response(self, data):
        if self.page.paginator.count == 1:
            return Response(data[0])
        else:
            return Response({
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'count': self.page.paginator.count,
                'results': data
            })


class CustomerViewSet(OAuthLibMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomerPaginations

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsCustomer]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = Customer.objects.all()
        if self.request.user.is_superuser:
            return qs.order_by('-id')
        else:
            return qs.filter(user_id=self.request.user.id).order_by('-id')

    def create(self, request):
        data = request.data
        data['is_active'] = True
        serializer = UserSerializer(data=data)

        if serializer.is_valid():
            if User.objects.filter(username=data['username']).exists() == True:
                return Response(status=status.HTTP_409_CONFLICT)
            elif serializer.is_valid():
                '''is_valid = validate_email(
                    email_address=data['username'],
                    check_format=False,
                    check_blacklist=True,
                    check_dns=True,
                    dns_timeout=1,
                    check_smtp=True,
                    smtp_timeout=1,
                    smtp_helo_host='smtp.gmail.com',
                    smtp_from_address='tasskmanager@gmail.com',
                    smtp_skip_tls=False,
                    smtp_tls_context=None,
                    smtp_debug=True)'''
                is_valid = None

                if is_valid == True or is_valid == None:
                    user = User.objects.create_user(**data)
                    user.save()
                    customer = Customer.objects.create(
                        user=User.objects.get(username=data['username']))

                    tok = generate_token()
                    app = Application.objects.first()
                    access_token = AccessToken.objects.create(user=User.objects.get(
                        username=data['username']), application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

                    response = send_mail(
                        subject='Потвърждаване на имейл',
                        message="Верификация тук: " + settings.BASE_FRONTEND_URL +
                        "/verify/" + str(access_token),
                        from_email='tasskmanager@gmail.com',
                        recipient_list=[user.username],
                        fail_silently=False,
                    )

                    return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
                else:
                    return Response(data={"error": "Email is fake"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsCustomer]

    def get_queryset(self):
        qs = Project.objects.all()
        if self.request.user.is_superuser:
            return qs
        else:
            return qs.filter(customer__user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        data = request.data
        customer = Customer.objects.get(user__id=request.user.id)

        if customer.confirm_email == True:
            serializer = ProjectSerializer(data=data)

            if serializer.is_valid():
                ad = Project.objects.create(customer=customer, **serializer.validated_data)

            return Response(ProjectSerializer(ad).data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Email not confirmed"}, status=status.HTTP_403_FORBIDDEN)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsCustomer]

    def get_queryset(self):
        qs = Task.objects.all()
        if self.request.user.is_superuser:
            return qs
        else:
            return qs.filter(project__customer__user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        data = request.data
        if Project.objects.filter(id=data['project_id'], customer__user__id=self.request.user.id).exists():
            project = Project.objects.get(
                id=data['project_id'], customer__user__id=self.request.user.id)
            del data['project_id']
            serializer = TaskSerializer(data=data)

            if serializer.is_valid():
                ad = Task.objects.create(project=project, **serializer.validated_data)
                return Response(TaskSerializer(ad).data, status=status.HTTP_201_CREATED)
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data={"error": "You can't add task in someone else's project"}, status=status.HTTP_403_FORBIDDEN)
