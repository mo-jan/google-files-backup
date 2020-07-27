#! /usr/bin/env python
import datetime
import io
from pathlib import Path

import pandas as pd
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


def search_file(drive_service, num_of_responses, query):
    """
    Search for files and store results of query in pd.DataFrame
    """
    results = (
        drive_service.files()
        .list(
            pageSize=num_of_responses,
            q=query,
            fields="nextPageToken, files(id, name, kind, exportLinks, mimeType, parents, size, createdTime, modifiedTime, trashed, ownedByMe, capabilities/canCopy, exportLinks/application)",
        )
        .execute()
    )
    items = results.get("files", [])

    if not items:
        print("No files found.")
    else:
        return pd.DataFrame(items)


def export_file(drive_service, file_id, mimetype, filepath):
    """
    Download google-native file, export it to the requested mime_type,
    save it at the filepath location on local OS.
    """
    request = drive_service.files().export_media(fileId=file_id, mimeType=mimetype)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    with io.open(filepath, "wb") as f:
        fh.seek(0)
        f.write(fh.read())


def upload_file(drive_service, filename, filepath, mimetype, parents):
    """
    Upload files to a specific folder
    """
    file_metadata = {"name": filename, "parents": parents}
    media = MediaFileUpload(filepath, mimetype=mimetype, resumable=True)
    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, modifiedTime")
        .execute()
    )
    bkpId = file.get("id")
    bkpModifiedTime = file.get("modifiedTime")

    return [bkpId, bkpModifiedTime]


def trash_file(drive_service, file_id):
    """
    Move file to bin on google drive
    """
    body = {"trashed": True}
    try: 
        updated_file = drive_service.files().update(fileId=file_id, body=body).execute()
        print(f"Moved old backup file to bin.")
        return updated_file
    except Exception:
        print(f"!!! did not find old bkp file with id {file_id}")

