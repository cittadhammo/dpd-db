#!/usr/bin/env python3

"""Modules for initilizing, reading, writing, updatingand testing
config.ini file."""

import configparser
from rich import print

config = configparser.ConfigParser()
config.read("config.ini")


def config_initialize() -> None:
    """Initialize config.ini."""
    config.add_section("regenerate")
    config.set("regenerate", "inflections", "yes")
    config.set("regenerate", "transliterations", "yes")
    config.set("regenerate", "freq_maps", "yes")
    config.add_section("deconstructor")
    config.set("deconstructor", "include_cloud", "no")
    config_write()


def config_read(section: str, option: str, default_value=None) -> str:
    """Read config.ini. If error, return a specified default value"""
    try:
        return config.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default_value


def config_write() -> None:
    """Write config.ini."""
    with open("config.ini", "w") as file:
        config.write(file)


def config_update(section: str, option: str, value) -> None:
    """Update config.ini with a new section, option & value."""
    if config.has_section(section):
        config.set(section, option, str(value))
    else:
        config.add_section(section)
        config.set(section, option, str(value))
    config_write()


def config_test(section: str, option: str, value) -> None:
    """Test config.ini to see if a section, option equals a value."""
    if (
        section in config and
        config.has_option(section, option)
    ):
        if config.get(section, option) == str(value):
            return True
        else:
            return False
    else:
        print("[red]unknown config setting")
        return False


def config_test_option(section, option):
    """Test config.ini to see if a section, option exists."""
    if config.has_section(section):
        return config.has_option(section, option)
    else:
        return False


if __name__ == "__main__":
    config_initialize()
