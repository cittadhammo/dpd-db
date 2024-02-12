#!/usr/bin/env python3

import tomlkit

from rich import print

from db.models import DbInfo
from db.get_db_session import get_db_session
from tools.configger import config_update
from tools.date_and_time import year_month_day
from tools.paths import ProjectPaths
from tools.tic_toc import tic, toc


major = 0
minor = 1


def update_version():
    tic()
    print("[bright_yellow]updating dpd release version")
    pth = ProjectPaths()
    version = make_version()
    
    config_update("version", "version", version, silent=True)
    printer("config.ini", "ok")

    update_poetry_version(pth, version)
    update_db_version(pth, version)


def printer(key, value):
    print(f"[green]{key:<20}[white]{value}")


def make_version():
    patch = year_month_day()
    version = f"v{major}.{minor}.{patch}"
    printer("version", version)
    return version


def update_poetry_version(pth, version):
    with open(pth.pyproject_path) as file:
        doc = file.read()
        t = tomlkit.parse(doc)
        t["tool"]["poetry"]["version"] = version    # type: ignore

    with open(pth.pyproject_path, "w") as file:
        file.write(t.as_string())
    
    printer("pyproject.toml", "ok")


def update_db_version(pth, version):
    db_session = get_db_session(pth.dpd_db_path)
    db_info = db_session.query(DbInfo) \
                        .filter_by(key="dpd_release_version") \
                        .first()
    
    # update the dpd_release_version if it exists
    if db_info:
        db_info.value = version
    
    # add the dpd_release_version and author info if it doesnt exist
    else:
        dpd_release_version = DbInfo(
            key="dpd_release_version", value=version)
        db_session.add(dpd_release_version)

        author = DbInfo(
            key="author", value="Bodhirasa")
        db_session.add(author)

        email_address = DbInfo(
            key="email", value="digitalpalidictionary@gmail.com")
        db_session.add(email_address)

        website = DbInfo(
            key="website", value="https://digitalpalidictionary.github.io/")
        db_session.add(website)
    
    db_session.commit()
    printer("dpd.db", "ok")

    toc()

if __name__ == "__main__":
    update_version()
    # version = make_version()