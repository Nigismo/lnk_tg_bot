from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int

    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    MARZBAN_URL: str
    MARZBAN_USERNAME: str
    MARZBAN_PASSWORD: str

    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    CRYPTO_PAY_TOKEN: str = ""

    HAPP_PROVIDER_CODE: str = ""
    HAPP_AUTH_KEY: str = ""

    MAX_CONCURRENT: int = 1600

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = Settings()
