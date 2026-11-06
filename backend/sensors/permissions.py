from rest_framework.permissions import BasePermission

CLIENT_HEADER = 'X-Kayvak-Client'
CLIENT_VALUE = 'dashboard'


class HasKayvakHeader(BasePermission):
    """Only requests that carry our custom header may use the API.

    A web page from another site cannot send a custom header to localhost
    without a CORS preflight, and our CORS settings only allow the dashboard's
    own address. This blocks other sites in the same browser (CSRF) from
    driving the local server.
    """

    message = 'Missing or wrong X-Kayvak-Client header.'

    def has_permission(self, request, view):
        return request.headers.get(CLIENT_HEADER) == CLIENT_VALUE