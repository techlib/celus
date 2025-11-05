from importlib import import_module


def test_celery_task_routes(settings):
    for celery_task, spec in settings.CELERY_TASK_ROUTES.items():
        module_str, function_str = celery_task.rsplit(".", 1)
        module = import_module(module_str)
        assert hasattr(module, function_str), f"Checking {celery_task}"
        assert "queue" in spec
        assert spec["queue"] in [
            "celery",
            "ch_export",
            "export",
            "import",
            "interest",
            "normal",
            "preflight",
            "sushi",
        ], f"Invalid queue {spec['queue']}"


def test_celerybeat_schedule(settings):
    for record in settings.CELERY_BEAT_SCHEDULE.values():
        module_str, function_str = record["task"].rsplit(".", 1)
        module = import_module(module_str)
        assert hasattr(module, function_str), f"Checking {record['task']}"
