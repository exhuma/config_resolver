from config_resolver import get_config

cfg = get_config("acmecorp", "bird_feeder")
print(cfg.meta)
