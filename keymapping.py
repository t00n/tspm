import subprocess as sp
import sys
from xml.etree.ElementTree import parse


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

        if button not in keymapping:
            keymapping[button] = set()

        keymapping[button].add((parameter, name))

    for button, params in keymapping.items():
        if len(params) > 1:
            print(button)
            for p, n in params:
                print("\t%s %s" % (p, n))


if __name__ == '__main__':
    if sys.argv[1] == "duplicate":
        check_duplicate()
    elif sys.argv[1] == "list-keys":
        keymapping = get_keymapping()
        max_b_size = max([len(b) for b in keymapping.keys()])
        max_p_size = max([len(p) for p, _ in keymapping.values()])

        for b, (p, n) in keymapping.items():
            line = "%s\t|\t%s\t|\t%s" % (str(b).ljust(max_b_size), str(p).ljust(max_p_size), n)
            print(line)
    elif sys.argv[1] == "list-params":
        parametermapping = get_parametermapping()
        max_p_size = max([len(p) for p in parametermapping.keys()])

        for p, b in parametermapping.items():
            line = "%s\t|\t%s" % (str(p).ljust(max_p_size), b)
            print(line)
    else:
        sp.run(to_xml_cmd)
