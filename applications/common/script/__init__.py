from flask import Flask

from .admin import admin_cli
from .question import question_cli


def init_script(app: Flask):
    app.cli.add_command(admin_cli)
    app.cli.add_command(question_cli)
