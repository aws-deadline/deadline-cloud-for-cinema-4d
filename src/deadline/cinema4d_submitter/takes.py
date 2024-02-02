# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from enum import IntEnum


class TakeSelection(IntEnum):
    """Enum used for determining how to retrieve takes"""

    MAIN = 1
    ALL = 2
    MARKED = 3
    CURRENT = 4
