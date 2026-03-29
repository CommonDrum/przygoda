"""Generate a PBKDF2-SHA256 hash for use in .env APP_PASSWORD_HASH."""
import hashlib
import sys

password = sys.argv[1] if len(sys.argv) > 1 else input("Password: ")
salt = sys.argv[2] if len(sys.argv) > 2 else input("JWT_SECRET_KEY: ")
dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
print(dk.hex())
