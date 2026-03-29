"""Generate a bcrypt hash for use in .env APP_PASSWORD_HASH."""
import sys
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = sys.argv[1] if len(sys.argv) > 1 else input("Password: ")
print(pwd_context.hash(password))
