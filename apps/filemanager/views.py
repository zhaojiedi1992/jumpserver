import json
from django.http import HttpResponse
from django.shortcuts import render_to_response, render
from django.views.generic import TemplateView, DetailView, View
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt

from .volumes import ModelVolume, SFTPVolume
from .connector import ElFinderConnector
from .models import FileCollection


class ModelFileManagerView(TemplateView):
    template_name = 'filemanager/model_file_manager.html'


class ModelVolumeConnectorView(View):
    def get(self, request, *args, **kwargs):
        volume = SFTPVolume()
        # volume = SFTPVolume.get_volume(request)
        # model_volume = ModelVolume(**data)
        finder = ElFinderConnector([volume])
        finder.run(request)

        # Some commands (e.g. read file) will return a Django View - if it
        # is set, return it directly instead of building a response
        if finder.return_view:
            return finder.return_view

        response = HttpResponse(content_type=finder.httpHeader['Content-type'])
        response.status_code = finder.httpStatusCode
        if finder.httpHeader['Content-type'] == 'application/json':
            response.content = json.dumps(finder.httpResponse)
        else:
            response.content = finder.httpResponse

        return response

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


def read_file(request, volume, file_hash, template="read_file.html"):
    """ Default view for responding to "open file" requests.

        coll: FileCollection this File belongs to
        file: The requested File object
    """
    return render_to_response(template,
                              {'file': file_hash},
                              RequestContext(request))