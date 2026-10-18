"""Safe display-only normalization for the local client inventory."""

def readiness_rows(report):
    if not isinstance(report, dict) or not isinstance(report.get('rows'), list):
        raise ValueError('invalid local client report')
    result = []
    for item in report['rows'][:32]:
        if not isinstance(item, dict):
            continue
        values = []
        for key in ('protocol', 'client', 'status'):
            value = item.get(key, '')
            if not isinstance(value, str):
                raise ValueError('invalid client entry')
            values.append(value[:120].replace('\n', ' ').replace('\r', ' '))
        result.append(tuple(values))
    return result
