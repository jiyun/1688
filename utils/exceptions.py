class ScraperError(Exception):
    pass


class ParseError(ScraperError):
    def __init__(self, message: str, url: str = None):
        super().__init__(message)
        self.url = url


class DownloadError(ScraperError):
    def __init__(self, message: str, url: str = None, retryable: bool = False):
        super().__init__(message)
        self.url = url
        self.retryable = retryable


class DatabaseError(ScraperError):
    pass


class BrowserError(ScraperError):
    pass


class ConfigError(ScraperError):
    pass


class ImageProcessError(ScraperError):
    pass


class ImportError_(ScraperError):
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path
