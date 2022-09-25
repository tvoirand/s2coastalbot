"""Script to read s2coastalbot logs.
"""

# standard imports
import os
import argparse
from pathlib import Path
import datetime

# third party imports
import pandas as pd

# current project imports


def read_logs(log_file):
    """Read s2coastalbot logs.

    Parameters
    ----------
    log_file : Path
    """

    # initiate logs dataframe
    logs = pd.DataFrame(columns=["date", "pid", "level", "message"])

    # read log file
    with open(log_file, "r") as infile:

        # initiate some loop variables
        current_pid = infile.readline().split()[4][1:-2]
        message = ""

        for line in infile.readlines():

            # read process id
            try:
                pid = line.split()[4][1:-2]
            except IndexError:
                continue

            if (
                pid != current_pid
            ):  # in case of new process, store infos from previous line
                logs.loc[len(logs)] = [
                    datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f"),
                    current_pid,
                    level,
                    message,
                ]
                current_pid = pid

            date_str = line.split()[0]
            level = line.split()[5][1:-1]
            message = " ".join(line.split()[6:])

    print(logs)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file")
    args = parser.parse_args()

    read_logs(Path(args.input_file))
