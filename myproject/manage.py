#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Auto-fake migration for Render free plan (no shell access)
    if os.environ.get("RENDER") and len(sys.argv) > 1 and sys.argv[1] == "migrate":
        from django.core.management import call_command
        try:
            call_command("migrate", "myapp", "0021", fake=True)
        except Exception:
            pass

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
