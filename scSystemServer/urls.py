"""scSystemServer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from django.conf.urls import url
# from .data_model.main import inferUncertainty
from . import expose_function
from .import test
from . import communi_detection

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test.test_response),
    path('getPersonEvents/', expose_function.getPersonEvents),
    path('init/', expose_function.init),
    path('infer_person/', expose_function.inferPersonsEvent),

    path('getRelatedEvents/', expose_function.getRelatedEvents),   #推荐有可能帮助推断的事件
    path('getAllRelatedEvents/', expose_function.getRelatedEvents),
    
    path('getPersonScore/', expose_function.getPersonScore),
    path('getSimLife/', expose_function.getSimLife),
    path('getRelatedPeopleEvents/', expose_function.getRelatedPeopleEvents),
    path('getPersonRelation/', expose_function.getPersonRelation),
    path('getCommunity/', communi_detection.getCommunity),
    # url(r'^index/$', neo4jQuery.neo4jQuery),
    # url(r'^getPersonDetail/.*$', getPersonDetail.getPersonDetail),
]
