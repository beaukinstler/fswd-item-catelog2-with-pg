import sys
import os
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))



path = PROJECT_ROOT
#path = '/var/www/scripts/catalog'
python_home = '/home/vagrant/.local/share/virtualenvs/fswd-item-catelog2-with-pg-CycFicZs'

activate_this = python_home + '/bin/activate_this.py'
exec(open(activate_this).read(), {'__file__':activate_this})

if path not in sys.path:
   sys.path.insert(0, path)
import psycopg2
from main_app import app as application

