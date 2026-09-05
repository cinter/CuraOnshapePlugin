# Copyright (c) 2023 Erwan MATHIEU

from typing import TYPE_CHECKING, Dict, Any, Callable, List, Optional

from .BaseElement import BaseElement

if TYPE_CHECKING:
    from ..api.OnshapeApi import OnshapeApi
    from .DocumentsTreeNode import DocumentsTreeNode
    from PyQt6.QtNetwork import QNetworkReply


class Tab(BaseElement):
    """Represents a tab of a document"""

    def __init__(self, data: Dict[str, Any], document_id: str, workspace_id: str):
        super().__init__(data)

        self._document_id: str = document_id
        self._workspace_id: str = workspace_id

    def _loadChildren(self,
                      api: 'OnshapeApi',
                      on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                      on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        api.listParts(self._document_id, self._workspace_id, self.id, on_finished, on_error)
