"""Lab definition for automation lab"""

class AutomationLab:
    compose_files = ["docker-compose.automation.yml"]
    components = ["nautobot", "awx", "git_server"]

lab = AutomationLab
