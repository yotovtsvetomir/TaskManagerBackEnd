from django.contrib.auth.models import User
from rest_framework import serializers
from TaskManagerApp.models import *
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=False)
    username = serializers.EmailField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'password', 'is_active', 'is_staff')
        read_only_fields = ('is_active', 'is_staff')
        extra_kwargs = {
            'password': {'write_only': True}
        }

class UserShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id']


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)

    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['confirm_email']

    def update(self, instance, validated_data):
        if validated_data.get('user'):
            user_data = validated_data.get('user')
            instance.user.first_name = user_data['first_name']
            instance.user.last_name = user_data['last_name']
            instance.user.save()

        del validated_data['user']
        return super(CustomerSerializer, self).update(instance, validated_data)


class CustomerShortSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(required=False)

    class Meta:
        model = Customer
        fields = ['id', 'user']

class ProjectShortSerializer(serializers.ModelSerializer):
    customer = CustomerShortSerializer(required=False)

    class Meta:
        model = Project
        fields = ['id', 'customer']

class TaskSerializer(serializers.ModelSerializer):
    project = ProjectShortSerializer(required=False)

    class Meta:
        model = Task
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    customer = CustomerShortSerializer(required=False)
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'

    def get_tasks(self, instance):
        return TaskSerializer(Task.objects.filter(project__id=instance.id), many=True).data
