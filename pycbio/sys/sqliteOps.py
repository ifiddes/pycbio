"""
Convenience library for interfacing with a sqlite database.
TODO: use modern SQLAlchemy instead of this.
TODOv2: SQLAlchemy is hard, man.
"""
import os
from collections import defaultdict
import sqlite3 as sql
import pandas as pd
from pycbio.sys.dataOps import flatten_defaultdict_list

__author__ = "Ian Fiddes"


class ExclusiveSqlConnection(object):
    """Context manager for an exclusive SQL connection"""
    def __init__(self, path, timeout=6000):
        self.path = path
        self.timeout = timeout

    def __enter__(self):
        self.con = sql.connect(self.path, timeout=self.timeout, isolation_level="EXCLUSIVE")
        try:
            self.con.execute("BEGIN EXCLUSIVE")
        except sql.OperationalError:
            raise RuntimeError("Database still locked after {} seconds.".format(self.timeout))
        return self.con

    def __exit__(self, exception_type, exception_val, trace):
        self.con.commit()
        self.con.close()


def attach_database(con, path, name):
    """
    Attaches another database found at path to the name given in the given connection.
    """
    con.execute("ATTACH DATABASE '{}' AS {}".format(path, name))


def open_database(path, timeout=6000):
    con = sql.connect(path, timeout=timeout)
    cur = con.cursor()
    return con, cur


def execute_query(cur, query):
    """
    Wraps around cur.execute(query) to handle exceptions and report more useful information than what sqlite3 does
    by default.
    """
    try:
        return cur.execute(query)
    except sql.OperationalError, exc:
        raise RuntimeError("query failed: {}\nOriginal error message: {}".format(query, exc))


def get_query_ids(cur, query):
    """
    Returns a set of aln_ids which are OK based on the definition of OK in config.py that made this query.
    In other words, expects a query of the form SELECT AlignmentId FROM stuff
    """
    try:
        return {x[0] for x in cur.execute(query)}
    except sql.OperationalError, exc:
        raise RuntimeError("query failed: {}\nOriginal error message: {}".format(query, exc))


def get_query_dict(cur, query):
    """
    Returns a set of aln_ids which are OK based on the definition of OK in config.py that made this query.
    In other words, expects a query of the form SELECT AlignmentId,<other stuff> FROM stuff
    """
    try:
        return {x[0]: x[1] if len(x) == 2 else x[1:] for x in cur.execute(query)}
    except sql.OperationalError, exc:
        raise RuntimeError("query failed: {}\nOriginal error message: {}".format(query, exc))


def get_non_unique_query_dict(cur, query, flatten=True):
    """
    Same as get_query_dict, but has no guarantee of uniqueness. Therefore, the returned data structure is a
    defaultdict(list)
    """
    d = defaultdict(list)
    try:
        for r in cur.execute(query):
            d[r[0]].append(r[1:])
    except sql.OperationalError, exc:
        raise RuntimeError("query failed: {}.\nOriginal error message: {}".format(query, exc))
    return flatten_defaultdict_list(d) if flatten is True else d


def get_multi_index_query_dict(cur, query, num_indices=2):
    """
    Similar to get_non_unique_query_dict, but instead produces a layered dict of dicts where the number of layers
    is the num_indicies. Expects the query to be in the form Index1,Index2,IndexN,data and will produce the data
    structure {Index1: {Index2: data}}.
    """
    d = {}
    try:
        for r in cur.execute(query):
            last_layer = d
            for i in xrange(num_indices - 1):
                if r[i] not in last_layer:
                    last_layer[r[i]] = {}
                last_layer = last_layer[r[i]]
            last_layer[r[i + 1]] = r[i + 2:]
    except sql.OperationalError, exc:
        raise RuntimeError("query failed: {}.\nOriginal error message: {}".format(query, exc))
    return d


def write_dict(data_dict, database_path, table, index_label="AlignmentId"):
    """
    Writes a dict of dicts to a sqlite database.
    """
    df = pd.DataFrame.from_dict(data_dict)
    df = df.sort_index()
    with ExclusiveSqlConnection(database_path) as con:
        df.to_sql(table, con, if_exists="replace", index_label=index_label)


def write_csv(csv_path, database_path, table, sep=",", index_col=0, header=0, index_label="AlignmentId"):
    """
    Writes a csv/tsv file to a sqlite database. Assumes that this table has a header
    """
    df = pd.read_table(csv_path, sep=sep, index_col=index_col, header=header)
    df = df.sort_index()
    with ExclusiveSqlConnection(database_path) as con:
        df.to_sql(table, con, if_exists="replace", index_label=index_label)
