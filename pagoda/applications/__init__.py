"""The module containing the builtin applications for Pagoda."""

from typing import Type

from .application import PagodaApplication

from .teahaz import TeahazApplication


def list_applications() -> list[Type[PagodaApplication]]:
    """Lists all registered applications."""

    return [TeahazApplication]
