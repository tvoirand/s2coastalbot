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
    logs = pd.DataFrame(columns=["date", "pid", "time_spent", "level", "message"])

    # read log file
    with open(log_file, "r") as infile:

        # initiate some loop variables
        first_line = infile.readline()
        start_time = datetime.datetime.strptime(first_line.split()[0], "%Y-%m-%dT%H:%M:%S.%f")
        current_pid = first_line.split()[4][1:-2]
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
                end_time = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
                logs.loc[len(logs)] = [
                    end_time,
                    current_pid,
                    (end_time - start_time).seconds / 60,
                    level,
                    message,
                ]
                current_pid = pid
                start_time = datetime.datetime.strptime(line.split()[0], "%Y-%m-%dT%H:%M:%S.%f")

            date_str = line.split()[0]
            level = line.split()[5][1:-1]
            message = " ".join(line.split()[6:])

    print(logs)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file")
    args = parser.parse_args()

    read_logs(Path(args.input_file))
