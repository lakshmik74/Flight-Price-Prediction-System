#!/usr/bin/env python3
"""
Simple script to run the FlightPrice Django project with MySQL.
"""

import os
import sys
import subprocess

def main():
    try:
        # Run the Django development server on port 8000
        subprocess.run([sys.executable, 'manage.py', 'runserver', '8000'], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"Error running server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 