#!/usr/bin/env python
# -*- coding: utf-8 -*-
import kivy
from kivy.app import App
from kivy.logger import LOG_LEVELS, Logger
from kivy.utils import platform
from kivymd.theming import ThemeManager
from PIL import Image as PILImage
from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from pywallet.controller import Controller
from version import __version__


try:
    
    PILImage.frombytes
    PILImage.Image.tobytes
except AttributeError:
    PILImage.frombytes = PILImage.frombuffer
    PILImage.Image.tobytes = PILImage.Image.tostring

kivy.require('1.10.0')


class DebugRavenClient(object):
  
    def captureException(self):
        raise


class PyWalletApp(App):
    theme_cls = ThemeManager()

    def build(self):
        self.icon = "docs/images/icon.png"
        return Controller()

    @property
    def controller(self):
        return self.root


def configure_sentry(in_debug=False):
    
    key = ''
   
    secret = ''
    project_id = ''
    dsn = 'https://{key}:{secret}@sentry.io/{project_id}'.format(
        key=key, secret=secret, project_id=project_id)
    if in_debug:
        client = DebugRavenClient()
    else:
        client = Client(dsn=dsn, release=__version__)
        if platform == 'android':
            from jnius import autoclass
            Build = autoclass("android.os.Build")
            VERSION = autoclass('android.os.Build$VERSION')
            android_os_build = {
                'model': Build.MODEL,
                'brand': Build.BRAND,
                'device': Build.DEVICE,
                'manufacturer': Build.MANUFACTURER,
                'version_release': VERSION.RELEASE,
            }
            client.user_context({'android_os_build': android_os_build})
        handler = SentryHandler(client)
        handler.setLevel(LOG_LEVELS.get('error'))
        setup_logging(handler)
    return client


if __name__ == '__main__':
    in_debug = platform != "android"
    client = configure_sentry(in_debug)
    try:
        PyWalletApp().run()
    except Exception:
        if type(client) == Client:
            Logger.info()
        client.captureException()
