# Copyright (c) 2023 Erwan MATHIEU

import re
from typing import TYPE_CHECKING, Optional, Callable, List, Dict, Any

from datetime import datetime

if TYPE_CHECKING:
    from PyQt6.QtNetwork import QNetworkReply

    from ..api.OnshapeApi import OnshapeApi
    from .DocumentsTreeNode import DocumentsTreeNode

class BaseElement:
    """
    Base class for the elements retrieved from the Onshape API
    The elements are organized as such:
    Root > (Folder) > Document > Workspace > Tab (Part Studio) > Part
    """

    regex_thumbnail_size = re.compile('^([0-9]+)x([0-9]+)$')

    def __init__(self,
                 data: Dict[str, Any],
                 name: str = None,
                 id: str = None,
                 short_desc: Optional[str] = None,
                 last_modified_date: Optional['datetime'] = None,
                 last_modified_by: Optional[str] = None,
                 icon: Optional[str] = None,
                 has_children: bool = True,
                 is_downloadable: bool = False,
                 allow_single_child_shortcut: bool = False):
        """
        Base constructor

        :param name: The user-readable name of the object
        :param id: The unique ID of the object
        :param short_desc: Short basic description of the object (or one of its main properties)
        :param last_modified_date: Object last modification date
        :param last_modified_by: Name of the user at the origin of the last modification
        :param thumbnail_url: Remote URL to an image of the object
        :param icon: Local URL to an icon of the object
        :param has_children: Indicates whether the object may have children, or if it is a leaf
                             object in the storage tree
        :param is_downloadable: Indicates whether this object may be downloaded, or is just
                                a container
        :param allow_single_child_shortcut: Indicates whether this object may be hidden in case it
                                            has a single child, in which case we will directly
                                            navigate to it
        """

        self.name: str = data['name'] if name is None and data is not None else name
        self.id: str = data['id'] if id is None and data is not None else id
        self.short_desc: Optional[str] = (data['owner']['name'] if ('owner' in data and data['owner'] is not None) else None) if short_desc is None and data is not None else short_desc
        self.last_modified_date: Optional['datetime'] = (datetime.fromisoformat(data['modifiedAt']) if ('modifiedAt' in data and data['modifiedAt'] is not None) else None) if last_modified_date is None and data is not None else last_modified_date
        self.last_modified_by: Optional[str] = (data['modifiedBy']['name'] if ('modifiedBy' in data and data['modifiedBy'] is not None) else None) if last_modified_by is None and data is not None else last_modified_by
        self.thumbnail_url: Optional[str] = (BaseElement._findThumbnailUrl(data['thumbnailInfo']['sizes']) if ('thumbnailInfo' in data and data['thumbnailInfo'] is not None) else BaseElement._findThumbnailUrl(data['thumbnail']['sizes']) if ('thumbnail' in data and data['thumbnail'] is not None) else None) if data is not None else None
        self.children_url: Optional[str] = (data['treeHref'] if ('treeHref' in data and data['treeHref'] is not None) else data['href'] if 'href' in data else None) if data is not None else None
        self.icon: Optional[str] = icon
        self.has_children: bool = has_children
        self.is_downloadable: bool = is_downloadable
        self._allow_single_child_shortcut: bool = allow_single_child_shortcut

    def loadChildren(self,
                     api: 'OnshapeApi',
                     on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                     on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Starts loading the children of the current object, and immediatly start loading the child
           in case there is a single one and we allow for shortcutting

        :param api The API object to be used to load the children
        :param on_finished Callback function called on success. Receives (children, url_load_next_page).
        :param on_error Callback function called on communication error
        """
        def shortcut_callback(children: List['DocumentsTreeNode'], url_load_next_page: Optional[str]):
            if len(children) == 1:
                children[0].element.loadChildren(api, on_finished, on_error)
            else:
                on_finished(children, url_load_next_page)

        self._loadChildren(api,
                           shortcut_callback if self._allow_single_child_shortcut else on_finished,
                           on_error)

    def _loadChildren(self,
                      api: 'OnshapeApi',
                      on_finished: Callable[[List['DocumentsTreeNode'], Optional[str]], None],
                      on_error: Callable[['QNetworkReply', 'QNetworkReply.NetworkError'], None]) -> None:
        """Loads the children of this element"""
        if self.children_url is not None:
            api.loadElements(self.children_url, on_finished, on_error)
        else:
            raise RuntimeError(f'Element has no children_url and no custom method to load children')

    def hasThumbnail(self) -> bool:
        return self.thumbnail_url is not None

    @staticmethod
    def _findThumbnailUrl(thumbnail_sizes: List[Dict[str, Any]]) -> Optional[str]:
        """
        Tries to find the most appropriate thumbnail, i.e. the one that is the biggest
        and  also a square

        :param thumbnail_size: The available thumbnail sizes
        :return: The URL to the thumbnail
        """
        best_thumbnail = None
        biggest_size = 0

        for thumbnail in thumbnail_sizes:
            size_str = thumbnail['size']
            re_match = BaseElement.regex_thumbnail_size.match(size_str)
            if re_match is not None:
                width = int(re_match[1])
                height = int(re_match[2])
                if width == height and width > biggest_size:
                    biggest_size = width
                    best_thumbnail = thumbnail['href']

        if best_thumbnail is not None:
            return best_thumbnail
        elif len(thumbnail_sizes) > 0:
            return thumbnail_sizes[0]['href']
        else:
            return None
