from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Branch
from .serializers import BranchSerializer, MeSerializer


@extend_schema(responses=MeSerializer)
@api_view(["GET"])
def me(request):
    """The signed-in user, with role and branch."""
    return Response(MeSerializer(request.user).data)


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    search_fields = ["code", "name"]
