from __future__ import print_function
from googleapiclient.discovery import build

SPREADSHEET_ID = '10b3js5BtM12HmQ6kPLJ4Fig_FyvX77IJlYS0wemKqd0'
TAB_NAME = 'Accounts'
READ_RANGE_NAME = '{}!A2:B1000'.format(TAB_NAME)


def get_facebook_credentials():
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