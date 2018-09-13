import click
import requests
import re
import json
import sys
import os
import zipfile
import subprocess
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import quote


TS2017_DIR = "/home/toon/.PlayOnLinux/wineprefix/TrainSimulator2017/drive_c/Program Files/Train Simulator 2017/"
CACHE_DIR = ".tspmcache"
ADDONS_FILE = os.path.join(CACHE_DIR, "index.json")

if not os.path.isdir(CACHE_DIR):
    os.mkdir(CACHE_DIR)


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

    filename = os.path.join(CACHE_DIR, name)

    if os.path.exists(filename):
        print("File '{}'' already exists".format(filename))
    else:
        print("Download '{}'".format(name))
        # first retrieve file download url
        response = requests.get(addon['url'])
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
        quoted_url = quote(addon['url']).replace("/", "%2F")

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

        response = requests.post(dl_url, headers=headers, cookies=cookies, data=data)

        if not response.ok or response.headers['Content-Transfer-Encoding'] != 'binary':
            print("Something wrong happened during download")
            sys.exit(1)

        with open(filename, "wb") as f:
            f.write(response.content)

    filetype = subprocess.run(["file", filename], capture_output=True).stdout

    if b'Zip' in filetype:
        archive = zipfile.ZipFile(filename, 'r')
        for file in tqdm(archive.filelist, desc="Extracting..."):
            linux_filename = file.filename.replace("\\", "/")
            archive.extract(file.filename, os.path.join(TS2017_DIR, linux_filename))
    else:
        print("Open zipfiles are supported at the moment")
        sys.exit(1)

if __name__ == '__main__':
    cli()
