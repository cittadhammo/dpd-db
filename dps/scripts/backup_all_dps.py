#!/usr/bin/env python3

"""Save all tables in dps/backup folder."""


from rich.console import Console

import os

from db.get_db_session import get_db_session
from tools.tic_toc import tic, toc
from tools.paths import ProjectPaths
from dps.tools.paths_dps import DPSPaths

from scripts.backup_dpd_headwords_and_roots import backup_dpd_headwords, backup_dpd_roots
from scripts.backup_ru_sbs import backup_russian, backup_sbs

console = Console()

def backup_all_tables_dps():
    tic()
    console.print("[bold bright_yellow]Backing up all tables to dps/backup/*.tsvs")
    pth = ProjectPaths()
    dpspth = DPSPaths()
    db_session = get_db_session(pth.dpd_db_path)
    
    dps_ru_path = os.path.join(dpspth.dps_backup_dir, "russian.tsv")
    dps_sbs_path = os.path.join(dpspth.dps_backup_dir, "sbs.tsv")
    dps_headwords_path = os.path.join(dpspth.dps_backup_dir, "dpd_headwords.tsv")
    dps_roots_path = os.path.join(dpspth.dps_backup_dir, "dpd_roots.tsv")

    backup_dpd_headwords(db_session, pth, dps_headwords_path)
    backup_dpd_roots(db_session, pth, dps_roots_path)
    backup_russian(db_session, pth, dps_ru_path)
    backup_sbs(db_session, pth, dps_sbs_path)

    db_session.close()
    toc()


if __name__ == "__main__":
    backup_all_tables_dps()

