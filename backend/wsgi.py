"""
WSGI configuration for PythonAnywhere

This file is used by PythonAnywhere to run the FastAPI application.
Update the path below to match your PythonAnywhere username.
"""
import sys
import os

# Update this path with your PythonAnywhere username
# Example: /home/yourusername/reading-development-app-main/backend
project_home = '/home/USERNAME/reading-development-app-main/backend'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Change to the project directory
os.chdir(project_home)

# Import the FastAPI app
from main import app

# PythonAnywhere expects 'application' variable for WSGI
application = app
