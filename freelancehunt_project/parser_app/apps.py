import os
from modules._get_ads import run_parser

from django.apps import AppConfig


class ParserAppConfig(AppConfig):
    name = 'parser_app'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            self.start_scheduler()

    def start_scheduler(self):
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()

        # Налаштовуємо запуск, наприклад, кожні 15 хвилин
        scheduler.add_job(run_parser, 'interval', minutes=5)

        scheduler.start()
        print("Фоновий планувальник APScheduler успішно запущено!")
