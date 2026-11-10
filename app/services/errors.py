"""Domain errors raised by the service layer.

They subclass ValueError so the existing HTML views, which catch ValueError
and show the message to the user, keep working unchanged. The JSON API uses
the subclass to choose the HTTP status code.
"""


class ServiceError(ValueError):
    status_code = 400


class InvalidInputError(ServiceError):
    status_code = 400


class PermissionDeniedError(ServiceError):
    status_code = 403


class NotFoundError(ServiceError):
    status_code = 404


class ConflictError(ServiceError):
    status_code = 409
