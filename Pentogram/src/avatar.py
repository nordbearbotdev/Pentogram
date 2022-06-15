import abc
import asyncio
import functools
import logging
import typing
import unicodedata

import aioxmpp

import jclib.client
import jclib.identity
import jclib.storage
import jclib.utils

import pentogram.utils

from . import Qt


BASE_SIZE = 48

AVATAR_DUMMY_PATH = Qt.QPainterPath()
AVATAR_DUMMY_PATH.moveTo(2.4732999999999947, 0.006839999999982638)
AVATAR_DUMMY_PATH.cubicTo(2.3338799999999935, 0.00283999999999196,
                          2.233701999999994, 0.04673999999997136,
                          2.177060999999995, 0.1424599999999714)
AVATAR_DUMMY_PATH.cubicTo(0.6549399999999963, 2.7271699999999726,
                          0.9932499999999891, 9.385779999999983,
                          1.1465279999999893, 15.88594999999998)
AVATAR_DUMMY_PATH.cubicTo(1.1697879999999827, 23.37239999999997,
                          1.0994979999999828, 29.341819999999984,
                          1.1149579999999872, 36.18838999999997)
AVATAR_DUMMY_PATH.cubicTo(1.1149579999999872, 42.72858999999997,
                          6.906902999999986, 47.99357999999998,
                          13.447076999999993, 47.99357999999998)
AVATAR_DUMMY_PATH.lineTo(34.58242899999999, 47.99357999999998)
AVATAR_DUMMY_PATH.cubicTo(41.122601999999986, 47.99357999999998,
                          46.885001999999986, 42.63612999999998,
                          46.885001999999986, 36.09595999999999)
AVATAR_DUMMY_PATH.cubicTo(46.88100199999998, 28.669249999999977,
                          46.79650199999999, 20.914739999999995,
                          46.885001999999986, 15.854379999999992)
AVATAR_DUMMY_PATH.cubicTo(47.038291999999984, 9.354209999999995,
                          47.34507199999999, 2.727170000000001,
                          45.82295199999999, 0.1424599999999998)
AVATAR_DUMMY_PATH.cubicTo(45.36948199999999, -0.6277300000000139,
                          42.12955199999999, 1.9487900000000025,
                          38.332261999999986, 5.934439999999995)
AVATAR_DUMMY_PATH.cubicTo(35.55393199999999, 8.850580000000008,
                          33.74174799999999, 8.788520000000005,
                          31.673985999999985, 8.788520000000005)
AVATAR_DUMMY_PATH.lineTo(16.325825999999992, 8.788520000000005)
AVATAR_DUMMY_PATH.cubicTo(14.634642999999997, 8.788520000000005,
                          12.423642999999998, 8.690519999999992,
                          9.667546999999999, 5.934439999999995)
AVATAR_DUMMY_PATH.cubicTo(6.261529999999993, 2.528419999999983,
                          3.4491940000000056, 0.038639999999986685,
                          2.4733719999999977, 0.006959999999992306)
AVATAR_DUMMY_PATH.lineTo(2.4732999999999947, 0.006839999999982638)


def _connect(tokens, signal, cb):
    tokens.append((signal, signal.connect(cb)))


def _disconnect_all(tokens):
    for signal, token in tokens:
        signal.disconnect(token)
    tokens.clear()


def first_grapheme(s):
    """
    Return the unicode codepoints resembling the first grapheme in `s`.
    """
    boundary_finder = Qt.QTextBoundaryFinder(
        Qt.QTextBoundaryFinder.Grapheme,
        s,
    )
    boundary = boundary_finder.toNextBoundary()
    return s[:boundary]


def render_dummy_avatar_base(painter: Qt.QPainter,
                             colour: Qt.QColor,
                             size: float):
    pen_colour = Qt.QColor(colour)
    pen_colour.setAlpha(127)
    painter.setPen(Qt.QPen(pen_colour))
    painter.setBrush(colour)
    painter.drawRect(Qt.QRectF(0, 0, size, size))

    white_transparent = Qt.QColor(Qt.Qt.white)
    white_transparent.setAlpha(63)
    painter.setBrush(Qt.QBrush(white_transparent))
    painter.setPen(Qt.QPen(Qt.Qt.white, 2))

    painter.translate(2, 2)
    painter.scale(44/48, 44/48)
    painter.fillPath(AVATAR_DUMMY_PATH, white_transparent)
    painter.resetTransform()


def render_dummy_avatar_grapheme(painter: Qt.QPainter,
                                 grapheme: str,
                                 base_font: Qt.QFont,
                                 size: float):
    PADDING_TOP = 4
    PADDING = 2

    painter.setPen(Qt.QPen(Qt.QColor(255, 255, 255, 255)))
    painter.setBrush(Qt.QBrush())

    font = Qt.QFont(base_font)
    font.setPixelSize(size * 0.85 - PADDING - PADDING_TOP)
    font.setWeight(Qt.QFont.Thin)

    painter.setFont(font)
    painter.drawText(
        Qt.QRectF(
            PADDING, PADDING_TOP,
            size - PADDING * 2,
            size - PADDING - PADDING_TOP,
        ),
        Qt.Qt.AlignHCenter | Qt.Qt.AlignVCenter | Qt.Qt.TextSingleLine,
        grapheme,
    )


def render_dummy_avatar(font: Qt.QFont,
                        name: str,
                        size: float,
                        colour_text: str=None):
    colour = jabbercat.utils.text_to_qtcolor(
        jclib.utils.normalise_text_for_hash(colour_text or name)
    )
    grapheme = first_grapheme(name)
    picture = Qt.QPicture()
    painter = Qt.QPainter(picture)
    painter.setRenderHint(Qt.QPainter.Antialiasing, True)
    render_dummy_avatar_base(painter, colour, size)
    render_dummy_avatar_grapheme(painter, grapheme, font, size)
    return picture


def render_avatar_image(image: Qt.QImage, size: float):
    if image.isNull():
        return None

    aspect_ratio = image.width() / image.height()
    if aspect_ratio > 1:
        width = size
        height = size / aspect_ratio
    else:
        width = size * aspect_ratio
        height = size

    x0 = (size - width) / 2
    y0 = (size - height) / 2

    picture = Qt.QPicture()
    painter = Qt.QPainter(picture)
    painter.drawImage(
        Qt.QRectF(x0, y0, width, height),
        image,
    )
    painter.end()
    return picture


class XMPPAvatarProvider:
    """
    .. signal:: on_avatar_changed(address)
        Emits when the avatar of a peer has changed.
        The image needs to be fetched separately and explicitly.
    """

    on_avatar_changed = aioxmpp.callbacks.Signal()

    def __init__(self, account: jclib.identity.Account):
        super().__init__()
        self.__tokens = []
        self._account = account
        self._avatar_svc = None
        self._cache = aioxmpp.cache.LRUDict()
        self._cache.maxsize = 1024
        self.logger = logging.getLogger(".".join([
            __name__, type(self).__qualname__, str(account.jid)
        ]))

    def __connect(self, signal, handler):
        _connect(self.__tokens, signal, handler)

    def __disconnect_all(self):
        _disconnect_all(self.__tokens)

    def prepare_client(self, client: aioxmpp.Client):
        svc = client.summon(aioxmpp.AvatarService)
        self.__connect(svc.on_metadata_changed, self._on_metadata_changed)
        self._avatar_svc = svc

    def shutdown_client(self, client: aioxmpp.Client):
        self.__disconnect_all()
        self._avatar_svc = None

    def _on_metadata_changed(self, jid, metadata):
        self.on_avatar_changed(jid)

    @asyncio.coroutine
    def _get_image(self, address: aioxmpp.JID) -> typing.Optional[Qt.QImage]:
        try:
            metadata = yield from self._avatar_svc.get_avatar_metadata(address)
        except (aioxmpp.errors.XMPPError,
                aioxmpp.errors.ErroneousStanza) as exc:
            self.logger.warning("cannot fetch avatar from %s: %s",
                                address, exc)
            return

        for descriptor in metadata:
            try:
                data = yield from descriptor.get_image_bytes()
            except (NotImplementedError, RuntimeError,
                    aioxmpp.errors.XMPPCancelError):
                continue
            img = Qt.QImage.fromData(data)
            if not img.isNull():
                return img

    @asyncio.coroutine
    def fetch_avatar(self, address: aioxmpp.JID) \
            -> typing.Optional[Qt.QPicture]:
        img = yield from self._get_image(address)
        if img is None:
            self._cache[address] = None
            return None

        picture = render_avatar_image(img, BASE_SIZE)
        self._cache[address] = picture
        return picture

    def get_avatar(self, address: aioxmpp.JID) \
            -> typing.Optional[Qt.QPicture]:
        return self._cache[address]


class RosterNameAvatarProvider:
    """
    Generate avatar images based on roster names or JIDs.
    """

    on_avatar_changed = aioxmpp.callbacks.Signal()

    def __init__(self):
        super().__init__()
        self.__tokens = []
        self._roster_svc = None

    def __connect(self, signal, handler):
        _connect(self.__tokens, signal, handler)

    def __disconnect_all(self):
        _disconnect_all(self.__tokens)

    def prepare_client(self, client: aioxmpp.Client):
        self._roster_svc = client.summon(aioxmpp.RosterClient)
        self.__connect(self._roster_svc.on_entry_added, self._on_entry_updated)
        self.__connect(self._roster_svc.on_entry_name_changed,
                       self._on_entry_updated)
        self.__connect(self._roster_svc.on_entry_removed,
                       self._on_entry_updated)

    def shutdown_client(self, client: aioxmpp.Client):
        self.__disconnect_all()
        self._roster_svc = None

    def get_avatar(self, address: aioxmpp.JID,
                   font: Qt.QFont) \
            -> typing.Optional[Qt.QPicture]:
        if self._roster_svc is None:
            return
        try:
            name = self._roster_svc.items[address].name
        except KeyError:
            return
        if name is None:
            return
        return render_dummy_avatar(font, name, BASE_SIZE,
                                   str(address))

    def _on_entry_updated(self, item):
        self.on_avatar_changed(item.jid)


class AvatarManager:
    on_avatar_changed = aioxmpp.callbacks.Signal()

    def __init__(self,
                 client: jclib.client.Client,
                 writeman: jclib.storage.WriteManager):
        super().__init__()
        self._queue = asyncio.Queue()
        self._enqueued = set()
        self._workers = [
            asyncio.ensure_future(self._worker())
            for i in range(10)
        ]
        self.logger = logging.getLogger(
            ".".join([__name__, type(self).__qualname__])
        )

        self.__accountmap = {}

        client.on_client_prepare.connect(self._prepare_client)
        client.on_client_stopped.connect(self._shutdown_client)

    def close(self):
        for worker in self._workers:
            worker.cancel()

    @asyncio.coroutine
    def _worker(self):
        while True:
            task = yield from self._queue.get()
            try:
                yield from task
            except Exception as exc:
                self.logger.warning("background job failed", exc_info=True)

    def get_avatar_font(self):
        return Qt.QFontDatabase.systemFont(
            Qt.QFontDatabase.GeneralFont
        )

    @asyncio.coroutine
    def _fetch_avatar_and_emit_signal(self, fetch_func, account, address):
        self.logger.debug("fetching avatar for %s", address)
        try:
            yield from asyncio.wait_for(fetch_func(address), timeout=10)
        except asyncio.TimeoutError:
            self.logger.info("failed to fetch avatar for %s (timeout)",
                             address)
            return
        finally:
            self._enqueued.discard((account, address))
        self.logger.debug("avatar for %s fetched", address)
        self.on_avatar_changed(account, address)

    def _fetch_in_background(self, account, provider, address):
        key = account, address
        if key in self._enqueued:
            return
        self._enqueued.add(key)
        self._queue.put_nowait(
            self._fetch_avatar_and_emit_signal(
                provider.fetch_avatar,
                account,
                address,
            )
        )

    def get_avatar(self,
                   account: jclib.identity.Account,
                   address: aioxmpp.JID,
                   name_surrogate: typing.Optional[str]=None) -> Qt.QPicture:
        try:
            _, generator, xmpp_avatar = self.__accountmap[account]
        except KeyError:
            font = self.get_avatar_font()
        else:
            try:
                result = xmpp_avatar.get_avatar(address)
            except KeyError:
                self._fetch_in_background(account, xmpp_avatar, address)
                result = None

            if result is not None:
                return result

            font = self.get_avatar_font()
            result = generator.get_avatar(address, font)
            if result is not None:
                return result

        return render_dummy_avatar(font,
                                   name_surrogate or str(address),
                                   BASE_SIZE)

    def _on_xmpp_avatar_changed(self,
                                account: jclib.identity.Account,
                                service: XMPPAvatarProvider,
                                address: aioxmpp.JID):
        try:
            service.get_avatar(address)
        except KeyError:
            return

        self._fetch_in_background(account, service, address)

    def _on_backend_avatar_changed(self,
                                   account: jclib.identity.Account,
                                   address: aioxmpp.JID):
        self.on_avatar_changed(account, address)

    def _prepare_client(self,
                        account: jclib.identity.Account,
                        client: jclib.client.Client):
        xmpp_avatar = XMPPAvatarProvider(account)
        xmpp_avatar.prepare_client(client)

        generator = RosterNameAvatarProvider()
        generator.prepare_client(client)

        tokens = []
        _connect(tokens, generator.on_avatar_changed,
                 functools.partial(self._on_backend_avatar_changed, account))
        _connect(tokens, xmpp_avatar.on_avatar_changed,
                 functools.partial(self._on_xmpp_avatar_changed,
                                   account, xmpp_avatar))

        self.__accountmap[account] = tokens, generator, xmpp_avatar

    def _shutdown_client(self,
                         account: jclib.identity.Account,
                         client: jclib.client.Client):
        tokens, *_ = self.__accountmap.pop(account)
        _disconnect_all(tokens)
