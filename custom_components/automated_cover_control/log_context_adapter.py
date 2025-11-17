import logging


class LogContextAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
        self.config_name = None

    def set_config_name(self, config_name):
        self.config_name = config_name

    def process(self, msg, kwargs):
        if self.config_name:
            return f"[{self.config_name}] {msg}", kwargs
        return f"[unknown] {msg}", kwargs
