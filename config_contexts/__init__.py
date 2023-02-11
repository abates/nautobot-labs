"""Lab definition for config contexts lab"""

class ConfigContextLab:
    compose_files = ["docker-compose.config_contexts.yml"]
    components = ["nautobot", "git_server"]

lab = ConfigContextLab
