from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from oauth2_provider.models import AccessToken, Application
from oauthlib.common import generate_token

from .models import *
import json


class RegisterTestCase(APITestCase):
    def test_customer_cannot_register_with_no_data(self):
        response = self.client.post("/customers/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_register_correctly(self):
        data = {
            "first_name": "Tsvetomir",
            "last_name": "Yotov",
            "username": "yotovtsvetomir@gmail.com",
            "password": "Ceco!123"
        }

        response = self.client.post("/customers/", data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], data['username'])
        self.assertEqual(response.data['user']['first_name'], data['first_name'])
        self.assertEqual(response.data['user']['last_name'], data['last_name'])


class AuthenticationTestCase(APITestCase):

    def setUp(self):
        user = User.objects.create_user(username="t-yotov@teamyotov.com", password="Ceco!123")
        customer = Customer.objects.create(id=1, user=user)

        user = User.objects.create_user(username="yotovtsvetomir@gmail.com", password="Ceco!123")
        customer = Customer.objects.create(id=2, user=user)
        self.user = user

        tok = generate_token()
        app = Application.objects.first()
        access_token = AccessToken.objects.create(
            user=user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(access_token))

    def test_customer_is_authenticated(self):
        response = self.client.get("/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_retrieve_his_data(self):
        response = self.client.get("/customers/2/")
        self.assertEqual(response.data['user']['username'], self.user.username)

    def test_customer_can_see_only_his_data(self):
        # we are trying to get the list of customers, but we are getting only the data of the authenticated customer.
        response = self.client.get("/customers/")
        self.assertEqual(response.data['user']['username'], self.user.username)

    def test_customer_can_not_get_another_customer_data(self):
        # Customer (yotovtsvetomir@gmail.com) is trying to access the data of customer (t-yotov@teamyotov.com)
        response = self.client.get("/customers/1/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_is_not_authenticated(self):
        self.client.credentials()
        response = self.client.get("/customers/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionTestCase(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username="yotovtsvetomir@gmail.com", password="Ceco!123")
        customer = Customer.objects.create(id=1, user=user)
        self.user = user

        tok = generate_token()
        app = Application.objects.first()
        access_token = AccessToken.objects.create(
            user=user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(access_token))

    def test_user_do_not_have_permission(self):
        # the user is not customer, maybe in future we have another type of user(accounting, support ...)
        other_user = User.objects.create_user(
            username="@teamyotov.com", password="Ceco!123")

        tok = generate_token()
        app = Application.objects.first()
        access_token = AccessToken.objects.create(
            user=other_user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(access_token))

        response = self.client.get("/customers/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_verify_email(self):
        response = self.client.get("/verify/email/")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_customer_can_not_create_project_when_not_verified(self):
        data = {
            'title': "TestProject",
            'description': "TestDescription"
        }

        response = self.client.post("/projects/", data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_can_create_project_when_verified(self):
        data = {
            'title': "TestProject",
            'description': "TestDescription"
        }
        Customer.objects.filter(id=1).update(confirm_email=True)
        response = self.client.post("/projects/", data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TasksTestCase(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username="t-yotov@gmail.com", password="Ceco!123")
        customer = Customer.objects.create(id=2, user=user)

        other_user_project = Project.objects.create(
            id=2, title="NotMyProject", description="NotMyDescription", customer=customer)

        user = User.objects.create_user(username="yotovtsvetomir@gmail.com", password="Ceco!123")
        customer = Customer.objects.create(id=1, user=user)
        self.user = user

        project = Project.objects.create(
            id=1, title="MyProject", description="MyDescription", customer=customer)

        task = Task.objects.create(content="TestTask", status="todo", project_id=1)

        tok = generate_token()
        app = Application.objects.first()
        access_token = AccessToken.objects.create(
            user=user, application=app, expires=timezone.now() + relativedelta(hours=1), token=tok)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(access_token))

    def test_customer_create_task_for_his_project(self):
        data = {
            'content': "MyTask",
            'status': "todo",
            'project_id': 1
        }

        response = self.client.post("/tasks/", data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_customer_can_not_create_task_without_content(self):
        data = {
            'status': "todo",
            'project_id': 1
        }

        response = self.client.post("/tasks/", data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_not_create_task_for_other_customer_project(self):
        data = {
            'content': "MyTask",
            'status': "todo",
            'project_id': 2
        }

        response = self.client.post("/tasks/", data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_update_task(self):
        data = {
            'status': "progress"
        }

        response = self.client.patch("/tasks/1/", data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], data['status'])
