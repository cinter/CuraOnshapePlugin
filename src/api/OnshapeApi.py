# Copyright (c) 2023 Erwan MATHIEU

import json
import tempfile
import functools

from PyQt6.QtCore import QObject, pyqtSlot, QUrlQuery, QUrl

from typing import Callable, List, Dict, Optional, TYPE_CHECKING

from UM.Application import Application
from UM.TaskManagement.HttpRequestManager import HttpRequestManager
from UM.TaskManagement.HttpRequestScope import JsonDecoratorScope
from UM.Logger import Logger

from .ApiAuthScope import ApiAuthScope
from .AcceptBinaryDataScope import AcceptBinaryDataScope
from ..data.Folder import Folder
from ..data.Workspace import Workspace
from ..data.Tab import Tab
from ..data.Part import Part
from ..data.ResourceCompanyOwner import ResourceCompanyOwner
from ..data.ResourceUserOwner import ResourceUserOwner
from ..data.Storage import Storage
from ..data.Document import Document
from ..data.DocumentsTreeNode import DocumentsTreeNode

if TYPE_CHECKING:
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtNetwork import QNetworkReply


class OnshapeApi(QObject):
    """Manager giving access to the required calls to the remote Onshape REST API"""

    API_ROOT = 'https://cad.onshape.com/api/v14' # Stay with version 14, version 17 gives a different result for /globaltreenodes
    DEFAULT_REQUEST_TIMEOUT = 10  # seconds
    DOWNLOAD_REQUEST_TIMEOUT = 60 # seconds
    SEARCH_REQUEST_TIMEOUT = 20  # seconds

    def __init__(self):
        super().__init__()
        self._http: 'HttpRequestManager' = HttpRequestManager.getInstance()
        self._auth_scope: 'ApiAuthScope' = ApiAuthScope()
        self._json_scope: 'JsonDecoratorScope' = JsonDecoratorScope(self._auth_scope)
        self._binary_scope: 'AcceptBinaryDataScope' = AcceptBinaryDataScope(self._auth_scope)
        self._folder_cache: Dict[str, Dict] = {}

    @pyqtSlot(str)
    def setToken(self, token: str) -> None:
        """Sets the authentication token, which is required to make API calls"""
        self._auth_scope.setToken(token)

    def clearFolderCache(self) -> None:
        """Clears the folder cache; should be called when the document list is refreshed"""
        self._folder_cache.clear()

    def _onListDocumentsFinished(self,
                                 reply: 'QNetworkReply',
                                 on_finished: Callable[[List['DocumentsTreeNode'], bool, int], None],
                                 on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        data_json = bytes(reply.readAll()).decode()
        Logger.debug(str(data_json))
        data_json = json.loads(data_json)
        storage = UserStorage()
        storage.appendDocuments(data_json['items'])
        has_more = data_json['next'] is not None
        document_count = len(data_json['items'])

        def folders_finished(children: List['DocumentsTreeNode']):
            on_finished(children, has_more, document_count)

        self._getFolders(folders_finished, on_error, storage)

    def _onResponseReceived(self,
                            reply: 'QNetworkReply',
                            on_finished: Callable[[List['DocumentsTreeNode'], bool, int], None],
                            **kwargs) -> None:

        data_json = bytes(reply.readAll()).decode()
        Logger.debug(str(data_json))
        data_json = json.loads(data_json)

        nodes = []

        # Find the proper sub-element where relevant items are stored, not always the same
        if 'items' in data_json:
            items = data_json['items']
        else:
            items = data_json

        for item in items:
            # Identify the type of element based on the item data
            element = None
            if 'jsonType' in item:
                json_type = item['jsonType']

                if json_type == 'resource-owner':
                    resource_type = item['resourceType']
                    if resource_type == 'resourcecompanyowner':
                        element = ResourceCompanyOwner(item)
                    elif resource_type == 'resourceuserowner':
                        element = ResourceUserOwner(item)

                elif json_type == 'magic' and item['subType'] in [2, 12]: # Other types are not relevant
                    element = Storage(item)

                elif json_type == 'folder':
                    element = Folder(item)

                elif json_type == 'document-summary':
                    element = Document(item)

            elif 'type' in item:
                type = item['type']

                if type == 'workspace':
                    element = Workspace(item)

                elif type == 'Part Studio':
                    element = Tab(item, **kwargs)

            elif 'partId' in item:
                element = Part(item, **kwargs)

            if element:
                nodes.append(DocumentsTreeNode(element))

        url_load_next_page = data_json['next'] if 'next' in data_json else None

        on_finished(nodes, url_load_next_page)

    def _get(self,
             url: QUrl,
             on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
             on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None],
             **kwargs) -> None:

        Logger.debug(f"GET {url.toString()}")
        self._http.get(url.toString(),
                       scope = self._json_scope,
                       callback = functools.partial(self._onResponseReceived, on_finished = on_finished, **kwargs),
                       error_callback = on_error,
                       timeout = self.DEFAULT_REQUEST_TIMEOUT)

    def loadElements(self,
                     url: str,
                     on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                     on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:

        self._get(QUrl(url), on_finished, on_error)

    def listStorages(self,
                     on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                     on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:

        self._get(QUrl(f'{self.API_ROOT}/globaltreenodes'), on_finished, on_error)

    def listWorkspaces(self,
                       document_id: str,
                       on_finished: Callable[[List['DocumentsTreeNode']], None],
                       on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Lists the available workspaces in the given document"""

        self._get(QUrl(f'{self.API_ROOT}/documents/d/{document_id}/workspaces'), on_finished, on_error)

    def listTabs(self,
                 document_id: str,
                 workspace_id: str,
                 on_finished: Callable[[List['DocumentsTreeNode']], None],
                 on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Lists the available tabs (sub-documents) in the given document"""

        url = QUrl(f'{self.API_ROOT}/documents/d/{document_id}/w/{workspace_id}/elements')

        query = QUrlQuery()
        query.addQueryItem('withThumbnails', 'true')
        query.addQueryItem('elementType', 'PARTSTUDIO') # We can only get parts from PartStudios
        url.setQuery(query)

        self._get(url, on_finished, on_error, document_id=document_id, workspace_id=workspace_id)

    def listParts(self,
                  document_id: str,
                  workspace_id: str,
                  tab_id: str,
                  on_finished: Callable[[List['DocumentsTreeNode']], None],
                  on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Lists the available parts in the given tab"""

        url = QUrl(f'{self.API_ROOT}/parts/d/{document_id}/w/{workspace_id}/e/{tab_id}')

        query = QUrlQuery()
        query.addQueryItem('withThumbnails', 'true')
        query.addQueryItem('includeFlatParts', 'false')
        url.setQuery(query)

        self._get(url, on_finished, on_error, document_id=document_id, workspace_id=workspace_id, tab_id=tab_id)

    def loadThumbnail(self,
                      thumbnail_url: str,
                      on_finished: Callable[['QByteArray'], None],
                      on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Loads the thumbnail image, to be found at the given URL"""
        def response_received(reply: 'QNetworkReply'):
            on_finished(reply.readAll())

        self._http.get(thumbnail_url,
                       scope = self._binary_scope,
                       callback = response_received,
                       error_callback = on_error,
                       timeout = self.DEFAULT_REQUEST_TIMEOUT)

    def downloadParts(self,
                      document_id: str,
                      workspace_id: str,
                      tab_id: str,
                      parts_ids: List[str],
                      on_progress: Callable[[int, int], None],
                      on_finished: Callable[[str], None],
                      on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """
        Downloads the given part(s) as STL data into a local file.
        The finished callback receives the path of the created local file.
        The created file will be placed in a temporary folder. However, it is up to the caller to
        remove the file as soon as it is no more required.
        """
        def response_received(reply: 'QNetworkReply'):
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.stl', delete=False) as file:
                file.write(reply.readAll())
                on_finished(file.name)

        url = QUrl(f'{self.API_ROOT}/partstudios/d/{document_id}/w/{workspace_id}/e/{tab_id}/stl')

        query = QUrlQuery()
        query.addQueryItem('partIds', ','.join(parts_ids))
        query.addQueryItem('units', 'millimeter')
        query.addQueryItem('mode', 'binary')

        resolution = Application.getInstance().getPreferences().getValue('plugin_onshape/tesselation_resolution')
        if resolution == 'coarse':
            precision = '0.04'
        elif resolution == 'fine':
            precision = '0.01'
        else:
            precision = '0.02'

        query.addQueryItem('angleTolerance', precision)
        query.addQueryItem('chordTolerance', precision)

        query.addQueryItem('grouping', 'true')
        url.setQuery(query)

        self._http.get(url,
                       scope = self._binary_scope,
                       download_progress_callback = on_progress,
                       callback = response_received,
                       error_callback = on_error,
                       timeout = self.DOWNLOAD_REQUEST_TIMEOUT)

    def search(self,
               parent_id: str,
               search_query: str,
               on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
               on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Retrieves a single page of the found documents in the user storage"""

        url = QUrl(f'{self.API_ROOT}/documents/search')

        request_body = {}
        request_body["rawQuery"] = search_query
        request_body["parentId"] = parent_id
        request_body["documentFilter"] = 0

        Logger.debug(f"Process search request {json.dumps(request_body)}")

        self._http.post(url.toString(),
                        data = json.dumps(request_body).encode("utf-8"),
                        scope = self._json_scope,
                        callback = functools.partial(self._onListDocumentsFinished, on_finished=on_finished, on_error=on_error),
                        error_callback = on_error,
                        timeout = self.SEARCH_REQUEST_TIMEOUT)
