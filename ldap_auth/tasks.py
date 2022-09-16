"""Tasks for use with Invoke.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
from distutils.util import strtobool

from invoke import Collection
from invoke import task as invoke_task


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_DESIGN_BUILDER_xxx
namespace = Collection("lab")
namespace.configure(
    {
        "lab": {
            "nautobot_ver": "1.4.2",
            "project_name": "lab_ldap",
            "python_ver": "3.8",
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "docker"),
            "compose_files": [
                "docker-compose.base.yml",
                "docker-compose.redis.yml",
                "docker-compose.postgres.yml",
                "docker-compose.lab.yml",
            ],
            "compose_http_timeout": "86400",
        }
    }
)


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    build_env = {
        # Note: 'docker-compose logs' will stop following after 60 seconds by default,
        # so we are overriding that by setting this environment variable.
        "COMPOSE_HTTP_TIMEOUT": context.lab.compose_http_timeout,
        "NAUTOBOT_VER": context.lab.nautobot_ver,
        "PYTHON_VER": context.lab.python_ver,
    }
    compose_command = f'docker-compose --project-name {context.lab.project_name} --project-directory "{context.lab.compose_dir}"'
    for compose_file in context.lab.compose_files:
        compose_file_path = os.path.join(context.lab.compose_dir, compose_file)
        compose_command += f' -f "{compose_file_path}"'
    compose_command += f" {command}"
    print(f'Running docker-compose command "{command}"', file=sys.stderr)

    class Streamer:
        def write(self, b):
            if "Nautobot initialized!" in b:
                launch_browser(context)
            return sys.stdout.write(b)

        def __getattr__(self, attr):
            return getattr(sys.stdout, attr)

    streamer = None
    if kwargs.pop("launch_browser", False):
        streamer = Streamer()
    return context.run(compose_command, env=build_env, out_stream=streamer, **kwargs)


def launch_browser(context, url=None):
    try:
        if url is None:
            result = context.run(f"docker port {context.lab.project_name}_nautobot_1", hide=True, warn=True)
            _, port = result.stdout.rsplit(":", 2)
            url = f"http://127.0.0.1:{port}/"

        if sys.platform == "linux" or sys.platform == "linux2":
            context.run(f"xdg-open {url}", hide=True, warn=True)
        elif sys.platform == "darwin":
            context.run(f"open {url}", hide=True, warn=True)
        elif sys.platform == "win32":
            context.run(f"start {url}", hide=True, warn=True)
    except Exception as ex:
        print(f"\n\nWARNING: {ex}\n\n")

def run_command(context, command, container="nautobot", **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    if is_truthy(context.lab.local):
        context.run(command, **kwargs)
    else:
        # Check if nautobot is running, no need to start another nautobot container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")
        if container in results.stdout:
            compose_command = f"exec {container} {command}"
        else:
            compose_command = f"run --entrypoint '{command}' {container}"

        docker_compose(context, compose_command, pty=True)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot in debug mode...", file=sys.stderr)
    docker_compose(context, "up", launch_browser=True)


@task
def start(context):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...", file=sys.stderr)
    docker_compose(context, "up --detach", launch_browser=True)


@task
def restart(context):
    """Gracefully restart all containers."""
    print("Restarting Nautobot...", file=sys.stderr)
    docker_compose(context, "restart")


@task
def stop(context):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot...", file=sys.stderr)
    docker_compose(context, "down")


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...", file=sys.stderr)
    docker_compose(context, "down --volumes")


@task(
    help={
        "service": "Docker-compose service name to view (default: nautobot)",
        "follow": "Follow logs",
        "tail": "Tail N number of lines or 'all'",
    }
)
def logs(context, service="nautobot", follow=False, tail=None):
    """View the logs of a docker-compose service."""
    command = "logs "

    if follow:
        command += "--follow "
    if tail:
        command += f"--tail={tail} "

    command += service
    docker_compose(context, command)


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task(
    help={
        "container": "container to run the command on (default: nautobot)",
    }
)
def nbshell(context, container="nautobot"):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"
    run_command(context, command, container=container)


@task(
    help={
        "container": "container to run the command on (default: nautobot)",
    }
)
def shell_plus(context, container="nautobot"):
    """Launch an interactive shell_plus session."""
    command = "nautobot-server shell_plus"
    run_command(context, command, container=container)


@task(
    help={
        "container": "container to run the command on (default: nautobot)",
    }
)
def cli(context, container="nautobot"):
    """Launch a bash shell inside the running Nautobot container."""
    run_command(context, "bash", container=container)


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command)


@task(help={})
def post_upgrade(context):
    """
    Performs Nautobot common post-upgrade operations using a single entrypoint.

    This will run the following management commands with default settings, in order:

    - migrate
    - trace_paths
    - collectstatic
    - remove_stale_contenttypes
    - clearsessions
    - invalidate all
    """
    command = "nautobot-server post_upgrade"

    run_command(context, command)

@task
def shell(context):
    """Start a shell on the nautobot docker instance."""
    run_command(context, "bash")
