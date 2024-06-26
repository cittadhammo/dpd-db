#!/usr/bin/env python3

"""Remove construction line 2 from ptp"""

from rich import print

from db.get_db_session import get_db_session
from db.models import DpdHeadwords
from tools.paths import ProjectPaths


def main():
    pth = ProjectPaths()
    db_session = get_db_session(pth.dpd_db_path)
    db = db_session.query(DpdHeadwords).all()
    count= 0
    for counter, i in enumerate(db):
        if i.pos == "prp" and "\n" in i.construction:
            i.construction = i.construction_line1
            print(counter, i.lemma_1, i.construction)
            count+=1

    db_session.commit()
    print(count)


if __name__ == "__main__":
    main()
