#!/usr/bin/env python3

"""
Gather configuration files that have been generated by CI jobs api-doc
from S3 of each relevant back-end module.
Assemble complete config to be utilised by dev.f.o reference/api navigation facility.

   Returns:
       0: Success.
       1: One or more failures with processing.
       2: Configuration issues.
"""

# pylint: disable=C0413
import sys
if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

import argparse
import json
import logging
from operator import itemgetter
import os
from time import sleep

import requests
import yaml

SCRIPT_VERSION = "1.1.0"

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}
PROG_NAME = os.path.basename(sys.argv[0])
PROG_DESC = __import__('__main__').__doc__
LOG_FORMAT = "%(levelname)s: %(name)s: %(message)s"
LOGGER = logging.getLogger(PROG_NAME)

def get_options():
    """Gets the command-line options."""
    parser = argparse.ArgumentParser(description=PROG_DESC)
    parser.add_argument(
        "-l", "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level. (Default: %(default)s)"
    )
    parser.add_argument(
        "-t", "--test", action="store_true",
        help="Test mode. Consider a few specific modules. (Default: False)"
    )
    args = parser.parse_args()
    logging.basicConfig(format=LOG_FORMAT)
    logging.getLogger("requests").setLevel(logging.ERROR)
    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    LOGGER.setLevel(loglevel)
    # Display a version string
    LOGGER.info("Using version: %s", SCRIPT_VERSION)
    url_base_devweb = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data"
    url_repos = os.path.join(url_base_devweb, "repos.json")
    status, json_repos = get_json_contents(url_repos)
    if not status:
        sys.exit(2)
    status, json_old_config = get_old_apidocs_config()
    if not status:
        sys.exit(2)
    if args.test:
        LOGGER.info("TEST mode.")
        delay = 0
        #list_modules_test = ["mod-notes", "mod-search", "mod-quick-marc", "mod-tags", "raml"]
        list_modules_test = ["mod-notes", "mod-search", "mod-quick-marc"]
    else:
        delay = 3
        list_modules_test = []
    return json_repos, json_old_config, list_modules_test, delay

def get_old_apidocs_config():
    """Gets the old manually-maintained configuration for apidocs.
    If a repository does not have the new config-doc.json generated by CI api-doc,
    then its old config will be utilised.
    """
    url_config = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"
    status = True
    contents = ""
    try:
        http_response = requests.get(url_config)
        http_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        LOGGER.critical("HTTP error retrieving configuration file: %s", err)
        status = False
    except Exception as err:
        LOGGER.critical("Error retrieving configuration file: %s", err)
        status = False
    else:
        try:
            contents = yaml.safe_load(http_response.text)
        except yaml.YAMLError as err:
            LOGGER.critical("Trouble parsing YAML configuration file '%s': %s", url_config, err)
            status = False
    return status, contents

def get_json_contents(url):
    """Gets the JSON contents from the specified url."""
    status = True
    contents = ""
    try:
        http_response = requests.get(url)
        http_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        LOGGER.critical("HTTP error retrieving file: %s", err)
        status = False
    except Exception as err:
        LOGGER.critical("Error retrieving file: %s", err)
        status = False
    else:
        try:
            contents = json.loads(http_response.text)
        except Exception as err:
            LOGGER.critical("Trouble loading JSON: %s", err)
            status = False
    return status, contents

def store_config(output_json):
    """Store this JSON output."""
    output_dir = "_data"
    os.makedirs(output_dir, exist_ok=True)
    output_pn = os.path.join(output_dir, "config-apidocs.json")
    with open(output_pn, "w") as output_fh:
        output_fh.write(json.dumps(output_json, sort_keys=True, indent=2, separators=(",", ": ")))
        output_fh.write("\n")

def report_summary(json_apidocs, json_old_config):
    """Report a summary and any misconfiguration."""
    old_config_list = set()
    new_config_list = set()
    missing_from_old = []
    missing_from_new = []
    remove_from_old_list = ["default", "mod-vendors"]
    for name_old in json_old_config:
        if name_old not in remove_from_old_list:
            old_config_list.add(name_old)
    for mod in json_apidocs:
        name_new = mod["name"]
        new_config_list.add(name_new)
        if name_new not in old_config_list:
            missing_from_old.append(name_new)
    for name_old in old_config_list:
        if name_old not in new_config_list:
            missing_from_new.append(name_old)
    LOGGER.info("%s in old config.", len(old_config_list))
    LOGGER.info("%s in new config, either discovered or transformed from old.",
        len(json_apidocs))
    LOGGER.info("%s discovered, and are not in old config: %s",
        len(missing_from_old), missing_from_old)
    LOGGER.info("%s in old config, but are not in new config: %s",
        len(missing_from_new), missing_from_new)
    diff_old_new = old_config_list.difference(new_config_list)
    if diff_old_new:
        LOGGER.info("difference between old config and new: %s", diff_old_new)

def list_api_modules(json_repos):
    """Produce a list of API-related modules."""
    list_modules = set()
    repo_types = ["backend-mod", "backend-edge", "backend-infrastructure", "raml-shared"]
    for mod in sorted(json_repos["repos"], key=itemgetter('name')):
        if mod["repoType"] in repo_types:
            list_modules.add(mod["name"])
    LOGGER.info("Assessing %s repos that are potentially API-related ...", len(list_modules))
    return sorted(list_modules)

def inspect_s3(mod_name):
    """Inspect the S3 space of this module."""
    LOGGER.debug("%s: Inspecting S3 ...", mod_name)
    url_base = "https://s3.amazonaws.com/foliodocs/api/{}".format(mod_name)
    items_upload = []
    json_config = {}
    url_upload = url_base + "/u/files-upload.txt"
    url_config = url_base + "/config-doc.json"
    http_response = requests.get(url_upload)
    if http_response.status_code == 200:
        items_upload = http_response.text.rstrip().split("\n")
        LOGGER.info("%s: Found files-upload: %s", mod_name, items_upload)
    http_response = requests.get(url_config)
    if http_response.status_code == 200:
        try:
            json_config = json.loads(http_response.text)
        except Exception as err:
            LOGGER.error("%s: Trouble loading JSON: %s", mod_name, err)
        else:
            LOGGER.info("%s: Found config-doc.json", mod_name)
    return items_upload, json_config

def assemble_config_packet(mod_name, json_config, items_upload, old_config):
    """Assemble a JSON config entry."""
    json_packet = {}
    json_packet["name"] = mod_name
    json_packet["metadata"] = {}
    json_packet["config"] = {}
    json_packet["config"]["raml"] = []
    json_packet["config"]["oas"] = []
    json_packet["config"]["upload"] = []
    if json_config:
        json_packet["metadata"]["apiTypes"] = json_config["metadata"]["apiTypes"]
        if "RAML" in json_config["metadata"]["apiTypes"]:
            json_packet["config"]["raml"] = json_config["config"]["raml"]["files"]
        if "OAS" in json_config["metadata"]["apiTypes"]:
            json_packet["config"]["oas"] = json_config["config"]["oas"]["files"]
    elif old_config:
        files = []
        for docset in old_config:
            try:
                docset["files"]
            except KeyError:
                continue
            for file_fn in sorted(docset["files"]):
                file_pn = os.path.join(docset["directory"], file_fn + ".raml")
                files.append(file_pn)
        json_packet["config"]["raml"] = files
    if items_upload:
        json_packet["config"]["upload"] = items_upload
    return json_packet

def main():
    exit_code = 0
    json_apidocs = []
    (json_repos, json_old_config, list_modules_test, delay) = get_options()
    list_modules = list_api_modules(json_repos)
    if list_modules_test:
        list_modules = set(list_modules_test)
    for mod_name in list_modules:
        try:
            old_config = json_old_config[mod_name]
        except KeyError:
            old_config = {}
        (items_upload, json_config) = inspect_s3(mod_name)
        if json_config or items_upload or old_config:
            config_packet = assemble_config_packet(mod_name, json_config, items_upload, old_config)
            json_apidocs.append(config_packet)
        sleep(delay)
    store_config(json_apidocs)
    report_summary(json_apidocs, json_old_config)
    logging.shutdown()
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
