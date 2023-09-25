import json

from logs.models import AccessLog
from publications.models import Title
from sushi.models import SushiFetchAttempt


def lookup_json_by_title(title_id) -> (dict, list):
    title = ' '.join(Title.objects.values_list("name", flat=True).get(id=title_id).lower().split())
    batches = (
        AccessLog.objects.filter(target_id=title_id)
        .distinct()
        .values_list('import_batch', flat=True)
    )
    files = SushiFetchAttempt.objects.filter(import_batch__in=batches).only('data_file')
    out = {}
    err = []
    for file in files:
        try:
            data = json.load(file.data_file)
        except Exception as e:
            err.append((file.data_file.name, e))
        else:
            if file.data_file.name in out:
                continue
            out[file.data_file.name] = []
            for item in data["Report_Items"]:
                if ' '.join(item["Title"].lower().split()) == title:
                    out[file.data_file.name].append(item)
    return out, err
