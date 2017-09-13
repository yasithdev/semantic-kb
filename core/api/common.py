from flask import Request


def accepts_json(request: Request) -> bool:
    """
Returns whether a HTTP request accepts a JSON or HTML as output
    :param request: HTTP request object
    :return: true requests accepts JSON. false if accepts HTML)
    """
    return request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
