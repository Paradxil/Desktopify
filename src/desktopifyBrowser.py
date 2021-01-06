#Based on an example of embedding CEF Python browser using wxPython library.
#Only works on Windows

import wx
from cefpython3 import cefpython as cef
import platform
import sys
import os
import configparser

# Configuration
WIDTH = 900
HEIGHT = 640

# Globals
g_count_windows = 0

#Used to get the current directory
def getDir():
    dirname = None
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        dirname = sys._MEIPASS
    else:
        dirname = os.path.dirname(os.path.abspath(__file__))
    return dirname

def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error

    #Setup the cache
    dirname = getDir()
    filename = os.path.join(dirname, "../", "cache")
    settings = {"cache_path": filename}

    #Enable high dpi support
    cef.DpiAware.EnableHighDpiSupport()

    #Initialize CEF
    cef.Initialize(settings=settings)

    #Start app
    app = CefApp(False)
    app.MainLoop()

    # Must destroy before calling Shutdown
    del app 
    cef.Shutdown()


def check_versions():
    print("[wxpython.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[wxpython.py] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]))
    print("[wxpython.py] wxPython {ver}".format(ver=wx.version()))
    # CEF Python version requirement
    assert cef.__version__ >= "66.0", "CEF Python v66.0+ required to run this"


def scale_window_size_for_high_dpi(width, height):
    """Scale window size for high DPI devices. This func can be
    called on all operating systems, but scales only for Windows.
    If scaled value is bigger than the work area on the display
    then it will be reduced."""
    (_, _, max_width, max_height) = wx.GetClientDisplayRect().Get()
    # noinspection PyUnresolvedReferences
    (width, height) = cef.DpiAware.Scale((width, height))
    if width > max_width:
        width = max_width
    if height > max_height:
        height = max_height
    return width, height


class MainFrame(wx.Frame):

    def __init__(self):
        self.browser = None

        #Get data from config file
        config = configparser.ConfigParser()

        configFile = None
        if len(sys.argv) > 1:
            configFile = os.path.join(getDir(), sys.argv[1])
            config.read(configFile)

        ssb_url = config.get("settings", "url", fallback="https://google.com")
        title = config.get("settings", "name", fallback="SSB Title")
        icon = config.get("settings", "icon", fallback=None)

        global g_count_windows
        g_count_windows += 1

        size = scale_window_size_for_high_dpi(WIDTH, HEIGHT)

        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, title=title, size=size)

        self.setup_icon(icon)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Set wx.WANTS_CHARS style for the keyboard to work.
        # This style also needs to be set for all parent controls.
        self.browser_panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.browser_panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.browser_panel.Bind(wx.EVT_SIZE, self.OnSize)

        self.embed_browser(ssb_url)
        self.Maximize()
        self.Show()

    def setup_icon(self, icon):
        if icon != None:
            self.SetIcon(wx.Icon(icon))

    def embed_browser(self, ssburl):
        window_info = cef.WindowInfo()
        (width, height) = self.browser_panel.GetClientSize().Get()
        assert self.browser_panel.GetHandle(), "Window handle not available"
        window_info.SetAsChild(self.browser_panel.GetHandle(), [0, 0, width, height])
        self.browser = cef.CreateBrowserSync(window_info, url=ssburl)

    def OnSetFocus(self, _):
        if not self.browser:
            return
        
        cef.WindowUtils.OnSetFocus(self.browser_panel.GetHandle(), 0, 0, 0)
        self.browser.SetFocus(True)

    def OnSize(self, _):
        if not self.browser:
            return

        cef.WindowUtils.OnSize(self.browser_panel.GetHandle(), 0, 0, 0)
        self.browser.NotifyMoveOrResizeStarted()

    def OnClose(self, event):
        print("[wxpython.py] OnClose called")
        if not self.browser:
            # May already be closing, may be called multiple times on Mac
            return
        
        # Calling browser.CloseBrowser() and/or self.Destroy()
        # in OnClose may cause app crash on some paltforms in
        # some use cases, details in Issue #107.
        self.browser.ParentWindowWillClose()
        event.Skip()
        self.clear_browser_references()

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.browser = None


class CefApp(wx.App):

    def __init__(self, redirect):
        self.timer = None
        self.timer_id = 1
        self.is_initialized = False
        super(CefApp, self).__init__(redirect=redirect)

    def OnInit(self):
        self.initialize()
        return True

    def initialize(self):
        if self.is_initialized:
            return
        self.is_initialized = True
        self.create_timer()
        frame = MainFrame()
        self.SetTopWindow(frame)
        frame.Show()

    def create_timer(self):
        # See also "Making a render loop":
        # http://wiki.wxwidgets.org/Making_a_render_loop
        # Another way would be to use EVT_IDLE in MainFrame.
        self.timer = wx.Timer(self, self.timer_id)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(5)  # 10ms timer

    def on_timer(self, _):
        cef.MessageLoopWork()

    def OnExit(self):
        self.timer.Stop()
        return 0


if __name__ == '__main__':
    main()
