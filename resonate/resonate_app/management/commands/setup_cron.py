from django.core.management.base import BaseCommand
import subprocess
import os

class Command(BaseCommand):
    help = 'Setup cron job for automatic track fetching'
    
    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=60, 
                          help='Fetch interval in minutes')
    
    def handle(self, *args, **options):
        interval = options['interval']
        project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        cron_command = f"*/{interval} * * * * cd {project_path} && python manage.py fetch_tracks >> {project_path}/logs/fetch_tracks.log 2>&1"
        
        self.stdout.write(self.style.SUCCESS("Add this to your crontab:"))
        self.stdout.write(cron_command)
        self.stdout.write("\nTo add to crontab, run: crontab -e")