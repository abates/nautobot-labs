from os import path
from lab_builder import config
from lab_builder.adapters import Adapter
from lab_builder.lab import LinuxNode, NetworkNode
from lab_builder.config import HealthCheck

class CEOS(NetworkNode):
    """Arista Containerized EOS node."""
    node_config = config.NodeConfig(
        kind="ceos",
        image="ceos:4.28.9M",
        cli=config.Command("Cli", True),
        shell=config.Command("/bin/bash", True),
    )


class DB(LinuxNode):
    """PostgreSQL database node."""

    node_config = config.NodeConfig(
        image="postgres:13",
        health_check=config.HealthCheck(
            interval=10,
            timeout=5,
            retries=10,
            test=["CMD-SHELL", "pg_isready --username=$$POSTGRES_USER --dbname=$$POSTGRES_DB"],
        ),
        environment=config.Environment({
            "POSTGRES_PASSWORD": "{NAUTOBOT_DB_PASSWORD}",
            "POSTGRES_USER": "{NAUTOBOT_DB_USER}",
            "POSTGRES_DB": "{NAUTOBOT_DB_NAME}",
            "PGPASSWORD": "{NAUTOBOT_DB_PASSWORD}",
        }),
        binds=config.Binds(config.NamedBind(name="data", mount_point="/var/lib/postgresql/data")),
        cli=config.Command("psql", True),
        shell=config.Command("/bin/bash", True),
    )


class Redis(LinuxNode):
    """Redis node."""

    node_config=config.NodeConfig(
        image="redis:6-alpine",
        command='sh -c "redis-server --loglevel debug --appendonly yes --requirepass $$REDIS_PASSWORD"',
        environment=config.Environment({
            "REDIS_PASSWORD": "{NAUTOBOT_REDIS_PASSWORD}"
        }),
    )

class GitServer(LinuxNode):
    """Simple git server node."""

    node_config = config.NodeConfig(
        containerfile=path.join(path.dirname(__file__), "containers/git-server/Containerfile"),
        binds=config.Binds(config.NamedBind(name="repos", mount_point="/internal/repos")),
        shell=config.Command("/bin/ash", True),
    )

    def started(self):
        super().started()
        adapter = self.lab.adapter
        adapter.exec(self, config.Command(["git", "config", "--global", "user.email", "operator@company.com"]))
        adapter.exec(self, config.Command(["git", "config", "--global", "user.name" "Operator"]))
        for repo_name in self.list_dir("/repos"):
            if not self.path_exists(f"/internal/repos/{repo_name}.git"):
                print(f"/internal/repos/{repo_name}.git does not exist")
                adapter.exec(self, config.Command([
                    "git", "init", "--bare", f"/internal/repos/{repo_name}.git", "--initial-branch=main",
                ]))

                adapter.exec(self, config.Command(["cp", "-r", f"/repos/{repo_name}", f"/tmp/{repo_name}"]))
                adapter.exec(self, config.Command(["git", "init"], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["git", "add", "."], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["git", "commit", "-m", "Initial Commit"], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["git", "branch", "-M", "main"], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["git", "remote", "add", "origin", f"/internal/repos/{repo_name}.git"], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["git", "push", "-u", "origin", "main"], working_directory=f"/tmp/{repo_name}"))
                adapter.exec(self, config.Command(["chown", "-R", "git", f"/internal/repos/{repo_name}.git"]))
