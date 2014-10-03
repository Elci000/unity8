# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Unity Autopilot Test Suite
# Copyright (C) 2012, 2013, 2014 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import ubuntuuitoolkit

from unity8.shell import emulators

from autopilot import logging as autopilot_logging
from autopilot.introspection import dbus
from ubuntuuitoolkit import emulators as toolkit_emulators


logger = logging.getLogger(__name__)


class DashApp(object):

    """Autopilot helper for the Dash app."""

    def __init__(self, app_proxy):
        self.app_proxy = app_proxy
        self.main_view = self.app_proxy.select_single(
            toolkit_emulators.MainView)
        self.dash = self.main_view.select_single(Dash)


class Dash(emulators.UnityEmulatorBase):
    """An emulator that understands the Dash."""

    def __init__(self, *args):
        super(Dash, self).__init__(*args)
        self.dash_content_list = self.wait_select_single(
            'QQuickListView', objectName='dashContentList')

    def get_applications_grid(self):
        get_grid = self.get_scope('clickscope').wait_select_single(
            'CardGrid', objectName='local')
        return get_grid

    def get_application_icon(self, text):
        """Returns a 'Tile' icon that has the text 'text' from the application
        grid.

        :param text: String containing the text of the icon to search for.

        """
        app_grid = self.get_applications_grid()
        resp_grid = app_grid.wait_select_single('ResponsiveGridView')
        return resp_grid.select_single('Tile', text=text)

    def get_scope(self, scope_name='clickscope'):
        return self.dash_content_list.wait_select_single(
            'QQuickLoader', scopeId=scope_name)

    @autopilot_logging.log_action(logger.info)
    def open_scope(self, scope_id):
        """Open a dash scope.

        :parameter scope_id: The id of the scope.
        :return: The scope.

        """
        scope_loader = self._get_scope_loader(scope_id)
        if scope_loader.isCurrent:
            logger.info('The scope is already open.')
            return self._get_scope_from_loader(scope_loader)
        else:
            return self._open_scope_scrolling(scope_loader)

    def _get_scope_loader(self, scope_id):
        try:
            return self.dash_content_list.select_single(
                'QQuickLoader', scopeId=scope_id)
        except dbus.StateNotFoundError:
            raise emulators.UnityEmulatorException(
                'No scope found with id {0}'.format(scope_id))

    def _get_scope_from_loader(self, loader):
        return loader.get_children()[0]

    def _open_scope_scrolling(self, scope_loader):
        scroll = self._get_scroll_direction(scope_loader)

        while not scope_loader.isCurrent:
            scroll()
            self.dash_content_list.moving.wait_for(False)

        scope = self._get_scope_from_loader(scope_loader)
        scope.isCurrent.wait_for(True)
        return scope

    def _get_scroll_direction(self, scope_loader):
        current_scope_loader = self.dash_content_list.select_single(
            'QQuickLoader', isCurrent=True)
        if scope_loader.globalRect.x < current_scope_loader.globalRect.x:
            return self._scroll_to_left_scope
        elif scope_loader.globalRect.x > current_scope_loader.globalRect.x:
            return self._scroll_to_right_scope
        else:
            raise emulators.UnityEmulatorException('The scope is already open')

    @autopilot_logging.log_action(logger.info)
    def _scroll_to_left_scope(self):
        original_index = self.dash_content_list.currentIndex
        dash_content = self.select_single(objectName="dashContent")
        x, y, width, height = dash_content.globalRect
        start_x = x + width / 3
        stop_x = x + width / 3 * 2
        start_y = stop_y = y + 1
        self.pointing_device.drag(start_x, start_y, stop_x, stop_y)
        self.dash_content_list.currentIndex.wait_for(original_index - 1)

    @autopilot_logging.log_action(logger.info)
    def _scroll_to_right_scope(self):
        original_index = self.dash_content_list.currentIndex
        dash_content = self.select_single(objectName="dashContent")
        x, y, width, height = dash_content.globalRect
        start_x = x + width / 3 * 2
        stop_x = x + width / 3
        start_y = stop_y = y + 1
        self.pointing_device.drag(start_x, start_y, stop_x, stop_y)
        self.dash_content_list.currentIndex.wait_for(original_index + 1)

    def enter_search_query(self, query):
        current_header = self._get_current_page_header()
        search_button = current_header.select_single(objectName="search_header_button")
        self.pointing_device.move(search_button.globalRect.x + search_button.width / 2,
                                  search_button.globalRect.y + search_button.height / 2)
        self.pointing_device.click()
        headerContainer = current_header.select_single(
            objectName="headerContainer")
        headerContainer.contentY.wait_for(0)
        search_text_field = self._get_search_text_field()
        search_text_field.write(query)
        self.select_single(objectName="processingIndicator").visible.wait_for(False)

    def _get_search_text_field(self):
        page_header = self._get_current_page_header()
        return page_header.select_single(objectName='searchTextField')

    def _get_current_page_header(self):
        dashContentList = self.select_single(objectName="dashContentList")
        all_headers = dashContentList.select_many("QQuickLoader")
        for i in all_headers:
            if i.isCurrent:
                return i.select_single(objectName="scopePageHeader")
        return None


class ListViewWithPageHeader(ubuntuuitoolkit.QQuickFlickable):
    pass


class GenericScopeView(emulators.UnityEmulatorBase):
    """Autopilot emulator for generic scopes."""

    @autopilot_logging.log_action(logger.info)
    def open_preview(self, category, app_name):
        """Open the preview of an application.

        :parameter category: The name of the category where the application is.
        :parameter app_name: The name of the application.
        :return: The opened preview.

        """
        # FIXME some categories need a long press in order to see the preview.
        # Some categories do not show previews, like recent apps.
        # --elopio - 2014-1-14
        self.click_scope_item(category, app_name)
        preview_list = self.wait_select_single(
            'QQuickLoader', objectName='subPageLoader')
        preview_list.subPageShown.wait_for(True)
        preview_list.x.wait_for(0)
        return preview_list.select_single(
            Preview, objectName='preview{}'.format(preview_list.currentIndex))

    @autopilot_logging.log_action(logger.debug)
    def click_scope_item(self, category, title):
        """Click an item from the scope.

        :parameter category: The name of the category where the item is.
        :parameter title: The title of the item.

        """
        category_element = self._get_category_element(category)
        icon = category_element.select_single('AbstractButton', title=title)
        self.pointing_device.click_object(icon)

    def _get_category_element(self, category):
        try:
            return self.wait_select_single(
                'Base', objectName='dashCategory{}'.format(category))
        except dbus.StateNotFoundError:
            raise emulators.UnityEmulatorException(
                'No category found with name {}'.format(category))

    def get_applications(self, category):
        """Return the list of applications on a category.

        :parameter category: The name of the category.

        """
        category_element = self._get_category_element(category)
        see_all = category_element.select_single(objectName='seeAll')
        application_cards = category_element.select_many('AbstractButton')

        application_cards = sorted(
            (card for card in application_cards
             if card.globalRect.y < see_all.globalRect.y),
            key=lambda card: (card.globalRect.y, card.globalRect.x))

        result = []
        for card in application_cards:
            if card.objectName not in ('cardToolCard', 'seeAll'):
                result.append(card.title)
        return result


class Preview(emulators.UnityEmulatorBase):
    """Autopilot custom proxy object for generic previews."""
