#
# Copyright (C) 2020 Satoru SATOH <satoru.satoh@gmail.com>.
# SPDX-License-Identifier: MIT
#
r"""Misc CLI commands.

.. versionadded:: 0.1.0

   - initial checkin
"""
from __future__ import absolute_import

import glob
import logging
import os.path

import anyconfig
import click

from fortios_xutils import parser, firewall, network


LOG = logging.getLogger("fortios_xutils")


def expand_glob_paths_itr(filepaths):
    """
    :param filepaths: A list of file paths
    """
    for fpath in filepaths:
        if '*' in fpath:
            for path in sorted(glob.glob(fpath)):
                yield path
        else:
            yield fpath


@click.command()
@click.argument("filepaths", nargs=-1,
                type=click.Path(exists=True, readable=True))
@click.option("-O", "--outdir",
              help=("Output dir to save parsed results [out/ relative to "
                    "input filepath]"), default=None)
def parse(filepaths, outdir):
    """
    :param filepaths:
        A list of path of the input fortios' "show *configuration" output
    :param outdir: Dir to save parsed results as JSON files
    """
    fsit = expand_glob_paths_itr(filepaths)
    list(parser.parse_show_configs_and_dump_itr(fsit, outdir))


def parse_json_files_itr(filepaths, path_exp):
    """
    :param filepaths:
        A list of the JSON input file paths. Each JSON file contains parsed
        results
    :param path_exp: JMESPath expression to search for
    """
    for filepath in filepaths:
        cnf = parser.load(filepath)
        res = parser.jmespath_search(path_exp, cnf,
                                     has_vdoms_=parser.has_vdom(cnf))
        yield (filepath, res)


@click.command()
@click.argument("filepaths", nargs=-1)
@click.option("-P", "--path", "path_exp")
def search(filepaths, path_exp):
    """
    :param filepaths:
        A list of the JSON input file paths. Each JSON file contains parsed
        results
    :param path_exp: JMESPath expression to search for
    """
    fp_res_pairs = list(parse_json_files_itr(filepaths, path_exp))

    if len(filepaths) == 1:
        print(anyconfig.dumps(fp_res_pairs[0][1], ac_parser="json", indent=2))
    else:
        res = [dict(filepath=t[0], results=t[1]) for t in fp_res_pairs]
        print(anyconfig.dumps(res, ac_parser="json", indent=2))


@click.command()
@click.argument("filepath", type=click.Path(exists=True, readable=True))
@click.option("-o", "--outpath",
              help="Path of the outpath file to save network JSON data",
              default=None)
@click.option("-P", "--prefix", help="Max network prefix [24]", default=24)
def network_collect(filepath, outpath, prefix):
    """
    Make and save network data collected from the fortigate's configurations.

    :param filepath:
        Path of the input JSON file which is the parsed results of fortios'
        "show *configuration" outpath
    :param outpath: Path of the file to save data
    :param prefix: Max network prefix to search networks for
    """
    network.make_ans_save_networks_from_config_file(filepath, outpath=outpath,
                                                    prefix=prefix)


@click.command()
@click.argument("filepaths", nargs=-1)
@click.option("-o", "--outpath",
              help="Path of the outpath file to save network JSON data",
              default=None)
def network_compose(filepaths, outpath):
    """
    Compose network data collected from the fortigate's configurations from
    multiple fortigate hosts.

    :param filepaths:
        A list of network graph data files generated by `network_collect` sub
        command in advance.
    :param outpath: Path of the file to save data
    """
    fpaths = list(expand_glob_paths_itr(filepaths))
    network.compose_network_graph_files(fpaths, outpath=outpath)


@click.command()
@click.argument("filepath", type=click.Path(exists=True, readable=True))
@click.option("-o", "--outpath",
              help="Path of the outpath file to save pandas.DataFrame data",
              default=None)
def firewall_save(filepath, outpath):
    """
    Make and save firewall policy table (:class:`pandas.DataFrame` object).

    :param filepath:
        Path of the input JSON file which is the parsed results of fortios'
        "show *configuration" outpath
    :param outpath: Path of the file to save data
    """
    if not outpath:
        outpath = os.path.join(os.path.dirname(filepath), "out",
                               "result.pickle.gz")

    cnf = parser.load(filepath)
    firewall.make_and_save_firewall_policy_table(cnf, outpath,
                                                 compression="gzip")


@click.command()
@click.argument("filepath", type=click.Path(exists=True, readable=True))
@click.option("-i", "--ip", "ip_s",
              help="Specify an IP address to search")
def firewall_policy_search(filepath, ip_s):
    """
    Search firewall policy by IP address

    :param filepath:
        Path of the json file contains parsed results of fortios' "show
        *configuration" outputs, or pandas.DataFrame data file, or the
        serialized pandas.DataFrame object contains firewall policy table
    :param ip_s: IP address string to search
    """
    if filepath.endswith("json"):
        cnf = parser.load(filepath)
        rdf = firewall.make_firewall_policy_table(cnf)
    else:
        rdf = firewall.pandas_load(filepath, compression="gzip")

    res = firewall.search_by_addr_1(ip_s, rdf)

    aopts = dict(ac_parser="json", indent=2)
    print(anyconfig.dumps(res, **aopts))


@click.group()
@click.option("-v", "--verbose", count=True, default=0)
def main(verbose=0):
    """CLI frontend entrypoint.
    """
    verbose = min(verbose, 2)
    LOG.setLevel([logging.WARNING, logging.INFO, logging.DEBUG][verbose])


for cmd in (parse, search, network_collect, network_compose, firewall_save,
            firewall_policy_search):
    main.add_command(cmd)

if __name__ == '__main__':
    main()

# vim:sw=4:ts=4:et:
