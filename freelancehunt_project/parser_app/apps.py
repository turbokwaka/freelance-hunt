import os
import sys
from pathlib import Path

from django.apps import AppConfig


class ParserAppConfig(AppConfig):
    name = 'parser_app'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            self.start_scheduler()

    def start_scheduler(self):
        current_file = Path(__file__).resolve()
        root_dir = current_file.parent.parent.parent
        modules_path = root_dir / "modules"

        if str(modules_path) not in sys.path:
            sys.path.append(str(modules_path))

        from apscheduler.schedulers.background import BackgroundScheduler
        import get_ads

        scheduler = BackgroundScheduler()
        scheduler.add_job(get_ads.run_parser, 'interval', minutes=5)

        scheduler.start()
        print("✅ Фоновий планувальник APScheduler успішно запущено!")