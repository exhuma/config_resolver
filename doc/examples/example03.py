import logging
from config_resolver import get_config

logging.basicConfig(level=logging.DEBUG)
cfg = get_config("acmecorp", "bird_feeder", {"version": "1.0"}).config
print(cfg.get('section', 'var'))
