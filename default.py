# -*- coding: utf-8 -*-
import os
import json
import urllib
import requests
import datetime
from HTMLParser import HTMLParser

from resources.lib.simpleplugin import Plugin, Addon, ListContext

import xbmc
import xbmcgui


ListContext.cache_to_disk = True
plugin = Plugin()
addon = Addon()
_ = plugin.initialize_gettext()

ICON_ATOZ = os.path.join(addon.path, 'resources', 'media', 'a-z.png')
ICON_BOOKMARK = os.path.join(addon.path, 'resources', 'media', 'bookmark.png')
ICON_CATEGORIES = os.path.join(addon.path, 'resources', 'media', 'categories.png')
ICON_NEW = os.path.join(addon.path, 'resources', 'media', 'new.png')
ICON_REUPLOAD = os.path.join(addon.path, 'resources', 'media', 'reupload.png')
ICON_SEARCH = os.path.join(addon.path, 'resources', 'media', 'search.png')
ICON_NEXT = os.path.join(addon.path, 'resources', 'media', 'next.png')
ICON_WEEK = os.path.join(addon.path, 'resources', 'media', 'week.png')
ICON_MONTH = os.path.join(addon.path, 'resources', 'media', 'month.png')
ICON_YEAR = os.path.join(addon.path, 'resources', 'media', 'year.png')
FANART = os.path.join(addon.path, 'resources', 'media', 'fanart_blurred.png')

base_url = 'http://doku5.com/api.php'


class DialogSelect(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get("listing")
        self.title = kwargs.get("title")
        self.totalitems = 0
        self.result = None

    def autofocus_listitem(self):
        pass

    def close_dialog(self, cancelled=False):
        if cancelled:
            self.result = False
        else:
            self.result = self.list_control.getSelectedItem()
        self.close()

    def onInit(self):
        self.list_control = self.getControl(6)
        self.getControl(3).setVisible(False)
        self.list_control.setEnabled(True)
        self.list_control.setVisible(True)
        self.set_cancel_button()
        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.title)
        self.list_control.addItems(self.listing)
        self.setFocus(self.list_control)
        self.totalitems = len(self.listing)
        self.autofocus_listitem()

    def onAction(self, action):
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close_dialog(True)
        if (action.getId() == 7 or action.getId() == 100) and xbmc.getCondVisibility(
                "Control.HasFocus(3) | Control.HasFocus(6)"):
            self.close_dialog()

    def onClick(self, controlID):
        if controlID == 5:
            self.result = True
            self.close()
        else:
            self.close_dialog(True)

    def set_cancel_button(self):
        try:
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
            self.getControl(7).setVisible(True)
            self.getControl(7).setEnabled(True)
        except Exception:
            pass


def build_url(params):
    params.setdefault('noDYV', 'off' if plugin.get_setting('show_deleted_videos') else 'on')
    url = '{0}?{1}'.format(base_url, urllib.urlencode(params))
    return url


def list_videos(url):
    json_data = requests.get(url).json()
    nonce = json_data['nonce']
    listing = []
    for i in json_data['dokus']:
        title = HTMLParser().unescape(i['title'])
        plot = i['description']
        studio = i['dokuSrc']
        date = '.'.join(reversed(i['date'].split(' ', 1)[0].split('-')))
        votes = i['voting']['voteCountAll']
        rating = float(i['voting']['voteCountInPerc'])/10

        description = u"{0}".format(date)
        if studio and studio != "N/A":
            description += u" | {0}".format(studio)
        description += u" | {0}% ({1} {2})\n{3}".format(rating, votes, "Vote" if votes == 1 else "Votes", plot)

        listing.append({
            'label': title,
            'thumb': i['cover'],
            'fanart': 'http://img.youtube.com/vi/{0}/maxresdefault.jpg'.format(i['youtubeId']),
            'info': {'video': {
                'title': title,
                'plot': description,
                'duration': i['length']*60,
                'aired': date,
                'year': date[-4:],
                'votes': votes,
                'rating': rating,
                'studio': studio,
            }},
            'context_menu': [
                (_("Add to Bookmarks"),
                 'XBMC.RunPlugin({0})'.format(plugin.get_url(action='add_bookmark', youtube_id=i['youtubeId']))),
                (_("Vote up"),
                 'XBMC.RunPlugin({0})'.format(plugin.get_url(action='vote_up', doku_id=i['dokuId'], nonce=nonce))),
                (_("Vote down"),
                 'XBMC.RunPlugin({0})'.format(plugin.get_url(action='vote_down', doku_id=i['dokuId'], nonce=nonce))),
            ],
            'is_playable': True,
            'url': plugin.get_url(action='play', youtube_id=i['youtubeId'], name=title.encode('utf-8')),
        })
    if 'nextpage' in json_data['query']:
        listing.append({
            'label': '[COLOR blue]{0}[/COLOR]'.format(_("Next page")),
            'thumb': ICON_NEXT,
            'url': plugin.get_url(action='index', url=HTMLParser().unescape(json_data['query']['nextpage'])),
            'fanart': FANART,
        })
    return listing


def already_voted(doku_id):
    with plugin.get_storage() as storage:
        if not 'votes' in storage:
            storage['votes'] = []
        votes = storage['votes']
    return doku_id in votes


def vote(type, doku_id, nonce):
    # type 1 == vote up
    # type 2 == vote down
    if already_voted(doku_id):
        xbmcgui.Dialog().notification(_("Error"), _("Documentation already rated"))
    else:
        requests.get(base_url, params={'vote4': True, 'postId': doku_id, 'type': type, 'nonce': nonce, 'callback': 'kody'})
        with plugin.get_storage() as storage:
            storage['votes'].append(doku_id)


@plugin.action()
def root(params):
    return [
        {'label': _("New Documentaries"), 'url': plugin.get_url(action='new'), 'thumb': ICON_NEW, 'fanart': FANART},
        {'label': _("Reuploads"), 'url': plugin.get_url(action='reuploads'), 'thumb': ICON_REUPLOAD, 'fanart': FANART},
        {'label': _("Top of the week"), 'url': plugin.get_url(action='top_week'), 'thumb': ICON_WEEK, 'fanart': FANART},
        {'label': _("Top of the month"), 'url': plugin.get_url(action='top_month'), 'thumb': ICON_MONTH, 'fanart': FANART},
        {'label': _("Top of the year"), 'url': plugin.get_url(action='list_years'), 'thumb': ICON_YEAR, 'fanart': FANART},
        {'label': _("Search"), 'url': plugin.get_url(action='search'), 'thumb': ICON_SEARCH, 'fanart': FANART},
        {'label': _("Categories"), 'url': plugin.get_url(action='list_categories'), 'thumb': ICON_CATEGORIES, 'fanart': FANART},
        {'label': _("A-Z"), 'url': plugin.get_url(action='list_alphabet'), 'thumb': ICON_ATOZ, 'fanart': FANART},
        {'label': _("Bookmarks"), 'url': plugin.get_url(action='bookmarks'), 'thumb': ICON_BOOKMARK, 'fanart': FANART},
    ]


@plugin.action()
def index(params):
    return list_videos(params.url)


@plugin.action()
def new(params):
    url = build_url({'get': 'new-dokus'})
    return list_videos(url)


@plugin.action()
def reuploads(params):
    url = build_url({'get': 'reuploads'})
    return list_videos(url)


@plugin.action()
def top_week(params):
    url = build_url({'top-dokus': 'trend'})
    return list_videos(url)


@plugin.action()
def top_month(params):
    url = build_url({'top-dokus': 'last-month'})
    return list_videos(url)


@plugin.action()
def list_years(params):
    listing = [{
        'label': _("Last year"),
        'url': plugin.get_url(action='last_year'),
    }]
    current_year = datetime.datetime.now().year
    for i in reversed(range(2012, current_year + 1)):
        year = str(i)
        listing.append({
            'label': year,
            'url': plugin.get_url(action='year', year=year),
        })
    return listing


@plugin.action()
def last_year(params):
    url = build_url({'top-dokus': 'last-year'})
    return list_videos(url)


@plugin.action()
def year(params):
    url = build_url({'top-dokus': 'year-{0}'.format(params.year)})
    return list_videos(url)


@plugin.action()
def search(params):
    dialog = xbmcgui.Dialog()
    query = dialog.input(_("Search video"))
    if query:
        url = build_url({'search': query})
        return list_videos(url)


@plugin.action()
def list_categories(params):
    json_data = requests.get('{0}?getCats'.format(base_url)).json()
    listing = []
    for i in json_data:
        listing.append({
            'label': i['name'],
            'url': plugin.get_url(action='index', url=HTMLParser().unescape(i['url'])),
        })
    return listing


@plugin.action()
def list_alphabet(params):
    listing = []
    for i in range(ord('A'), ord('Z') + 1):
        letter = chr(i)
        listing.append({
            'label': letter,
            'url': plugin.get_url(action='letter', letter=letter),
        })
    return listing


@plugin.action()
def letter(params):
    url = build_url({'letter': params.letter})
    return list_videos(url)


@plugin.action()
def bookmarks(params):
    with plugin.get_storage() as storage:
        if not 'bookmarks' in storage:
            storage['bookmarks'] = []
        listing = storage['bookmarks']
    for index, item in enumerate(listing):
        item['context_menu'] = [
            (_("Remove from Bookmarks"),
             'XBMC.RunPlugin({0})'.format(plugin.get_url(action='remove_bookmark', index=index))),
        ]
    return listing


@plugin.action()
def add_bookmark(params):
    label = xbmc.getInfoLabel('ListItem.Label')
    thumb = xbmc.getInfoLabel('ListItem.Thumb')
    year = xbmc.getInfoLabel('ListItem.Year')
    plot = xbmc.getInfoLabel('ListItem.Plot')
    duration = xbmc.getInfoLabel('ListItem.Duration')
    aired = xbmc.getInfoLabel('ListItem.Premiered')
    votes = xbmc.getInfoLabel('ListItem.Votes')
    rating = xbmc.getInfoLabel('ListItem.Rating')
    studio = xbmc.getInfoLabel('ListItem.Studio')

    with plugin.get_storage() as storage:
        if not 'bookmarks' in storage:
            storage['bookmarks'] = []
        if label in [i['label'] for i in storage['bookmarks']]:
            xbmcgui.Dialog().notification(_("Error"), _("Documentation already in Bookmarks"))
        else:
            data = {
                'label': label,
                'thumb': thumb,
                'fanart': 'http://img.youtube.com/vi/{0}/maxresdefault.jpg'.format(params.youtube_id),
                'info': {'video': {
                    'title': label,
                    'plot': plot,
                    'duration': int(duration)*60,
                    'aired': aired,
                    'year': year,
                    'votes': votes,
                    'rating': rating,
                    'studio': studio,
                }},
                'is_playable': True,
                'url': plugin.get_url(action='play', youtube_id=params.youtube_id, name=label),
            }
            storage['bookmarks'].append(data)


@plugin.action()
def remove_bookmark(params):
    with plugin.get_storage() as storage:
        storage['bookmarks'].pop(int(params.index))
    xbmc.executebuiltin('Container.Refresh')


@plugin.action()
def vote_up(params):
    vote(1, params.doku_id, params.nonce)


@plugin.action()
def vote_down(params):
    vote(2, params.doku_id, params.nonce)


def youtube_search(query):
    FIELDS_BASE = ["dateadded", "file", "lastplayed", "plot", "title", "art", "playcount"]
    FIELDS_FILE = FIELDS_BASE + ["streamdetails", "director", "resume", "runtime"]
    FIELDS_FILES = FIELDS_FILE + [
        "plotoutline", "sorttitle", "cast", "votes", "trailer", "year", "country", "studio",
        "genre", "mpaa", "rating", "tagline", "writer", "originaltitle", "imdbnumber", "premiered", "episode",
        "showtitle",
        "firstaired", "watchedepisodes", "duration", "season"]
    data = {
        "jsonrpc": "2.0",
        "method": "Files.GetDirectory",
        "id": 1,
        "params": {
            "properties": FIELDS_FILES,
            "directory": "plugin://plugin.video.youtube/kodion/search/query/?q={0}".format(query)
        }
    }
    json_response = xbmc.executeJSONRPC(json.dumps(data))
    json_object = json.loads(json_response.decode('utf-8'))
    result = []
    if 'result' in json_object:
        for key, value in json_object['result'].iteritems():
            if not key == "limits" and (isinstance(value, list) or isinstance(value, dict)):
                result = value
    result = [i for i in result if not i["filetype"] == "directory"]
    return result


@plugin.action()
def play(params):
    if requests.head("http://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={0}&format=json".format(params.youtube_id)).status_code == 200:
        video_url = "plugin://plugin.video.youtube/play/?video_id={0}".format(params.youtube_id)
    else:
        results = []
        for media in youtube_search(urllib.quote_plus(params.name)):
            label = media["label"]
            label2 = media["plot"]
            image = ""
            if media.get('art'):
                if media['art'].get('thumb'):
                    image = (media['art']['thumb'])
            listitem = xbmcgui.ListItem(label=label, label2=label2, iconImage=image)
            listitem.setProperty("path", media["file"])
            results.append(listitem)
        xbmc.executebuiltin("dialog.Close(busydialog)")
        title = "{0} \"{1}\"".format(_("Select mirror for"), params.name)
        dialog = DialogSelect("DialogSelect.xml", "", listing=results, title=title)
        dialog.doModal()
        result = dialog.result
        if not result:
            return
        video_url = result.getProperty("path")
    return Plugin.resolve_url(play_item={'path': video_url})


if __name__ == '__main__':
    plugin.run()
