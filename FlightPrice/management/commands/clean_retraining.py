from pathlib import Path
from django.core.management.base import BaseCommand

    try:
    # Import the helper from the app views so we reuse the same logic and DB access
    from FlightPrice.views import _clean_retraining_history
except Exception:
    _clean_retraining_history = None


class Command(BaseCommand):
    help = 'Remove RetrainingHistory entries whose model artifact files are missing.'

    def add_arguments(self, parser):
        parser.add_argument('--models-dir', help='Path to models directory', default=None)
        parser.add_argument('--dry-run', action='store_true', help='Only show what would be removed')

    def handle(self, *args, **options):
        if _clean_retraining_history is None:
            self.stdout.write(self.style.ERROR('Cleaner helper not available.'))
            return

        models_dir = Path(options['models_dir']) if options.get('models_dir') else None
        deleted, failed = _clean_retraining_history(models_dir=models_dir)

        if options.get('dry_run'):
            self.stdout.write(f"Would remove {deleted} entries. Failures: {len(failed)}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Removed {deleted} entries."))
            if failed:
                self.stdout.write(self.style.WARNING(f"Failed: {failed}"))
