from rest_framework.decorators import api_view
from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from .models import Bookings
from .serializers import (
    BookingsOutSerializer, 
    BookingSerializer, 
    RegisterSerializer, 
    LoginSerializer,
    ProductCreateSerializer,
    ProductOutSerializer,
    PaymentSerializer, 
)
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.request import Request
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from .models import Products, Payments
from rest_framework.pagination import CursorPagination
import secrets
from .helpers import get_booking_by_id, get_payment_by_tx_ref
from .payments import payment_init, payment_verify

class CustomPagination(CursorPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
    ordering = ["-created_at"]


@api_view(["POST"])
def register(request: Request):
    if request.method == "POST":
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED, data={
            "success":True,
            "message": "Registration successful",
            "user_id": serializer.data
        })

    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ["bookings__user"]
    search_fields = []
    pagination_class = CustomPagination

    def check_object_permission(self, request: Request, product_obj):
        if product_obj.user != request.user:
            raise PermissionDenied("Permission denied: you can't perform this action")
        return True
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        product_obj = self.get_object()
        if self.check_object_permission(request, product_obj):
            serializer = self.get_serializer(product_obj, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.validated_data) 
        

    def destroy(self, request, *args, **kwargs):
        product_obj = self.get_object()
        if self.check_object_permission(request, product_obj):
            self.perform_destroy(product_obj)  
        return Response(status=status.HTTP_204_NO_CONTENT)

    queryset = (
        Products.objects.select_related(
            "user"
        ).prefetch_related(
            "bookings", "reviews"
        )
    )
    def get_queryset(self):
        return self.queryset.all().order_by("-created_at")
    
    def get_serializer_class(self):
        if self.action in ("create", "update", "patch", "destroy"):
            return ProductCreateSerializer
        return ProductOutSerializer
    
class PaymentView(APIView):
    http_method_names = ["post"]

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_pk=None):
        booking_dict = get_booking_by_id(booking_pk)

        if booking_dict.get("status") == "success":
            booking = booking_dict.get("booking")
        serializer = self.serializer_class(data=request.data, context={"request": request, "booking": booking})
        serializer.is_valid(raise_exception=True)
        pmt_ref = f"ref_{secrets.token_urlsafe(30)}"
        if Payments.objects.filter(pmt_ref=pmt_ref).exists():
            pmt_ref = f"ref_{secrets.token_urlsafe(30)}"
        email = request.user.email
        first_name = request.user.first_name if request.user.first_name else email[:5]
        last_name = request.user.last_name if request.user.last_name else email[5:]
        phone = request.user.phone_number if request.user.phone_number else None
        amount = 0
        pmt_choices = ["FULL_PAYMENT", "PAY_PERNIGHT"]
        pmt_size = serializer.validated_data.get("pmt_size")
        if pmt_size == pmt_choices[0]:
            amount = float(booking.product.price)
        elif pmt_size == pmt_choices[1]:
            amount = float(booking.product.price_per_night)
        else:
            amount = None
            raise NotFound("amount not  provided")
        try:
            initiate_payment = payment_init(
                email=email, 
                amount=amount,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                pmt_ref=pmt_ref
            )
        except Exception:
            raise

        if initiate_payment.get("status") in ("Failed", False, "failed", "FAILED"):
            return Response(data={
                "status": False,
                "message": initiate_payment.get("message")
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment = Payments.objects.create(
            amount=amount,
            pmt_ref=pmt_ref,
            user=request.user,
            email=email,
            booking=booking
        )
        return Response(initiate_payment, status=status.HTTP_200_OK)

class PaymentVerifyView(APIView):
    http_method_names = ["get"] 
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, tx_ref=None):
        payment_obj = get_payment_by_tx_ref(tx_ref=tx_ref, user=request.user)
        if payment_obj.get("status") != "success":
            return Response({"status": False,  "message": "failed to get payment object"}, status=status.HTTP_400_BAD_REQUEST)
        payment = payment_obj.get("payment", None)
        payments_verify = payment_verify(payment.pmt_ref.strip())
        if not payments_verify.get("status") in ("success", True, "SUCCESS"):
            return Response({ "status": False, "message": "Failed to fetch chapa data"}, status=status.HTTP_502_BAD_GATEWAY)
        payment_method = payments_verify.get("data")["method"]
        p_status = payments_verify.get("data")["status"].split("/")
        amount = f"{payments_verify.get("data")["amount"]:.2f}"
        if amount != str(payment.booking.product.price_per_night) and amount != str(payment.booking.product.price):
            return Response({ "status": False, "message": "Amount mismatch"}, status=status.HTTP_400_BAD_REQUEST)
        if p_status[0] in ("success", "SUCCESS", "Success") and p_status[1] in ("completed", "COMPLETED", "Completed"):
            payment.pmt_status = Payments.PaymentStatus.COMPLETED
        else:
            payment.pmt_status = Payments.PaymentStatus.FAILED
        payment.pmt_method = payment_method
        payment.save(update_fields=["pmt_status", "pmt_method"])
        return Response({"status": True, "message": "Payment verified successfully", "payment_status": payment.pmt_status
        }, status=status.HTTP_200_OK)



        