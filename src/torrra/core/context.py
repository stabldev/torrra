_config = None


def get_config():
    global _config
    if _config is None:
        from torrra.core.config import Config

        _config = Config()
    return _config
