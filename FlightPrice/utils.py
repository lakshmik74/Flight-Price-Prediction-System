from django.db import connection


def ensure_signup_table():
    with connection.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signup (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            password VARCHAR(50) NOT NULL,
            contact_no VARCHAR(12) NOT NULL,
            email_id VARCHAR(50) NOT NULL,
            address VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
