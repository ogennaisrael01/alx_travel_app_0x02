from django.urls import path, include
from .views import register, ProductViewSet, PaymentView, PaymentVerifyView
from rest_framework.routers import DefaultRouter
from .reports import genearat_simple_reports

router = DefaultRouter()

router.register(r"products", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", register, name="register"),
    path("auth/", include("rest_framework.urls")),
    path("payment/<uuid:booking_pk>/", PaymentView.as_view(), name="payment"),
    path("payment/verify/<str:tx_ref>/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("reports/", genearat_simple_reports, name="generate-report")
]
