import json
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic import TemplateView, View
from django.template import RequestContext

from .volumes import SFTPVolume, ModelVolume
from .connector import ElFinderConnector


class SFTPManagerView(TemplateView):
    template_name = 'filemanager/file_manager.html'


class SFTPConnectorView(View):
    def get(self, request, *args, **kwargs):
        # coll_id = self.kwargs.get('coll_id')
        volume = SFTPVolume()
        # volume = ModelVolume(coll_id=coll_id)
        finder = ElFinderConnector([volume])
        finder.run(request)

        # Some commands (e.g. read file) will return a Django View - if it
        # is set, return it directly instead of building a response
        if finder.return_view:
            print(finder.return_view)
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