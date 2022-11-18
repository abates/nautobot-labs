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

import glob
import os
import sys
from distutils.util import strtobool

from invoke import Collection
from invoke import task as invoke_task, Task
from invoke.exceptions import Exit

# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_DESIGN_BUILDER_xxx
namespace = Collection("nautobot_lab")
namespace.configure(
    {
        "nautobot_lab": {
            "nautobot_ver": "1.5.0",
            "project_name": "nautobot_lab",
            "python_ver": "3.8",
            "compose_http_timeout": "86400",
            "lab_name": None,
            "docker_files": [],
        }
    }
)


def task(*args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function):
        """Wrapper around invoke.task to add the task to the namespace as well."""

        if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
            # The decorator was called with no arguments
            task_func = invoke_task(function)
        else:
            task_func = invoke_task(*args, **kwargs)(function)
        namespace.add_task(task_func)

        return task_func

    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        return task_wrapper(args[0])

    # The decorator was called with arguments
    return task_wrapper



def compose_files(component):
    basedir = os.path.dirname(__file__)
    component_dir = os.path.join(basedir, component)
    if os.path.exists(component_dir):
        files = []
        sub_components = []
        if os.path.exists(os.path.join(component_dir, "components")):
            with open(os.path.join(component_dir, "components")) as file:
                sub_components = file.read().strip().split("\n")

            for sub_component in sub_components:
                files.extend(compose_files(sub_component))
        files.extend(glob.glob(os.path.join(component_dir, "docker-compose.*.yml")))
        return files

    compose_file = os.path.join(basedir, "docker", f"docker-compose.{component}.yml")
    if os.path.exists(compose_file):
        return [compose_file]

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
        "COMPOSE_HTTP_TIMEOUT": context.nautobot_lab.compose_http_timeout,
        "NAUTOBOT_VER": context.nautobot_lab.nautobot_ver,
        "PYTHON_VER": context.nautobot_lab.python_ver,
    }
    compose_dir = os.path.join(os.path.dirname(__file__), "docker")
    project_name = context.nautobot_lab.project_name + "_" + context.nautobot_lab.lab_name
    compose_command = f'docker-compose --project-name {project_name} --project-directory "{compose_dir}"'
    compose_command += " -f " + (" -f ".join(compose_files(context.nautobot_lab.lab_name)))
    compose_command += f" {command}"
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
            lab_name = context.nautobot_lab.project_name + "_" + context.nautobot_lab.lab_name
            result = context.run(f"docker port {lab_name}_nautobot_1", hide=True, warn=True)
            _, port = result.stdout.rsplit(":", 2)
            url = f"http://127.0.0.1:{port}/"

        if sys.platform == "linux" or sys.platform == "linux2":
            context.run(f"xdg-open {url}", hide=True, warn=True)
        elif sys.platform == "darwin":
            context.run(f"open {url}", hide=True, warn=True)
        elif sys.platform == "win32":
            context.run(f"start {url}", hide=True, warn=True)
    except Exception as ex:
        print(f"\n\nFAILED TO LAUNCH BROWSER: {ex}\n\n")

def is_running(context, container=None):
    docker_compose_status = "ps --services --filter status=running"
    results = docker_compose(context, docker_compose_status, hide="out").stdout.strip()
    if container is None:
        return len(results.stdout) > 0
    return container in results

def run_command(context, command, container="nautobot", **kwargs):
    # Check if nautobot is running, no need to start another nautobot container to run a command
    if is_running(context, container):
        compose_command = f"exec {container} {command}"
    else:
        compose_command = f"run --entrypoint '{command}' {container}"

    docker_compose(context, compose_command, pty=True)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------

@task
def get_current_lab(context, raise_on_not_found=False):
    running_container_ids = context.run('docker ps --filter "label=com.docker.compose.project" -q', hide=True).stdout.strip().split("\n")
    for container_id in running_container_ids:
        project_name = context.run("docker inspect --format='{{index .Config.Labels \"com.docker.compose.project\"}}' " + container_id, hide=True).stdout.strip()
        if project_name.startswith("nautobot_lab_"):
            context.nautobot_lab.lab_name = project_name[len("nautobot_lab_"):]
            return

    if raise_on_not_found:
        raise Exit("The lab is not currently running")
    return None

@task
def start(context, lab_name):
    """Start Nautobot and its dependencies in debug mode."""
    print(f"Starting {lab_name}...", file=sys.stderr)
    context.nautobot_lab.lab_name = lab_name
    docker_compose(context, "up", launch_browser=True)

@task
def config(context, lab_name):
    """Start Nautobot and its dependencies in debug mode."""
    context.nautobot_lab.lab_name = lab_name
    docker_compose(context, "config", launch_browser=True)

@task
def restart(context):
    """Gracefully restart all containers."""
    get_current_lab(context, raise_on_not_found=True)
    print("Restarting Nautobot...", file=sys.stderr)
    docker_compose(context, "restart")


@task
def stop(context):
    """Stop Nautobot and its dependencies."""
    get_current_lab(context, raise_on_not_found=True)
    print("Stopping Nautobot...", file=sys.stderr)
    docker_compose(context, "down")


@task
def destroy(context, lab_name):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...", file=sys.stderr)
    context.nautobot_lab.lab_name = lab_name
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
    get_current_lab(context, raise_on_not_found=True)
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
def shell_plus(context, container="nautobot"):
    """Launch an interactive shell_plus session."""
    get_current_lab(context, raise_on_not_found=True)
    command = "nautobot-server shell_plus"
    run_command(context, command, container=container)


@task(
    help={
        "container": "container to run the command on (default: nautobot)",
    }
)
def cli(context, container="nautobot"):
    """Launch a bash shell inside the running Nautobot container."""
    get_current_lab(context, raise_on_not_found=True)
    run_command(context, "bash -l", container=container)


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    get_current_lab(context, raise_on_not_found=True)
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)

