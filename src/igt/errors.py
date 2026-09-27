class IgtError(Exception):
    """Base for every expected failure; the CLI maps it to `exit_code`."""

    exit_code = 1


class InvalidUrlError(IgtError):
    exit_code = 2


class ConfigError(IgtError):
    exit_code = 3


class DownloadError(IgtError):
    exit_code = 4


class TranscribeError(IgtError):
    exit_code = 5


class NoSpeechError(TranscribeError):
    pass


class ApiError(IgtError):
    exit_code = 6
