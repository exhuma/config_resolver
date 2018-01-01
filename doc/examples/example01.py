import logging
from config_resolver import get_config

logging.basicConfig(level=logging.DEBUG)
cfg = get_config("acmecorp", "bird_feeder").config
print(cfg.get('section', 'var'))
