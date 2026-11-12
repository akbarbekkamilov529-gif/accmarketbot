from __future__ import annotations

from app.i18n import t


class LocalizedError(Exception):
    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        super().__init__(key)

    def localized(self, locale: str | None = None) -> str:
        return t(self.key, locale, **self.params)


def error_text(exc: BaseException, locale: str | None = None) -> str:
    if isinstance(exc, LocalizedError):
        return exc.localized(locale)
    return t("errors.unexpected", locale)
