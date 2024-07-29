import glob
from os import path, getcwd, curdir, makedirs
import json
from shutil import rmtree


def find_newest_report(test_name, report_dir="reports") -> str:
    """Helper to find the latest report json that contains `test_name` order by create date desc"""
    files = list(
        filter(path.isfile, glob.glob(f"{getcwd()}/{report_dir}/*.json"))
    )
    files.sort(key=lambda x: path.getmtime(x))
    files.reverse()

    for a_file in files:
        with open(a_file) as f:
            content = json.load(f)
            if content.get("name") == test_name:
                return a_file


def count_file_match(extension: str, report_dir: str) -> int:
    """Helper to count matching files with extension inside the  report folder"""
    files = list(
        filter(path.isfile, glob.glob(f"{getcwd()}/{report_dir}/{extension}"))
    )
    return len(files)


def clean_up_report_directories(report_dir):
    """Remove report dir then create a new one"""
    if path.exists(path.join(curdir, report_dir)):
        rmtree(path.join(curdir, report_dir))
    makedirs(path.join(curdir, report_dir), exist_ok=True)


def collect_files_from_report(source, name, path_prefix):
    output = []
    if source.get("attachments"):
        for attachment in source["attachments"]:
            if name in attachment.get("name"):
                output.append(f"{path_prefix}/" + attachment.get("source"))
    return output
