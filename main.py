#! /usr/bin/env python
import pickle
import datetime
import json
from pathlib import Path

import pandas as pd
from googleapiclient import errors

from src.auth import credentials_func
from src.queries import search_file, export_file, upload_file, trash_file
from src.bkp_helpers import create_bkp_history, handle_filetype


# For optaining google's credentials.json follow the Google Drive API Python Quickstart guide
# https://developers.google.com/drive/api/v3/quickstart/python

# when modifying SCOPES, delete token.pickle
SCOPES = ["https://www.googleapis.com/auth/drive"]
DIR = Path("data/interim/")
FILEPATH = Path(DIR / "files")
BKP_TABLE_NAME = "df_bkp_history.pkl"
ORPHANS_FOLDER_ID = "1j_sTgDdrkBtAzTw-rsBUlqq_qxQw4CeF"


def main():
    FILEPATH.mkdir(parents=True, exist_ok=True)
    drive_service = credentials_func(SCOPES)
    df_bkp_history = get_bkp_history(drive_service, DIR)
    df_bkp_history = update_bkp_history(drive_service, df_bkp_history)
    df_bkp_history = run_update(drive_service, df_bkp_history)
    print("DONE!")


def get_bkp_history(drive_service, DIR):
    """
    Import bkp_id pickle file, if there is none, initialize it

    :return: df_bkp_history dataframe, with list of files
    :rtype: pd.DataFrame
    """
    # Import bkp_id pickle file, if it exists
    while True:
        try:
            df_bkp_history = pd.read_pickle(Path(DIR / BKP_TABLE_NAME))
            break
        except FileNotFoundError:
            DIR.mkdir(parents=True, exist_ok=True)
            df_bkp_history = create_bkp_history(drive_service, DIR)
            df_bkp_history.to_pickle(Path(DIR / BKP_TABLE_NAME), protocol=4)
            print(
                f"""
                Couldn't find {Path(DIR / BKP_TABLE_NAME)}. 
                Created initial file {BKP_TABLE_NAME} in respective folder.
                """
            )
            break

    return df_bkp_history


def run_update(drive_service, df):
    """
    Take ids and status from df_bkp_history table. Check if files are new. 
    runs bkp process
    """
    for i in df.index:
        # fetch file metadata to be used in loop
        filename = df.loc[i, "name"]
        file_id = df.loc[i, "id"]
        mimetype = df.loc[i, "mimeType"]
        parents = df.loc[i, "parents"]
        modifiedTime = df.loc[i, "modifiedTime"]
        bkp_id = df.loc[i, "bkp_id"]
        bkp_modifiedTime = df.loc[i, "bkp_modifiedTime"]

        # define format for export (mimetype_exp)
        mimetype_exp, filename_exp, filepath_exp = handle_filetype(
            mimetype, filename, file_id, FILEPATH
        )

        # Skip file which was not modified since it's last backup
        if modifiedTime < str(bkp_modifiedTime):
            print(
                "file has not been modified",
                filename,
                bkp_id,
                modifiedTime,
                bkp_modifiedTime,
            )

        # Backup file
        else:
            try:
                export_file(drive_service, file_id, mimetype_exp, filepath_exp)

                if parents == "no parents":
                    parents = [ORPHANS_FOLDER_ID]
                    print(f"file stored in z_bkp_misc_files folder, ID: {parents}.")

                exp_data = upload_file(
                    drive_service, filename_exp, filepath_exp, mimetype_exp, parents
                )

                if bkp_id == "no-bkp-yet":
                    file_status = "New file"
                elif modifiedTime >= bkp_modifiedTime:
                    file_status = "Existing file"
                    # move old backup file to gdrive-bin
                    trash_file(drive_service, df.loc[i, "bkp_id"])

                print(
                    file_status,
                    filename,
                    exp_data[0],
                    modifiedTime,
                    bkp_modifiedTime,
                    filepath_exp,
                )

                # update df_bkp_history
                df.loc[i, "bkp_id"] = exp_data[0]
                df.loc[i, "bkp_modifiedTime"] = exp_data[1]
                df.loc[i, "bkp_issue"] = "no"

                print(
                    f"bkp_id {exp_data[0]} and modifiedTime {exp_data[1]} added in df_bkp_history"
                )

            except errors.HttpError as error:
                print(f"Could not process file {filename} with id {file_id}.")
                print(f"Error: {error}")
                df.loc[i, "bkp_issue"] = "yes"

    df.to_pickle(Path(DIR / "df_bkp_history.pkl"), protocol=4)

    return df


def update_bkp_history(drive_service, df):
    """
    Create new bkp table resembling current drive. Update existing 
    df_bkp_history.
    """
    df_new = create_bkp_history(drive_service, DIR)

    for i in df_new.index:
        # add new files to list
        if i not in df.index:
            df = df.append(df_new.loc[i])
            print(f"found new file {i, df.loc[i, 'name']}.")
        # update existing file in bkp_df if it's been updated
        elif df_new.loc[i, "modifiedTime"] > df.loc[i, "modifiedTime"]:
            df.loc[i, "modifiedTime"] = df_new.loc[i, "modifiedTime"]
            df.loc[i, "name"] = df_new.loc[i, "name"]
            df.loc[i, "parents"] = df_new.loc[i, "parents"]
            print(f"found modified file {i, df.loc[i, 'name']}.")

    df = df.sort_values("modifiedTime", ascending=False)

    return df


if __name__ == "__main__":
    main()
