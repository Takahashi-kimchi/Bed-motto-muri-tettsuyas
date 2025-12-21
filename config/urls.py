"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from schedule import views as schedule_views # <-- scheduleアプリのビューをインポート
from django.contrib.auth import views as auth_views 
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 認証関連のURL
    path('accounts/', include('django.contrib.auth.urls')),
    
    # ユーザー登録
    path('accounts/signup/', schedule_views.SignUpView.as_view(), name='signup'),

    # schedule アプリのURLをルートに紐づける
    path('', include('schedule.urls')), 
]