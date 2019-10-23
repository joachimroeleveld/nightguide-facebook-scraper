from __future__ import print_function
from googleapiclient.discovery import build
import re
import functools


def get_facebook_credentials():
    SPREADSHEET_ID = '10b3js5BtM12HmQ6kPLJ4Fig_FyvX77IJlYS0wemKqd0'
    TAB_NAME = 'Accounts'
    READ_RANGE_NAME = '{}!A2:B1000'.format(TAB_NAME)

    service = build('sheets', 'v4', cache_discovery=False)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=READ_RANGE_NAME).execute()
    values = result.get('values', [])

    # Find first nonempty value
    index = None
    for index, val in reversed(list(enumerate(values))):
        if val[0] != '':
            index = index
            break

    # Delete read entry
    delete_range = '{tab}!A{index}:B{index}'.format(index=index + 2, tab=TAB_NAME)
    body = {'values': [['', '']]}
    sheet.values().update(range=delete_range, spreadsheetId=SPREADSHEET_ID, body=body,
                          valueInputOption='USER_ENTERED').execute()

    pair = values[index]
    return pair[0], pair[1]


def get_additional_event_ids(page_slug):
    SPREADSHEET_ID = '19TFT0BFhAr_BKp364X1z9gE4BvSh2OX_-ZODEd_OsAQ'
    READ_RANGE_NAME = '{}!A1:Q1000'.format(page_slug)

    service = build('sheets', 'v4', cache_discovery=False)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=READ_RANGE_NAME).execute()
    values = result.get('values', [])

    columns = values[0]

    venue_id_index = columns.index('venue_id')

    id_columns = [col for col in columns if 'id_' in col]
    id_column_indices = list(map(lambda col: columns.index(col), id_columns))

    def get_ids_for_venue(row):
        venue_id = row[venue_id_index]
        # Check if Mongo ID
        if not re.match('\w{24}', venue_id):
            return None
        # Get ID columns
        ids = map(lambda index: row[index] if index < len(row) else None, id_column_indices)
        ids_filtered = set(filter(lambda id: re.match('\d+', id) if id else False, ids))
        if not len(ids_filtered):
            return None
        return (venue_id, ids_filtered)

    ids_per_venue = {k: v for (k, v) in filter(None, map(get_ids_for_venue, values[1:]))}

    return ids_per_venue
