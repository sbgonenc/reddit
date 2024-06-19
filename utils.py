import json


def data_to_text(data):
    text = ""
    for contents in data.values():
        for thread in contents["contents"]:
            text += thread["title"] + " " + thread["self_text"] + " "
            for comment in thread["comments"]:
                text += comment["text"] + " "
    return text


def json_to_text(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data_to_text(data)

