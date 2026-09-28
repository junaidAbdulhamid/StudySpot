import json
import logging


class RedactQueryString(logging.Filter):
    """Uvicorn access records must never retain coordinate query strings."""

    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            args[2] = str(args[2]).split("?", 1)[0]
            record.args = tuple(args)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        )


def configure_logging():
    logging.getLogger("uvicorn.access").addFilter(RedactQueryString())
    logger = logging.getLogger("studyspot")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
