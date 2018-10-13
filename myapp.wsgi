import sys
import os
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))



path = PROJECT_ROOT
#path = '/var/www/scripts/catalog'

if path not in sys.path:
   sys.path.insert(0, path)
import psycopg2
from main_app import app as application

