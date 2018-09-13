import click
import requests
import re
import json
import sys
import os
import zipfile
import subprocess
import traceback
import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import quote
from distutils.dir_util import copy_tree


TS2017_DIR = "/home/toon/.PlayOnLinux/wineprefix/TrainSimulator2017/drive_c/Program Files/Train Simulator 2017/"
CACHE_DIR = ".tspmcache"
ADDONS_FILE = os.path.join(CACHE_DIR, "index.json")
ARCHIVE_DIR = os.path.join(CACHE_DIR, "archives")
TMP_DIR = os.path.join(CACHE_DIR, "tmp")
FINAL_DIR = os.path.join(CACHE_DIR, "final")

for dir in (CACHE_DIR, ARCHIVE_DIR, TMP_DIR, FINAL_DIR):
    if not os.path.isdir(dir):
        os.mkdir(dir)


@click.group()
def cli():
    pass


BASE_CATEGORY_URL = "http://www.trainsimmods.com/category/train-simulator-2017/page/{}"


@cli.command()
def update():
    i = 1
    addons = []
    addons_by_category = {}
    with tqdm() as pbar:
        while True:
            pbar.update()
            response = requests.get(BASE_CATEGORY_URL.format(i))
            if not response.ok:
                break
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = soup.find_all('article')

            for art in articles:
                # contains name and url
                main_a = art.find('a', {"href": re.compile(r".")})
                name = main_a.attrs['title']
                url = main_a.attrs['href']
                # contains category
                category_a = art.find('a', {"rel": "category tag"})
                category = category_a.text

                # add addon
                addon = {
                    'name': name.strip(),
                    'url': url.strip(),
                    'category': category.strip(),
                }
                addons.append(addon)
                if category not in addons_by_category:
                    addons_by_category[category] = []

                addons_by_category[category].append(addon)

            i += 1

    with open(ADDONS_FILE, "w") as f:
        json.dump({
            'addons': sorted(addons, key=lambda x: x['name']),
            'addons_by_category': {
                cat: sorted(add, key=lambda x: x['name']) for cat, add in addons_by_category.items()
            },
        }, f)


@cli.command()
def list():
    with open(ADDONS_FILE) as f:
        cache = json.load(f)

    addons_by_category = cache['addons_by_category']

    for category, addons in addons_by_category.items():
        print(category)
        print("=" * len(category))
        for addon in addons:
            print(addon['name'])
        print("_" * 80)


def download(name, url, filename):
    try:
        print("Download '{}'".format(name))
        # first retrieve file download url
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        dl_url = soup.select("div[class=download-button] > p > a")[0].attrs['href']
        if dl_url.startswith("http://"):
            dl_url = dl_url.replace("http://", "https://")
        print("Download url:", dl_url)

        if "dl-file.com" not in dl_url:
            print("Sorry, url is {} and tspm is only supporting dl-file.com at the moment".format(dl_url))
            sys.exit(1)

        # http://dl-file.com/vuo0airlf15o/Diesel_locomotive_2____10__-2437_v1.2_for_TS_2017.rar.html
        dl_id = re.match("^https://dl-file.com/(.*)/.*", dl_url).groups()[0]
        print("Download id:", dl_id)

        # assumes all files are on dl-file.com
        quoted_url = quote(url).replace("/", "%2F")

        cookies = {
            'lang': 'english',
            'ref_url': quoted_url,
            'aff': '11',
            '__utma': '125620191.1934667345.1536844881.1536844881.1536844881.1',
            '__utmb': '125620191.5.10.1536844881',
            '__utmc': '125620191',
            '__utmz': '125620191.1536844881.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
            '__utmt': '1',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': dl_url,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        data = {
            'op': 'download2',
            'id': dl_id,
            'rand': '',
            'referer': dl_url,
            'method_free': 'Free Download',
            'method_premium': ''
        }

        response = requests.post(dl_url, headers=headers, cookies=cookies, data=data, stream=True)

        if not response.ok or response.headers['Content-Transfer-Encoding'] != 'binary':
            print("Something wrong happened during download")
            sys.exit(1)

        else:
            filesize = int(response.headers['Content-length'])
            with open(filename, "wb") as f:
                for chunk in tqdm(response.iter_content(1024), total=filesize // 1024, unit='kB'):
                    f.write(chunk)
    except:
        traceback.print_exc()
        os.remove(filename)
        sys.exit(1)


def extract(filename, dest_dir):
    filetype = subprocess.run(["file", filename], capture_output=True).stdout.decode()[:-1]
    if 'Zip' in filetype:
        archive = zipfile.ZipFile(filename, 'r')
        for file in tqdm(archive.filelist, desc="Extracting {}".format(filename)):
            linux_filename = file.filename.replace("\\", "/")
            archive.extract(file.filename, os.path.join(dest_dir, linux_filename))
    else:
        print("Sorry, filetype is '{}' and only zipfiles are supported at the moment".format(filetype))
        sys.exit(1)


@cli.command()
@click.argument("name")
def install(name):
    name = name.strip()
    with open(ADDONS_FILE) as f:
        cache = json.load(f)

    addon = None

    for add in cache['addons']:
        if add['name'] == name:
            addon = add
            break

    if addon is None:
        print("Addon '{}' not found, maybe you should try to update first ?".format(name))
        sys.exit(1)

    filename = os.path.join(ARCHIVE_DIR, name)

    if os.path.exists(filename):
        print("File '{}'' already exists".format(filename))
    else:
        download(name, addon['url'], filename)

    # first, extract all files in a temporary directory
    tmp_dir = os.path.join(TMP_DIR, name)
    extract(filename, tmp_dir)

    final_dir = os.path.join(FINAL_DIR, name)
    # second, check for any *.rwp files. They are zip files containing the real addon files
    second_extract = False
    for file in glob.glob(tmp_dir + "/**/*.rwp"):
        second_extract = True
        extract(file, final_dir)

    # if we did not extract anythign in the second phase, then final files are still in tmp dir
    if not second_extract:
        final_dir = tmp_dir

    # third, copy files in to TS2017 dir
    for file in glob.glob(final_dir + "/*"):
        dir_name = os.path.basename(file)
        copy_tree(file, os.path.join(TS2017_DIR, dir_name))

if __name__ == '__main__':
    cli()
