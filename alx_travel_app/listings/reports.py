from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from rest_framework.response import Response

from .tasks import products_reports

@permission_classes(permission_classes=[permissions.IsAuthenticated])
@api_view(http_method_names=["get"])
def genearat_simple_reports(request):
    if request.method == "GET":
        user = request.user
        products_reports.delay(user)

    return Response("Report sent to user")
    
