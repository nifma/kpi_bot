import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

AUTH_TOKEN = os.getenv("AUTH_TOKEN")

db_connection_config = {
    "host": os.getenv("HOST"),
    "port": int(os.getenv("PORT", 3306)),
    "user": os.getenv("USER"),
    "password": os.getenv("PASSWORD"),
    "database": os.getenv("DATABASE")
}


SOCKS5_PROXY = os.getenv("SOCKS5_PROXY", "")

SOCKET_IO_URL = os.getenv("SOCKET_IO_URL")

KPI_API_URL = os.getenv("KPI_API_URL")
