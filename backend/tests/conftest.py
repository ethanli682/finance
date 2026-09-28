import os

# Point the app at a throwaway database before anything imports app.config.
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://finance:finance@localhost:5432/finance_test"),
)
