"""Download the public, keyless inputs for the H2 run into data/raw (gitignored).

Run: python fetch_data.py. Each file is checked against the sha256 recorded when the
result in README.md was produced. Hansen and GHGRP files are versioned and must match
(error). Nasdaq and ECHO files are refreshed upstream, so a mismatch only warns: the
run then uses a newer snapshot than the one reported.

Licences: EPA GHGRP/ECHO public domain; Hansen GFC CC BY 4.0 (Hansen et al. 2013,
Science 342:850); Nasdaq Trader symbol directory is public reference data, only read.
"""

import hashlib
import os
import sys
import urllib.request

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
HANSEN = "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/"
EPA = "https://www.epa.gov/system/files/other-files/2024-10/"

# name -> (url, sha256, versioned: a mismatch is an error)
FILES = {
    "ghgrp.zip": (EPA + "2023_data_summary_spreadsheets.zip",
                  "895349c8008b7962dba68659c8187cec6b340d68be84ccb3f0e7fb6037bf8345", True),
    "parent.xlsb": (EPA + "ghgp_data_parent_company.xlsb",
                    "5613dd8454b08deb160e3f1dec18c1a9b45464bc0ef8453c97989ea0d4fdbce2", True),
    "case.zip": ("https://echo.epa.gov/files/echodownloads/case_downloads.zip",
                 "7e7ea90e1a28501c79d719a7acb6147d7434cf8bd66cbd7cd3669f31162f4370", False),
    "nasdaqlisted.txt": ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
                         "047ae090e3165e70f2923505df62318bd17ed8f276f3eb3731ce7241b2985e16", False),
    "otherlisted.txt": ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
                        "dd7f595f4546462841448bb6c06314dbc1e15b689492678b3b45a35c89ffde63", False),
}

TILES = {
    "20N_070W": "e928d8cc8b1ae2fddee7d8fea3b38b5ccf57e296207a1ef4ea19604ca32388ea",
    "20N_160W": "630956bd574952a82115573a2ca835d5effc5d91613038593222405a8235fc43",
    "30N_110W": "0d04319f2b890edca79307bc3bbd3b8005911934852972164854c80720859d03",
    "30N_160W": "199eb007223b015c1ed043de295ee4b8b558bdace977d45adfb9d1760038c028",
    "40N_130W": "ec3e9c3cb416a852886af4c11b054c055c427f313b3439be4d9e79386aea1703",
    "50N_070W": "d85d75ac5829786c296ff369478d0d7c7b50f5e50b7ed737e73da66d09b6d1de",
    "70N_160W": "0444d98da57248949591f63ee6f7d35a6c75c42734689ed5b918bcf771df850b",
    "30N_090W": "8233eb05bb731fc6e26682e86c7dd478960ef7e77d3912ec2a7d903f0f3f9cd1",
    "30N_100W": "2cebd77ccc7aadf43703a71753c55714145c82c70006610c51fe3fa8c7da33a7",
    "40N_080W": "a40edc2268213b858d80dc9860f25f1914c6c2cba503b3cce850476324828a6a",
    "40N_090W": "fa972fdb89c46447d67fbd4875eb56b97b85f22f62acde75384bda2b0ac47acb",
    "40N_100W": "0a1352204521fd35370383749916fb4453f39180a9e6f606fbb7c0b8c18fbcd2",
    "40N_110W": "80291094b637edb613ca548f177bf421526265c7ca0734ef36c4af30b09a9939",
    "40N_120W": "35547e90396c99aae3b8d59a8ef977f06cbe772b3fc859c741c64b0b26483443",
    "50N_080W": "f471fcbee1cb8b2e86ac9ccc1722b0a5201a020c193ae75354bf3e069ae63a18",
    "50N_090W": "c9b192871c0f31538f4503b57bdcec8aa8dccba05bd3a562695e252d860418df",
    "50N_100W": "f67f102a5a49f758a6eeaceecc9100d2331f6a3a71ebfc5a88e745e5e9a20e05",
    "50N_110W": "9b4caea3548f2a3294c322a69c68fd6557562690b2987529ff909f36f2da3884",
    "50N_120W": "f24100296656cb1bc189899c2810c7ab772071b02d31cf033c2ad240b9756aaa",
    "50N_130W": "73ca8bf804a84cde301af49c1ad34ea593b63bea7ae2a8d698288643713e165a",
    "60N_140W": "1166f012de337c3824f150cc68f1c4dda6d78a79f769858ce2c81bcf71c5a761",
    "80N_150W": "d9bc2fecd7036188bef12d398afc941f891067873559db6e362c92c95be45fa8",
}
for _t, _h in TILES.items():
    FILES["hansen/Hansen_GFC-2024-v1.12_lossyear_%s.tif" % _t] = (
        HANSEN + "Hansen_GFC-2024-v1.12_lossyear_%s.tif" % _t, _h, True)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(name: str, url: str, digest: str, versioned: bool) -> None:
    path = os.path.join(RAW, *name.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    got = sha256(path)
    if got != digest:
        msg = "%s: sha256 %s != recorded %s" % (name, got, digest)
        if versioned:
            raise SystemExit("MISMATCH " + msg)
        print("WARNING (upstream refreshed) " + msg, file=sys.stderr)


if __name__ == "__main__":
    for n, (u, h, v) in FILES.items():
        fetch(n, u, h, v)
    print("ok: %d files in %s" % (len(FILES), RAW))
