from config_resolver import get_config

cfg = get_config("bird_feeder", "acmecorp")
print(cfg.meta)
