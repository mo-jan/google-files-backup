#! /usr/bin/env python
import datetime
from pathlib import Path

import pandas as pd

from src.queries import search_file


def create_bkp_history(SCOPES, DIR):
    """
    Create bkp table. Add columns needed for backup processes.
    """
    df = search_file(
        SCOPES,
        1000,  # check if this is enough.
        "trashed = false and mimeType = 'application/vnd.google-apps.document' or mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'application/vnd.google-apps.presentation'",
    )

    df = df.set_index("id", drop=False)
    df["parents"].fillna("no parents", inplace=True)
    df["bkp_id"] = "no-bkp-yet"
    df["bkp_modifiedTime"] = datetime.datetime(2001, 11, 11, 11, 11, 11)
    df["bkp_issue"] = "no-bkp-yet"

    return df


def handle_filetype(mimetype, filename, file_id, filepath):
    """
    Handle mimetype, filename, filepath of to-be-exported file
    """

    if mimetype == "application/vnd.google-apps.document":
        mimetype_exp = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filetype = ".docx"
    elif mimetype == "application/vnd.google-apps.spreadsheet":
        mimetype_exp = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filetype = ".xlsx"
    elif mimetype == "application/vnd.google-apps.presentation":
        mimetype_exp = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        filetype = ".pptx"
    else:
        print("No google-native doc, sheets or presentation found")
    filename_exp = str(filename + "_" + file_id + "_bkp" + filetype)
    filepath_exp = str(filepath / str(filename + "_" + file_id + "_bkp" + filetype))

    return mimetype_exp, filename_exp, filepath_exp
