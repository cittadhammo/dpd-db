from bhs.bhs import main as bhs
from cpd.cpd import main as cpd
from dpr.dpr import main as dpr
from mw.mw_from_simsapa import main as mw
from peu.peu import main as peu
from pts.pts_from_simsapa import main as pts
from whitney.whitney import main as whitney


def main():
    print("[bright_yellow]exporting dicts in goldendict and mdict format")
    bhs()
    cpd()
    dpr()
    mw()
    peu()
    pts()
    whitney()


if __name__ == "__main__":
    main()
