#!/usr/bin/env python3

"""Save a list of raw inflections (without stems) to TSV."""

import json

from db.get_db_session import get_db_session
from db.models import InflectionTemplates
from tools.pali_sort_key import pali_sort_key
from tools.paths import ProjectPaths as pth
from tools.tic_toc import tic, toc
from tools.tsv_read_write import write_tsv_list


def main():
    tic()
    db_session = get_db_session("dpd.db")
    infl_templ = db_session.query(InflectionTemplates)

    inflections_pos = []
    for i in infl_templ:
        data = json.loads(i.data)
        for row in data:
            if row != data[0]:
                row_length = len(row)
                for x in range(1, row_length, 2):
                    for inflection in row[x]:
                        pos = row[x+1][0]
                        pattern = i.pattern
                        inflections_pos += [(inflection, pos, pattern)]

    inflections_pos = sorted(
        inflections_pos, key=lambda x: (pali_sort_key(x[0]), x[1], x[2]))

    path = pth.temp_dir.joinpath("inflections_raw.tsv")
    headers = ["inflection", "pos", "pattern"]
    write_tsv_list(path, headers, inflections_pos)

    toc()


if __name__ == "__main__":
    main()