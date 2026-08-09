import os
import json
import threading
from datetime import date as _date

APP_DIR = os.path.join(os.path.expanduser("~"), ".sticky_todo")
CREDENTIALS_FILE = os.path.join(APP_DIR, "credentials.json")
TOKEN_FILE = os.path.join(APP_DIR, "token.json")
SHEET_CONFIG_FILE = os.path.join(APP_DIR, "sheet_config.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SPREADSHEET_TITLE = "Sticky Todo Tracker"
PRIORITY_ORDER = ["Urgent", "High", "Medium", "Low", "None"]

HEADER_BG = {"red": 0.145, "green": 0.145, "blue": 0.157}
HEADER_FG = {"red": 0.91, "green": 0.91, "blue": 0.92}
TITLE_BG = {"red": 0.109, "green": 0.109, "blue": 0.118}
ACCENT_FG = {"red": 0.541, "green": 0.541, "blue": 0.573}
DONE_FG = {"red": 0.435, "green": 0.435, "blue": 0.463}
TEXT_FG = {"red": 0.91, "green": 0.91, "blue": 0.92}
ROW_ALT_BG = {"red": 0.129, "green": 0.129, "blue": 0.137}
WHITE_TEXT = {"red": 1, "green": 1, "blue": 1}

LOG_MAX_ROWS = 1000

try:
    import gspread
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    SHEETS_AVAILABLE = True
except Exception:
    SHEETS_AVAILABLE = False

_lock = threading.Lock()
_client = None
_spreadsheet = None
_charts_created = False


def is_configured():
    return SHEETS_AVAILABLE and os.path.exists(CREDENTIALS_FILE)


def _read_config():
    if os.path.exists(SHEET_CONFIG_FILE):
        try:
            with open(SHEET_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _write_config(cfg):
    try:
        with open(SHEET_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def get_sheet_url():
    cfg = _read_config()
    sid = cfg.get("spreadsheet_id")
    return f"https://docs.google.com/spreadsheets/d/{sid}" if sid else None


def _get_client():
    global _client
    if _client is not None:
        return _client
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    _client = gspread.authorize(creds)
    return _client


def _get_spreadsheet():
    global _spreadsheet, _charts_created
    if _spreadsheet is not None:
        return _spreadsheet
    client = _get_client()
    cfg = _read_config()
    sid = cfg.get("spreadsheet_id")
    if sid:
        try:
            _spreadsheet = client.open_by_key(sid)
            _charts_created = cfg.get("charts_created", False)
            return _spreadsheet
        except Exception:
            pass
    sh = client.create(SPREADSHEET_TITLE)
    try:
        sh.share(None, perm_type="anyone", role="writer")
    except Exception:
        pass
    _write_config({"spreadsheet_id": sh.id, "charts_created": False})
    _spreadsheet = sh
    _charts_created = False
    return sh


def _get_or_create_ws(sh, title, rows, cols):
    try:
        return sh.worksheet(title)
    except Exception:
        return sh.add_worksheet(title=title, rows=rows, cols=cols)


def _flatten(all_data):
    rows = []
    for key in sorted(all_data.keys(), reverse=True):
        try:
            d = _date.fromisoformat(key)
            display = d.strftime("%d %b %Y")
        except Exception:
            display = key
        for item in all_data[key]:
            status = "Done" if item.get("done") else "Pending"
            rows.append((display, item.get("text", ""),
                         item.get("priority", "None"), status))
    return rows


def push_data(all_data):
    if not is_configured():
        return
    with _lock:
        sh = _get_spreadsheet()
        _write_log(sh, all_data)
        _write_summary(sh, all_data)


def _text_format_request(sheet_id, start_row, end_row, start_col, end_col,
                          fg_color, strikethrough):
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "foregroundColor": fg_color,
                        "strikethrough": strikethrough,
                    }
                }
            },
            "fields": "userEnteredFormat.textFormat.foregroundColor,"
                      "userEnteredFormat.textFormat.strikethrough",
        }
    }


def _write_log(sh, all_data):
    ws = _get_or_create_ws(sh, "Log", rows=LOG_MAX_ROWS, cols=4)
    ws.clear()

    header = ["Date", "Task", "Priority", "Status"]
    rows = _flatten(all_data)
    ws.update(values=[header] + rows, range_name="A1")

    ws.format("A1:D1", {
        "backgroundColor": HEADER_BG,
        "textFormat": {"foregroundColor": HEADER_FG, "bold": True, "fontSize": 10},
        "horizontalAlignment": "LEFT",
    })
    ws.freeze(rows=1)
    try:
        ws.columns_auto_resize(0, 3)
    except Exception:
        pass

    sheet_id = ws.id
    requests = [
        _text_format_request(sheet_id, 1, LOG_MAX_ROWS, 1, 4, TEXT_FG, False),
    ]
    for i, r in enumerate(rows):
        if r[3] == "Done":
            row_index = i + 1
            requests.append(
                _text_format_request(sheet_id, row_index, row_index + 1, 1, 4,
                                      DONE_FG, True)
            )
    try:
        sh.batch_update({"requests": requests})
    except Exception:
        pass


def _write_summary(sh, all_data):
    global _charts_created
    ws = _get_or_create_ws(sh, "Summary", rows=40, cols=8)
    ws.clear()

    all_items = [item for items in all_data.values() for item in items]
    total = len(all_items)
    done = sum(1 for i in all_items if i.get("done"))
    pending = total - done

    priority_counts = {p: 0 for p in PRIORITY_ORDER}
    for i in all_items:
        p = i.get("priority", "None")
        priority_counts[p] = priority_counts.get(p, 0) + 1

    values = [
        ["Sticky Todo — Summary", ""],
        ["", ""],
        ["Total tasks", total],
        ["Completed", done],
        ["Pending", pending],
        ["", ""],
        ["Status", "Count"],
        ["Done", done],
        ["Pending", pending],
        ["", ""],
        ["Priority", "Count"],
    ] + [[p, priority_counts[p]] for p in PRIORITY_ORDER]

    ws.update(values=values, range_name="A1")

    ws.format("A1:B1", {
        "backgroundColor": TITLE_BG,
        "textFormat": {"foregroundColor": WHITE_TEXT, "bold": True, "fontSize": 12},
    })
    ws.format("A3:A5", {"textFormat": {"foregroundColor": ACCENT_FG, "bold": True}})
    ws.format("A7:B7", {"backgroundColor": HEADER_BG,
                         "textFormat": {"foregroundColor": HEADER_FG, "bold": True}})
    ws.format("A11:B11", {"backgroundColor": HEADER_BG,
                           "textFormat": {"foregroundColor": HEADER_FG, "bold": True}})
    try:
        ws.columns_auto_resize(0, 1)
    except Exception:
        pass

    if not _charts_created:
        _add_charts(sh, ws)
        _charts_created = True
        cfg = _read_config()
        cfg["charts_created"] = True
        cfg["spreadsheet_id"] = sh.id
        _write_config(cfg)


def _add_charts(sh, ws):
    sheet_id = ws.id

    def pie_request(title, row_start, row_end, anchor_row, anchor_col):
        return {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": title,
                        "pieChart": {
                            "legendPosition": "RIGHT_LEGEND",
                            "domain": {"sourceRange": {"sources": [{
                                "sheetId": sheet_id, "startRowIndex": row_start,
                                "endRowIndex": row_end, "startColumnIndex": 0,
                                "endColumnIndex": 1,
                            }]}},
                            "series": {"sourceRange": {"sources": [{
                                "sheetId": sheet_id, "startRowIndex": row_start,
                                "endRowIndex": row_end, "startColumnIndex": 1,
                                "endColumnIndex": 2,
                            }]}},
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": sheet_id, "rowIndex": anchor_row,
                                           "columnIndex": anchor_col},
                            "widthPixels": 380, "heightPixels": 260,
                        }
                    },
                }
            }
        }

    body = {"requests": [
        pie_request("Done vs Pending", 7, 9, 1, 3),
        pie_request("Tasks by Priority", 10, 16, 16, 3),
    ]}
    try:
        sh.batch_update(body)
    except Exception:
        pass

