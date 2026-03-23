import sqlite3

source = sqlite3.connect('/home/sadmin/Desktop/Task Management Webapp/tasks.db')
backup = sqlite3.connect('backup.db')

source.backup(backup)

backup.close()
source.close()