# Copyright (c) 2023 Erwan MATHIEU

from typing import Dict, Any

from UM.Qt.QtApplication import QtApplication

from .BaseElement import BaseElement


class Storage(BaseElement):
    """Represents a storage place for the user, e.g. 'created by me' or 'shared with me' """

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data,
                         settable_as_default = True,
                         icon = QtApplication.getInstance().getTheme().getIcon('Folder', 'medium').toString() if QtApplication.getInstance().getTheme() is not None else None)
