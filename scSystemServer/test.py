from django.http import HttpResponse
import json

def test_response(request):
    data = {'info': 'success'}
    return HttpResponse(json.dumps(data))