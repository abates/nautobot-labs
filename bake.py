#!/usr/bin/env python3

from copy import copy
from os import path
import sys

import click
from cookiecutter.generate import generate_files

base_dir = path.dirname(__file__)
template_dir = path.join(base_dir, "cookie-cutter")

class _patch_import_path:
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self._path = None

    def __enter__(self):
        self._path = copy(sys.path)
        sys.path.append(self.template_dir)

    def __exit__(self, type, value, traceback):
        sys.path = self.template_dir

import_patch = _patch_import_path(template_dir)

click.echo("Enter the lab name using snake_case:")
lab_name = click.prompt("Lab Name", "lab_name")

done = False
services = []
images = []
click.echo("Enter additional docker services (blank to end):")
while not done:
    service = click.prompt("Service", "", show_default=False)
    if service:
        image = None
        while not image:
            image = click.prompt(f"Image for {service}", "", show_default=False)
            if not image:
                click.echo("Image cannot be blank")
        services.append(service)
        images.append(image)
    else:
        done = True

context = {
    "cookiecutter": {
        "lab_name": lab_name,
        "additional_services": services,
        "additional_images": images,
    }
}

result = generate_files(
    repo_dir=template_dir,
    context=context,
    overwrite_if_exists=False,
    skip_if_file_exists=False,
    output_dir=base_dir,
    accept_hooks=True,
)
