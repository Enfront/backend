from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import FileData

from shared.exceptions import CustomException


class FileUploadView(APIView):
    def delete(self, request, ref_id):
        if ref_id is None:
            raise CustomException(
                'A file id must be provided',
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            file = FileData.objects.get(ref_id=ref_id)

            file.status = -1
            file.save()
        except FileData.DoesNotExist:
            raise CustomException(
                'A file with id ' + str(ref_id) + ' was not found.',
                status.HTTP_404_NOT_FOUND
            )

        data = {
            'success': True,
            'message': 'A file with pk ' + str(ref_id) + ' was deleted.',
            'data': {},
        }

        return Response(data, status=status.HTTP_204_NO_CONTENT)
