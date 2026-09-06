# Copyright (c) 2023 Erwan MATHIEU

from typing import Dict, Any, Callable, Optional, List, TYPE_CHECKING

from .BaseElement import BaseElement

if TYPE_CHECKING:
    from ..api.OnshapeApi import OnshapeApi
    from .DocumentsTreeNode import DocumentsTreeNode
    from PyQt6.QtNetwork import QNetworkReply


class Document(BaseElement):
    """Represents a document created by the user in his storage space"""

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data, allow_single_child_shortcut = True)

    def _loadChildren(self,
                      api: 'OnshapeApi',
                      on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                      on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        api.listWorkspaces(self.id, on_finished, on_error)