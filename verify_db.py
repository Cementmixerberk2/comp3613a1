import sqlite3

conn = sqlite3.connect('database.db')
print('tables', conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
print('users', conn.execute('SELECT COUNT(*) FROM user').fetchone())
print('students', conn.execute('SELECT COUNT(*) FROM student').fetchone())
print('applications', conn.execute('SELECT COUNT(*) FROM application').fetchone())
print('positions', conn.execute('SELECT COUNT(*) FROM position').fetchone())
print('app rows', conn.execute('SELECT id, student_id, position_id, status FROM application ORDER BY id').fetchall())
