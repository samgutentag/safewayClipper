#! /usr/bin/env python3

"""Chart data from clipper logs to a graph

Use this script to help isolate when your store updates/refreshes clickable
offers and dial in when to run the clipper.

Inspiration from https://gutentag.co/google_python_docstrings
and https://gutentag.co/google_python_styleguide

Use CalVer versioning as described at https://calver.org/

"""

__authors__ = ["Sam Gutentag"]
__email__ = "developer@samgutentag.com"
__maintainer__ = "Sam Gutentag"
__version__ = "2020.07.24dev"
# "dev", "alpha", "beta", "rc1"

import logging
import os
from datetime import datetime
from glob import glob

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def setup_logging():
    """Set up  logging filename and ensure logging directory exists."""
    # name of this file
    this_file = os.path.splitext(os.path.basename(__file__))[0]

    log_datetag = datetime.today().strftime("%Y%m%d")

    # construct name of log file
    log_file = f"{this_file}_logfile_{log_datetag}.txt"

    # ensure logging directory exists
    this_dir = os.path.dirname(os.path.realpath(__file__))
    log_dir = os.path.join(this_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # logging settings
    logging.basicConfig(filename=os.path.join(log_dir, log_file),
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # logging.disable(logging.CRITICAL)
    logging.info("\n\n\n\n")
    logging.info("-" * 80)


def get_clipper_data(*args):
    """Collect csv from ./data/ dir and compose dataframe

    Returns:
        data (dataframe): all csv data composed in single pandas dataframe

    Raises:
        AssertionError: no files found in data directory, nothing to collect

    """
    files = glob("./data/*.csv")

    if len(files) == 0:
        raise AssertionError(f"No files could be found in './data/ directory")

    chunks = []
    for f in files:
        logging.info(f"\tcolleting file {f}")
        chunk = pd.read_csv(f)
        chunks.append(chunk)

    logging.info("merging chunks")
    data = pd.concat(chunks)

    data.drop_duplicates(inplace=True)

    logging.info("formatting datetime column")
    data["datetime"] = pd.to_datetime(data["datetime"])

    logging.info("setting index to datetime")
    data.set_index(data["datetime"], inplace=True)
    data.drop(["datetime"], axis=1, inplace=True)

    data = data.sort_index()

    # drop all zero rows
    data = data.loc[(data != 0).any(1)]

    logging.info("\t...done")

    return data


def generate_report(*args):
    """Create box plot of weekly clip counts

    This is most useful when the clipper is run consistently. Sample
    chart is generated from a clipper that was run daily at 2am for
    4 months in the Bay Area.

    Sample chart can be found in the README.md

    """
    # make charts dir
    logging.info("Ensuring charts directory exists")

    this_dir = os.path.dirname(os.path.realpath(__file__))
    charts_dir = os.path.join(this_dir, "charts")
    if not os.path.isdir(charts_dir):
        os.makedirs(charts_dir)

    # get data
    logging.info("collecting data")
    data = get_clipper_data()

    # set seaborn plot style
    sns.set(style="whitegrid")

    # ensure boxes are in order by day of week, adjusted to start Sunday
    order = [6, 0, 1, 2, 3, 4, 5]
    sns.boxplot(x=data.index.dayofweek,
                y=data.coupons_clipped,
                palette="vlag",
                order=order)

    logging.info("plotting data")
    plt.title("Safeway Clipper Report")

    # set x and y ticks and axis labels
    plt.xticks(ticks=[x for x in range(0, 7)],
               labels=["SUN", "MON", "TUES", "WED", "THUR", "FRI", "SAT"],
               rotation=0)
    plt.xlabel("Day of Week")

    plt.ylabel("Clip Count")

    plt.tight_layout()

    # save to file
    chart_file = os.path.join(charts_dir, "clipper_report.png")
    logging.info(f"saving chart to file {chart_file}")
    plt.savefig(chart_file)
    plt.close()

    logging.info("\t...done")


if __name__ == "__main__":
    setup_logging()
    generate_report()
