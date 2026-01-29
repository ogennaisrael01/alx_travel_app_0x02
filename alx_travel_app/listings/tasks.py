from __future__ import absolute_import, unicode_literals

from celery import shared_task

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import  ValidationError
from django.utils import timezone

from .service import send_email
from .models import Products
from .helpers import _genarat_context_for_product_reports

import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def email_notification(context: dict):
    context_copy = context.copy()
    try:
        response = send_email(context_copy)
        if response.status_code == 202:
            logger.debug("Email notification sent to quene. Task Processing....")
    except Exception:
        raise

@shared_task
def products_reports(user):
    """
    Docstring for products_reports
    
    :param user: Generat monthly reports for user products(bookings, reviews, number of purchases)
    """
    
    # check if the passed user is a user instance else return ValidationEror
    if not isinstance(user, User):
        raise ValidationError(_("'user' is  not a valid user instance"))
    products = Products.objects.filter(user=user, created_at__gte=timezone.now() - timezone.timedelta(days=30)
                                       ).select_related("user")
    
    reports = {"email": user.email}
    number_of_products = products.count()
    num_of_bookings = list()
    for product in products:
        noipb = product.bookings.count()
        num_of_bookings.append(noipb)
    # average number of booking across all user products
    averager_boooking = sum(num_of_bookings) / len(num_of_bookings)

    reports.update({"products": number_of_products, "bookings": averager_boooking})
    try:
        context = _genarat_context_for_product_reports(reports)
        email_notification.delay(context)
    except Exception:
        raise
    
    


