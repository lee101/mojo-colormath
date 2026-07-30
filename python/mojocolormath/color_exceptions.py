class ColorMathException(Exception):
    pass


class InvalidObserverError(ColorMathException):
    pass


class InvalidIlluminantError(ColorMathException):
    pass


class UndefinedConversionError(ColorMathException):
    def __init__(self, source, target):
        super().__init__(
            f"conversion from {source.__name__} to {target.__name__} is not supported"
        )

