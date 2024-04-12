#!/usr/bin/env python3

"""Export DPD for GoldenDict and MDict."""

import shutil
import subprocess
import idzip

import zipfile
import csv
import pickle

from os import fstat
from pathlib import Path
from pyglossary import Glossary
from rich import print
from sqlalchemy.orm import Session
from subprocess import Popen, PIPE
from typing import List

from export_dpd import generate_dpd_html
from export_roots import generate_root_html
from export_epd import generate_epd_html
from export_variant_spelling import generate_variant_spelling_html
from export_help import generate_help_html

from helpers import make_roots_count_dict
from mdict_exporter import export_to_mdict

from db.get_db_session import get_db_session
from tools.cache_load import load_cf_set, load_idioms_set
from tools.date_and_time import make_timestamp

from tools.configger import config_read, config_test
from tools.goldendict_path import make_goldendict_path
from tools.paths import ProjectPaths
from exporter.ru_components.tools.paths_ru import RuPaths
from tools.sandhi_contraction import make_sandhi_contraction_dict
from tools.stardict import export_words_as_stardict_zip, ifo_from_opts
from tools.tic_toc import tic, toc, bip, bop
from tools.utils import RenderResult, RenderedSizes, sum_rendered_sizes
from tools import time_log

from exporter.ru_components.tools.tools_for_ru_exporter import mdict_ru_title, mdict_ru_description, gdict_ru_info


def main():
    tic()
    print("[bright_yellow]exporting dpd to goldendict and mdict")
    if not config_test("exporter", "make_dpd", "yes"):
        print("[green]disabled in config.ini")
        toc()
        return

    time_log.start(start_new=True)
    time_log.log("exporter.py::main()")

    pth = ProjectPaths()
    rupth = RuPaths()
    db_session: Session = get_db_session(pth.dpd_db_path)
    sandhi_contractions = make_sandhi_contraction_dict(db_session)

    cf_set: set = load_cf_set()
    idioms_set: set = load_idioms_set()

    rendered_sizes: List[RenderedSizes] = []

    # check config
    if config_test("dictionary", "make_mdict", "yes"):
        make_mdct: bool = True
    else:
        make_mdct: bool = False

    if config_test("goldendict", "copy_unzip", "yes"):
        copy_unzip: bool = True
    else:
        copy_unzip: bool = False

    # check config
    if config_test("dictionary", "make_link", "yes"):
        make_link: bool = True
    else:
        make_link: bool = False

    if config_test("dictionary", "show_dps_data", "yes"):
        dps_data: bool = True
    else:
        dps_data: bool = False

    if config_test("exporter", "language", "en"):
        lang = "en"
    elif config_test("exporter", "language", "ru"):
        lang = "ru"
    # add another lang here "elif ..." and 
    # add conditions if lang = "{your_language}" in every instance in the code.
    else:
        raise ValueError("Invalid language parameter")

        
    if config_test("dictionary", "external_css", "yes"):
        external_css = True
    else:
        external_css = False
    
    data_limit = int(config_read("dictionary", "data_limit") or "0")
    
    time_log.log("make_roots_count_dict()")
    roots_count_dict = make_roots_count_dict(db_session)

    time_log.log("generate_dpd_html()")
    dpd_data_list, sizes = generate_dpd_html(
        db_session, pth, rupth, sandhi_contractions, cf_set, idioms_set, make_link, dps_data, lang, data_limit)
    rendered_sizes.append(sizes)

    time_log.log("generate_root_html()")
    root_data_list, sizes = generate_root_html(db_session, pth, roots_count_dict, rupth, lang, dps_data)
    rendered_sizes.append(sizes)

    time_log.log("generate_variant_spelling_html()")
    variant_spelling_data_list, sizes = generate_variant_spelling_html(pth, rupth, lang)
    rendered_sizes.append(sizes)

    time_log.log("generate_epd_html()")
    epd_data_list, sizes = generate_epd_html(db_session, pth, make_link, dps_data, lang)
    rendered_sizes.append(sizes)
    
    time_log.log("generate_help_html()")
    help_data_list, sizes = generate_help_html(db_session, pth, rupth, lang, dps_data)
    rendered_sizes.append(sizes)

    db_session.close()

    combined_data_list: list = (
        dpd_data_list +
        root_data_list +
        variant_spelling_data_list +
        epd_data_list +
        help_data_list
    )

    time_log.log("write_limited_datalist()")
    write_limited_datalist(combined_data_list)

    time_log.log("write_size_dict()")
    write_size_dict(pth, sum_rendered_sizes(rendered_sizes))

    time_log.log("export_to_goldendict()")
    if lang == "en":
        if external_css:
            export_to_goldendict_pyglossary(pth, combined_data_list, lang, external_css=external_css)
        else:
            export_to_goldendict_simsapa(pth, combined_data_list, lang, external_css=external_css)
    elif lang == "ru":
        export_to_goldendict_simsapa(rupth, combined_data_list, lang)

    if copy_unzip:
        time_log.log("goldendict_unzip_and_copy()")
        if lang == "en":
            if external_css:
                goldendict_copy_dir(pth)
            else:
                goldendict_unzip_and_copy(pth)
        elif lang == "ru":
            if external_css:
                goldendict_copy_dir(rupth)
            else:
                goldendict_unzip_and_copy(rupth)

    if make_mdct:
        time_log.log("export_to_mdict()")
        if lang == "en":
            description = """
                <p>Digital Pāḷi Dictionary by Bodhirasa</p>
                <p>For more infortmation, please visit
                <a href=\"https://digitalpalidictionary.github.io\">
                the Digital Pāḷi Dictionary website</a></p>
            """
            title= "Digital Pāḷi Dictionary"
            export_to_mdict(
                combined_data_list, pth,
                description, title,
                external_css=external_css)

        elif lang == "ru":
            description = mdict_ru_description
            title= mdict_ru_title
            export_to_mdict(
                combined_data_list, rupth, description, title, external_css=external_css)

    toc()
    time_log.log("exporter.py::main() return")


def export_to_goldendict_simsapa(
        _pth_,
        data_list: list,
        lang="en",
        external_css=False
    ) -> None:
    """generate goldedict zip"""
    bip()

    print("[green]generating goldendict zip", end=" ")

    if lang == "en":
        ifo = ifo_from_opts(
            {"bookname": "DPD",
                "author": "Bodhirasa",
                "description": "",
                "website": "https://digitalpalidictionary.github.io/", }
        )
    elif lang == "ru":
        ifo = ifo_from_opts(gdict_ru_info)

    export_words_as_stardict_zip(data_list, ifo, _pth_.dpd_zip_path, _pth_.icon_path)

    # add bmp icon for android
    if lang == "en":
        with zipfile.ZipFile(_pth_.dpd_zip_path, "a") as zipf:
            source_path = _pth_.icon_bmp_path
            destination = "dpd/android.bmp"
            zipf.write(source_path, destination)

    # add external css
    if external_css is True:
        with zipfile.ZipFile(_pth_.dpd_zip_path, "a") as zipf:
            zipf.write(_pth_.dpd_css_path, "dpd/res/dpd.css")
            zipf.write(_pth_.buttons_js_path, "dpd/res/button.js")

    print(f"{bop():>29}")


def dictzip(filename: Path) -> None:
    """ Compress file into dictzip format """

    destination = filename.with_suffix(".syn.dz")

    with open(filename, "rb") as input_f, open(destination, 'wb') as output_f:
        inputinfo = fstat(input_f.fileno())
        idzip.compressor.compress(
            input_f,
            inputinfo.st_size,
            output_f,
            filename.name,
            int(inputinfo.st_mtime))

    filename.unlink()


def export_to_goldendict_pyglossary(
    _pth_: ProjectPaths,
    data_list: list[RenderResult],
    lang="en",
    external_css=False
) -> None:
    """generate goldendict zip using pyglossary"""

    bip()
    print("[green]exporting goldendict with pyglossary", end="")

    Glossary.init()
    glos = Glossary(info={
        "bookname": "DPD",
        "author": "Bodhirasa",
        "description": "Digital Pāḷi Dictionary - the feature-rich Pāḷi dictionary.",
        "website": "https://digitalpalidictionary.github.io/",
        "sourceLang": "pi",  # A full name "Pali" also may be used
        "targetLang": lang,
        "date": make_timestamp(),
    })

    # add css
    with open(_pth_.dpd_css_path, "rb") as f:
        css = f.read()
        glos.addEntry(glos.newDataEntry("dpd.css", css))

    # Add buttons script
    buttons_path = _pth_.buttons_js_path
    with open(buttons_path, "rb") as f:
        glos.addEntry(glos.newDataEntry(buttons_path.name, f.read()))

    # add dpd data
    for i in data_list:
        new_word = glos.newEntry(
            word=[i["word"]] + i["synonyms"],
            defi=i["definition_html"],
            defiFormat="h")
        glos.addEntry(new_word)

    output_path = _pth_.dpd_goldendict_pyglossary_dir
    output_name = Path("dpd.ifo")
    output_path_name = output_path.joinpath(output_name)
    
    # *.syn file compression expected in next after v4.6.1 PyGlossary release
    glos.write(
        filename=str(output_path_name),
        format="Stardict",
        dictzip=True,
        merge_syns=False,  # Include synonyms in compressed main file rather than *.syn when True
        sametypesequence="h",
        sqlite=False,  # More RAM, but faster when False
    )

    synfile = output_path_name.with_suffix(".syn")
    dictzip(synfile)
    
    print(f"{bop():>19}")


def goldendict_copy_dir(_pth_: ProjectPaths) -> None:
    "Copy DPD to Goldendict dir "

    bip()
    print("[green]Copy to GoldenDict dir", end="")
    goldendict_pth: (Path |str) = make_goldendict_path()
    if goldendict_pth and goldendict_pth.exists():
        subprocess.Popen(
            ["cp", "-rf", _pth_.dpd_goldendict_pyglossary_dir, "-t", goldendict_pth])
    print(f"{bop():>33}")


def goldendict_unzip_and_copy(_pth_) -> None:
    """unzip and copy to goldendict folder"""

    goldendict_pth: (Path |str) = make_goldendict_path()

    bip()

    if make_goldendict_path and make_goldendict_path.exists():
        try:
            with Popen(f'unzip -o {_pth_.dpd_zip_path} -d "{goldendict_pth}"', shell=True, stdout=PIPE, stderr=PIPE) as process:
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    print("[green]Unzipping and copying [blue]ok", end="")
                else:
                    print("[red]Error during unzip and copy:")
                    print(f"Exit Code: {process.returncode}")
                    print(f"Standard Output: {stdout.decode('utf-8')}")
                    print(f"Standard Error: {stderr.decode('utf-8')}")
        except Exception as e:
            print(f"[red]Error during unzip and copy: {e}")
    else:
        print("[red]local GoldenDict directory not found")

    print(f"{bop():>31}")


def write_size_dict(pth: ProjectPaths, size_dict):
    bip()
    print("[green]writing size_dict", end=" ")
    filename = pth.temp_dir.joinpath("size_dict.tsv")

    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter='\t')
        for key, value in size_dict.items():
            writer.writerow([key, value])

    print(f"{bop():>37}")


def write_limited_datalist(combined_data_list):
    """A limited dataset for troubleshooting purposes"""

    # limited_data_list = [
    #     item for item in combined_data_list if item["word"].startswith("ab")]

    with open("temp/limited_data_list", "wb") as file:
        pickle.dump(combined_data_list, file)


if __name__ == "__main__":
    main()
