import subprocess as sp
import sys
from xml.etree.ElementTree import parse

import click


serz_cmd = [
    "wine",
    "/home/toon/.PlayOnLinux/wineprefix/TrainSimulator2017/drive_c/Program Files/Train Simulator 2017/serz.exe",
]

bin_file = "../../.PlayOnLinux/wineprefix/TrainSimulator2017/drive_c/Program Files/Train Simulator 2017/Assets/DTG/HamburgLubeck/InputMappers/BR145_ExpertInput.bin"
xml_file = "../../.PlayOnLinux/wineprefix/TrainSimulator2017/drive_c/Program Files/Train Simulator 2017/Assets/DTG/HamburgLubeck/InputMappers/BR145_ExpertInput.xml"

to_xml_cmd = serz_cmd + [
    bin_file
]

to_bin_cmd = serz_cmd + [
    xml_file,
    "/bin",
    bin_file,
]


def get_keymapping():
    tree = parse(xml_file)

    root = tree.getroot()

    keymapping = {}

    for map_entry in root.findall('Blueprint/cInputMapperBlueprint/Map/iInputMapper-cInputMapEntry'):
        if map_entry.find('Device').text == "Keyboard":
            parameter = map_entry.find('Parameter').text
            button = map_entry.find('Button').text
            name = map_entry.find('Name').text

            keymapping[button] = (parameter, name)

    return keymapping


def check_duplicate():
    tree = parse(xml_file)

    root = tree.getroot()

    keymapping = {}

    for map_entry in root.findall('Blueprint/cInputMapperBlueprint/Map/iInputMapper-cInputMapEntry'):
        parameter = map_entry.find('Parameter').text
        button = map_entry.find('Button').text
        name = map_entry.find('Name').text

        if "Stop" in name:
            action = name[:-4]
        elif "Start" in name:
            action = name[:-5]
        else:
            action = name

        if button not in keymapping:
            keymapping[button] = set()

        keymapping[button].add((parameter, action))

    for button, params in keymapping.items():
        if len(params) > 1:
            print(button)
            for p, n in params:
                print("\t%s %s" % (p, n))


@click.group()
def cli():
    pass


@cli.command()
def list():
    keymapping = get_keymapping()
    max_b_size = max([len(b) for b in keymapping.keys()])
    max_p_size = max([len(p) for p, _ in keymapping.values()])

    for b, (p, n) in keymapping.items():
        line = "%s\t|\t%s\t|\t%s" % (str(b).ljust(max_b_size), str(p).ljust(max_p_size), n)
        print(line)


@cli.command()
def duplicate():
    check_duplicate()


if __name__ == '__main__':
    cli()
