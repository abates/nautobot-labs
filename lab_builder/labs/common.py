import os
import shutil
from lab_builder.node import HealthCheck, LinuxNode


class DB(LinuxNode):
    """PostgreSQL database node."""

    image = "postgres:13"
    health_check = HealthCheck(
      interval=10,
      timeout=5,
      retries=10,
      test=["CMD-SHELL", "pg_isready --username=$$POSTGRES_USER --dbname=$$POSTGRES_DB"],
    )

    environment = {
        "POSTGRES_PASSWORD": "{NAUTOBOT_DB_PASSWORD}",
        "POSTGRES_USER": "{NAUTOBOT_DB_USER}",
        "POSTGRES_DB": "{NAUTOBOT_DB_NAME}",
        "PGPASSWORD": "{NAUTOBOT_DB_PASSWORD}",
    }

    binds = ["data:/var/lib/postgresql/data"]


class Redis(LinuxNode):
    """Redis node."""

    image = "redis:6-alpine"
    command = 'sh -c "redis-server --loglevel debug --appendonly yes --requirepass $$REDIS_PASSWORD"'
    environment = {
        "REDIS_PASSWORD": "{NAUTOBOT_REDIS_PASSWORD}"
    }

class GitServer(LinuxNode):
    """Simple git server node."""

    containerfile = "containers/git-server/Containerfile"

    binds = [
        "repos:/internal/repos",
    ]

    def started(self):
        super().started()
        self.run_cmd(["git", "config", "--global", "user.email", "operator@company.com"])
        self.run_cmd(["git", "config", "--global", "user.name" "Operator"])
        for repo_name in self.list_dir("/repos"):
            if not self.path_exists(f"/internal/repos/{repo_name}.git"):
                print(f"/internal/repos/{repo_name}.git does not exist")
                self.run_cmd([
                    "git", "init", "--bare", f"/internal/repos/{repo_name}.git", "--initial-branch=main",
                ])

                self.run_cmd(["cp", "-r", f"/repos/{repo_name}", f"/tmp/{repo_name}"])
                self.run_cmd(["git", "init"], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["git", "add", "."], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["git", "commit", "-m", "Initial Commit"], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["git", "branch", "-M", "main"], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["git", "remote", "add", "origin", f"/internal/repos/{repo_name}.git"], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["git", "push", "-u", "origin", "main"], working_directory=f"/tmp/{repo_name}")
                self.run_cmd(["chown", "-R", "git", f"/internal/repos/{repo_name}.git"])