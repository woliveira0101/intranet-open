
def parse_whiteboard(wb):
    wb = wb.strip().replace('[', ' ').replace(']', ' ')
    if wb:
        return dict(i.split('=', 1) for i in wb.split() if '=' in i)
    return {}
