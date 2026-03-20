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

        # 2. Додаємо цю папку до шляхів пошуку Python, якщо її там ще немає
        if str(root_dir) not in sys.path:
            sys.path.append(str(root_dir))

        from apscheduler.schedulers.background import BackgroundScheduler
        from modules.get_ads import run_parser

        scheduler = BackgroundScheduler()

        # Налаштовуємо запуск, наприклад, кожні 15 хвилин
        scheduler.add_job(run_parser, 'interval', minutes=5)

        scheduler.start()
        print("Фоновий планувальник APScheduler успішно запущено!")
