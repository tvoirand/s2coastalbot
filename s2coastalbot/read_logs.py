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


def read_logs_folder(logs_folder):
    """Read s2coastalbot logs stored in the logs folder.

    Assumes that logs are stored in a rotating file, named *.log, *.log.1, *.log.2 etc, with
    highest number for oldest log file.

    Parameters
    ----------
    logs_folder : Path

    Returns
    -------
    logs_df : pd.DataFrame
    """

    log_files = sorted([f for f in logs_folder.iterdir() if ".log" in f.name], reverse=True)

    # read each log file so as to include processes that are spread across several logs files
    logs_df, last_process_start = read_log_file(log_files[0])
    for log_file in log_files[1:]:
        logs_df, last_process_start = read_log_file(log_file, logs_df, last_process_start)

    return logs_df


def read_log_file(log_file, logs_df=None, start_time=None):
    """Read s2coastalbot logs from one given log file.

    Parameters
    ----------
    log_file : Path
    logs_df : pd.DataFrame or None
    start_time : datetime.datetime or None

    Returns
    -------
    logs_df : pd.DataFrame
    start_time : datetime.datetime
        starting time of the last process logged in this file
    """

    # initiate logs dataframe
    if logs_df is None:
        logs_df = pd.DataFrame(columns=["date", "pid", "time_spent", "level", "message"])

    # read log file
    with open(log_file, "r") as infile:

        # initiate some loop variables
        first_line = infile.readline()
        current_pid = first_line.split()[4][1:-2]
        if start_time is None:
            start_time = datetime.datetime.strptime(first_line.split()[0], "%Y-%m-%dT%H:%M:%S.%f")
        message = ""

        for line in infile.readlines():

            # read process id
            try:
                pid = line.split()[4][1:-2]
            except IndexError:
                continue

            if pid != current_pid:  # in case of new process, store infos from previous line
                end_time = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
                logs_df.loc[len(logs_df)] = [
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

    return logs_df, start_time


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-lf", "--logs_folder")
    args = parser.parse_args()

    logs_df = read_logs_folder(Path(args.logs_folder))

    print(logs_df)
