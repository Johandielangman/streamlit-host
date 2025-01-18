# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
#      /\_/\
#     ( o.o )
#      > ^ <
#
# Author: Johan Hanekom
# Date: January 2024
#
# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~

# =========== // STANDARD IMPORTS // ===========

from dataclasses import dataclass
import subprocess
import argparse
import tomllib
import logging
import shutil
import sys
import os
import re


from typing import (
    Optional,
    List
)

# =========== // CONSTANTS// ===========

BASE_PATH: str = os.path.dirname(os.path.abspath(__file__))
APPS_ROOT_PATH: str = os.path.join(BASE_PATH, "apps")

PROG_NAME: str = os.path.basename(__file__)
VENV_NAME: str = ".venv"
SETUP_NAME: str = "setup.toml"

SUPERVISOR_CONF_NAME: str = "supervisord.conf"
SUPERVISOR_CONF_PATH: str = os.path.join(BASE_PATH, SUPERVISOR_CONF_NAME)

NGINX_CONF_NAME: str = "nginx.conf"
NGINX_CONF_PATH: str = os.path.join(BASE_PATH, NGINX_CONF_NAME)

PY: str = "python"

# =========== // SIMPLE LOGGER SETUP // ===========

logger: logging.Logger = logging.getLogger(PROG_NAME)
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)


# =========== // DATA CLASSES // ===========

@dataclass
class Owner:
    name: str = ""


@dataclass
class Streamlit:
    port: int
    base_path: str
    entry_file: str


@dataclass
class Setup:
    title: str = ""
    owner: Owner = None
    streamlit: Streamlit = None
    app_folder_path: str = ""
    pip_path: str = ""
    python_path: str = ""


# =========== // TEMPLATES // ===========

def create_supervisor_program_str(
    *,
    app_name: str,
    python_path: str,
    app_python_file: str,
    app_folder_path: str,
    server_port: int,
    server_base_path: str
) -> str:
    return """[program:{app_name}]
    command={python_path} -m streamlit run {app_python_file} --server.port={server_port} --server.baseUrlPath={server_base_path}
    directory={app_folder_path}
    autostart=true
    autorestart=true
    stderr_logfile=/var/log/supervisor/{app_name}.err.log
    stdout_logfile=/var/log/supervisor/{app_name}.out.log
    """.format(
        app_name=app_name,
        python_path=python_path,
        app_python_file=app_python_file,
        app_folder_path=app_folder_path,
        server_port=server_port,
        server_base_path=server_base_path
    )


# =========== // GENERAL FUNCTIONS // ===========

def run_command(
    command: List[str],
    cwd: Optional[str] = None
) -> None:
    result: subprocess.CompletedProcess = subprocess.run(
        command,
        cwd=cwd,
        text=True
    )
    result.check_returncode()


def load_setup(
    app_folder_path: str,
    setup_name: str = SETUP_NAME
) -> Setup:
    with open(os.path.join(app_folder_path, setup_name), "rb") as f:
        data = tomllib.load(f)
    return Setup(
        title=data['title'],
        owner=Owner(**data['owner']),
        streamlit=Streamlit(**data['streamlit']),
        app_folder_path=app_folder_path
    )


def create_venv_and_install(
    setup: Setup,
    args: argparse.Namespace
) -> None:

    # =========== // STEP 1: SETTING THE PYTHON AND PIP EXE PATHS // ===========

    venv_path: str = os.path.join(setup.app_folder_path, VENV_NAME)

    if sys.platform == "win32":
        pip_path = os.path.join(venv_path, "Scripts", "pip")
        python_path = os.path.join(venv_path, "Scripts", "python")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")
        python_path = os.path.join(venv_path, "bin", "python")

    # Just in case I need it later on
    setup.pip_path = pip_path
    setup.python_path = python_path

    # =========== // STEP 2: CONSIDER THE HARD RESET // ===========

    if args.hard_reset and os.path.exists(venv_path):
        logger.info(f"[{setup.title}] Wiping {venv_path}")
        shutil.rmtree(venv_path)

    # =========== // STEP 3: CREATE AND INSTALL // ===========

    if not os.path.exists(venv_path):
        # ==========> STEP 3.1: CREATE THE VIRTUAL ENVIRONMENT
        logger.debug(f"[{setup.title}] Creating venv")
        run_command(
            [
                PY,
                "-m",
                "venv",
                venv_path
            ]
        )

        # ==========> STEP 3.2: INSTALL ALL THE DEPENDENCIES
        logger.debug(f"[{setup.title}] Installing requirements")
        run_command(
            [
                pip_path,
                "install",
                "-r",
                "requirements.txt"
            ],
            cwd=setup.app_folder_path
        )
    else:
        logger.warning(f"[{setup.title}] {VENV_NAME} file already exists. Please remove with `--hard`")


def to_snake_case(string: str) -> str:
    string = re.sub(r'[^a-zA-Z0-9]', ' ', string)
    string = re.sub(r'(?<!^)(?=[A-Z])', '_', string)
    string = re.sub(r'\s+', '_', string).lower()
    return string


def update_supervisor_conf(
    setup: Setup
) -> None:
    with open(SUPERVISOR_CONF_PATH, "a") as f:
        f.write("\n")
        f.write(
            create_supervisor_program_str(
                app_name=to_snake_case(str(setup.title)),
                python_path=setup.python_path,
                app_folder_path=setup.app_folder_path,
                app_python_file=setup.streamlit.entry_file,
                server_base_path=setup.streamlit.base_path,
                server_port=setup.streamlit.port
            )
        )


def create_nginx_location_block(
    *,
    base_path: str,
    port: int
) -> str:
    # Ensure base_path starts with / and ends with /
    if not base_path.startswith('/'):
        base_path = '/' + base_path
    if not base_path.endswith('/'):
        base_path = base_path + '/'

    # https://discuss.streamlit.io/t/deploy-streamlit-with-nginx-docker/52907
    return f"""
    location {base_path} {{
        proxy_pass http://127.0.0.1:{port}{base_path};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}

    location {base_path}_stcore/stream {{
        proxy_pass http://127.0.0.1:{port}{base_path}_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }}
    """


def create_nginx_config(
    setups: List[Setup]
) -> str:
    locations = "\n".join(
        create_nginx_location_block(
            base_path=setup.streamlit.base_path,
            port=setup.streamlit.port
        )
        for setup in setups
    )

    return f"""
server {{
    listen 80;
    server_name localhost;

    # Streamlit apps
    {locations}

    # Default location block
    location / {{
        return 404;
    }}
}}
"""


def update_nginx_conf(
    setup: Setup
) -> None:
    # =========== // FIRST TIME FILE CREATION // ===========
    if not os.path.exists(NGINX_CONF_PATH):
        logger.info(f"[{setup.title}] Creating new nginx configuration")
        with open(NGINX_CONF_PATH, "w") as f:
            f.write(create_nginx_config([setup]))
    else:
        # =========== // POST FIRST FILE CREATION: REPLACE COMMENT // ===========

        with open(NGINX_CONF_PATH, "r") as f:
            existing_config = f.read()

        backup_file(NGINX_CONF_PATH)
        location_block = create_nginx_location_block(
            base_path=setup.streamlit.base_path,
            port=setup.streamlit.port
        )

        if location_block not in existing_config:
            new_config = existing_config.replace(
                "    # Default location block",
                f"    {location_block}\n    # Default location block"
            )

            with open(NGINX_CONF_PATH, "w") as f:
                f.write(new_config)


def backup_file(file_path: str) -> None:
    backup_path = file_path + '.bak'
    shutil.copy(file_path, backup_path)


# =========== // MAIN CALL // ===========

def main(args: argparse.Namespace) -> None:
    if not os.path.exists(APPS_ROOT_PATH):
        _e: str = f"Could not find {APPS_ROOT_PATH}"
        logger.critical(_e)
        raise FileNotFoundError(_e)

    all_app_names: set = set()
    all_path_names: set = set()
    all_ports: set = set()

    for i, app_folder_name in enumerate(os.listdir(APPS_ROOT_PATH)):
        app_folder_path: str = os.path.join(APPS_ROOT_PATH, app_folder_name)
        logger.info(f"Building {app_folder_name}")

        # =========== // STEP 1: LOAD SETUP FILE // ===========

        logger.info(f"[{app_folder_name}] Loading settings...")
        setup: Setup = load_setup(app_folder_path)

        # =========== // STEP 2: ROUGH CHECK TO UNIQUE NAMES AND PORTS // ===========

        if setup.title in all_app_names:
            setup.title = setup.title + f" {i}"
        all_app_names.update((setup.title, ))

        if setup.streamlit.base_path in all_path_names:
            setup.streamlit.base_path = setup.streamlit.base_path + f"_{i}"
        all_path_names.update((setup.streamlit.base_path, ))

        if setup.streamlit.port in all_ports:
            setup.streamlit.port = int(f"{setup.streamlit.port}{i}")
        all_ports.update((setup.streamlit.port, ))

        # =========== // STEP 3: CREATE VENV AND INSTALL PACKAGES // ===========

        logger.info(f"[{app_folder_name}] Creating venv and installing python dependencies...")
        create_venv_and_install(
            setup=setup,
            args=args
        )

        # =========== // STEP 4: UPDATE SUPERVISOR CONF // ===========

        if args.deploy:
            logger.info(f"[{app_folder_name}] Updating supervisor conf...")
            backup_file(SUPERVISOR_CONF_PATH)
            update_supervisor_conf(
                setup=setup
            )
        else:
            logger.info("Skipping supervisor update")

        # =========== // STEP 5: UPDATE NGINX CONF   // ===========

        if args.deploy:
            logger.info(f"[{app_folder_name}] Updating nginx conf...")
            update_nginx_conf(
                setup=setup
            )
        else:
            logger.info("Skipping nginx update")


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog=PROG_NAME
    )
    parser.add_argument(
        "-d",
        "--deploy",
        action="store_true",
        help=(
            "Whether this function is running locally or not. "
            "This will determine if it should write back the supervisor file"
        )
    )
    parser.add_argument(
        "-H",
        "--hard-reset",
        action="store_true",
        help=(
            "Will hard reset the .venv files. "
            "It will delete them and start from scratch."
        )
    )
    args: argparse.Namespace = parser.parse_args()

    try:
        main(args=args)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        sys.exit(1)
