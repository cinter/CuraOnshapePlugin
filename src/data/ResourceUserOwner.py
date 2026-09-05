# Copyright (c) 2023 Erwan MATHIEU

from typing import Dict, Any

from UM.Qt.QtApplication import QtApplication

from .BaseElement import BaseElement


class ResourceUserOwner(BaseElement):
    """Represents a user-owned storage in the user storage space"""

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data, icon = QtApplication.getInstance().getTheme().getIcon('People', 'default').toString())
