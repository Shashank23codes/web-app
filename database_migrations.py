from flask import Flask
from flask_mysqldb import MySQL
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

def run_migrations():
    with app.app_context():
        cur = mysql.connection.cursor()
        try:
            # Migration 1: Add rejection tracking columns
            logger.info("Running migration 1: Adding rejection tracking columns")
            cur.execute("""
                ALTER TABLE donation_requests
                ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
                ADD COLUMN IF NOT EXISTS rejection_images TEXT,
                ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP NULL,
                ADD COLUMN IF NOT EXISTS rejected_by INT
            """)
            
            # Migration 2: Add blocked status to users
            logger.info("Running migration 2: Adding blocked status to users")
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE
            """)
            
            # Migration 3: Add feedback tracking
            logger.info("Running migration 3: Adding feedback tracking")
            cur.execute("""
                ALTER TABLE donation_requests 
                ADD COLUMN IF NOT EXISTS feedback_given BOOLEAN DEFAULT FALSE
            """)
            
            mysql.connection.commit()
            logger.info("All migrations completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            mysql.connection.rollback()
        finally:
            cur.close()

if __name__ == "__main__":
    run_migrations()
