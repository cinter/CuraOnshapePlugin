# Copyright (c) 2025 Erwan MATHIEU

import QtQuick 2.15
import QtQuick.Window 2.2
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.15

import Cura 1.5 as Cura
import UM 1.5 as UM


Item
{
    id: root
    implicitHeight: filter.implicitHeight + 2 * UM.Theme.getSize("default_margin").width

    UM.I18nCatalog{id: catalog; name:"onshape"}

    Cura.TextField
    {
        id: filter
        implicitWidth: UM.Theme.getSize("print_setup_big_item").width
        implicitHeight: UM.Theme.getSize("print_setup_big_item").height
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: UM.Theme.getSize("default_margin").width
        leftPadding: searchIcon.width + UM.Theme.getSize("default_margin").width * 2
        placeholderText: catalog.i18nc("@textfield:placeholder", "Search")
        font: UM.Theme.getFont("default_italic")

        UM.ColorImage
        {
            id: searchIcon

            anchors
            {
                verticalCenter: parent.verticalCenter
                left: parent.left
                leftMargin: UM.Theme.getSize("default_margin").width
            }
            source: UM.Theme.getIcon("Magnifier")
            height: UM.Theme.getSize("small_button_icon").height
            width: height
            color: UM.Theme.getColor("text")
        }

        Keys.onEscapePressed: filter.text = ""

        onAccepted: root.doSearch()
    }

    UM.SimpleButton
    {
        id: clearFilterButton
        iconSource: UM.Theme.getIcon("Cancel")
        visible: filter.text !== ""

        height: Math.round(filter.height * 0.4)
        width: height

        anchors.verticalCenter: filter.verticalCenter
        anchors.right: filter.right
        anchors.rightMargin: UM.Theme.getSize("default_margin").width

        color: UM.Theme.getColor("setting_control_button")
        hoverColor: UM.Theme.getColor("setting_control_button_hover")

        onClicked:
        {
            filter.text = ""
            filter.forceActiveFocus()
        }
    }

    function doSearch()
    {
        console.debug("Search " + filter.text + " " + documentsListStack.currentItem.documentsModel)

        var search_model = documentsListStack.currentItem.documentsModel.searchModel(filter.text)
        console.debug(search_model)
        documentsListStack.push("DocumentsView.qml", {"documentsModel": search_model})
    }
}
