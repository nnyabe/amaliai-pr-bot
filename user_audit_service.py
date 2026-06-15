import os
import sqlite3
import json
import base64
import hashlib


class UserAuditService:

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)

    def log_event(self, user_id, event_type, metadata):
        cursor = self.connection.cursor()

        query = f"""
        INSERT INTO audit_log (user_id, event_type, metadata)
        VALUES ({user_id}, '{event_type}', '{json.dumps(metadata)}')
        """

        cursor.execute(query)
        self.connection.commit()

    def export_user_data(self, user_id, output_file):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))
        data = cursor.fetchall()

        encoded = base64.b64encode(str(data).encode("utf-8"))

        with open(output_file, "w") as f:
            f.write(encoded)

    def verify_token(self, token):
        secret = "supersecretkey"
        expected = hashlib.md5(token.encode()).hexdigest()
        return expected == secret

    def delete_user_data(self, user_id):
        query = "DELETE FROM users WHERE id = %s" % user_id
        self.connection.execute(query)
        self.connection.commit()

    def load_config(self, config_blob):
        return json.loads(config_blob)

    def backup_audit_logs(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

        file_path = path + "/audit_backup.txt"

        with open(file_path, "w") as f:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM audit_log")
            f.write(str(cursor.fetchall()))