import logging
import os
import sys

import requests
import yaml


def iterate_urls(node):
    for version, version_data in node.items():
        if 'sha256' in version_data:
            url = version_data['url']
            sha = version_data['sha256']
            if isinstance(url, str):
                yield version, url, sha
            else:
                for url_ in url:
                    yield version, url_, sha


def main(path: str) -> int:
    if path.endswith('conandata.yml'):
        path = path[0:-13]
    with open(os.path.join(path, 'conandata.yml'), encoding='utf-8') as file:
        conandata = yaml.safe_load(file)

    shas: dict[str, str] = {}
    urls: list[str] = []
    versions_not_in_url = []
    at_least_one_version_in_url = False

    for version, url, sha in iterate_urls(conandata['sources']):

        if sha in shas and shas[sha] != version:
            print(f"sha256 {sha} is present twice for version {version}\n")
        else:
            shas[sha] = version

        if url in urls:
            print(f"url {url} is present twice for version {version}\n")
        else:
            urls.append(url)

        if url.startswith("http://"):
            logging.warning("url %s uses non secure http", url)
        elif not url.startswith("https://"):
            logging.warning("unknown url scheme %s", url)

        version = version.lower()
        url = url.lower()
        if not version.startswith("cci."):
            if (version in url) or \
                (version.replace('.', '') in url) or \
                (version.replace('.', '_') in url) or \
                (version.replace('-', '') in url) or \
                (version.endswith(".0") and version[:-2] in url):
                at_least_one_version_in_url = True
            else:
                versions_not_in_url.append((version, url))

        if url.endswith(".tar.gz"):
            new_url = url[:-2] + "xz"
            try:
                response = requests.head(new_url, timeout=10)
                if response.ok:
                    print(f"more compact archive exists at {new_url}\n")
                else:
                    new_url = url[:-2] + "bz2"
                    response = requests.head(new_url, timeout=10)
                    if response.ok:
                        print(f"more compact archive exists at {new_url}\n")
            except requests.exceptions.Timeout:
                logging.warning("timeout when contacting %s", url)
            except requests.exceptions.ConnectionError:
                logging.warning("connection error when contacting %s", url)
    if at_least_one_version_in_url:
        for vers in versions_not_in_url:
            print(f"url of {vers} does not contain version\n")

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit(main('.'))
    sys.exit(main(sys.argv[1]))
