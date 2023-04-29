
class ErrorParsingFeeds(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
    code = 400
    description = "General Parser Error while parsing feeds"


class ErrorParsingHTMLDocument(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

    code = 400
    description = "General Parser Error While parsing HTML document"


class RequestError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
    code = 400
    description = "Error Making Request"
