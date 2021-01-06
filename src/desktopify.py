#The GUI for desktopifying websites.
#Only works on windows

import configparser
import os
import sys
import threading
from subprocess import Popen

import favicon
import pythoncom
import requests
import winshell
import wx
from win32com.shell import shell, shellcon
import zipfile

from PIL import Image

#Text constants
text = {
"title": "Desktopify",
"submit": "Create App"
}

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

def getExePath():
    return os.path.join(getExeDir(), 'DesktopifyBrowser.exe')

def getAPPDATADir():
    return os.path.join(os.getenv('LOCALAPPDATA'), 'Desktopify')

def getExeDir():
    return os.path.join(os.getenv('LOCALAPPDATA'), 'Desktopify', 'DesktopifyBrowser')

def getAppsDir():
    return os.path.join(os.getenv('LOCALAPPDATA'), 'Desktopify', 'apps')

def getAppsPath():
    return getAppsDir()

def getAppDir(appName):
    appName = appName.strip().replace(' ', '_')
    return os.path.join(getAppsDir(), appName)

class SSBCreator(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Desktopify', size=(800,600))
        self.appManagerPanel = AppManager(self)
        self.createAppPanel = CreateAppPanel(self)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.appManagerPanel, 1, wx.EXPAND)
        self.sizer.Add(self.createAppPanel, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.createAppPanel.Hide()

        self.SetIcon(wx.Icon(os.path.join(getDir(), 'icon.ico')))

        self.Layout()
        self.Show()
    
    def switchPanels(self, event):
        if not self.createAppPanel.IsShown():
            self.appManagerPanel.Hide()
            self.createAppPanel.Show()
        else:
            self.createAppPanel.Hide()
            self.appManagerPanel.populateList()
            self.appManagerPanel.Show()
        self.Layout()

class CreateAppPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        my_sizer = wx.BoxSizer(wx.VERTICAL)

        #Add title
        titleFont = wx.Font(25, wx.DEFAULT, wx.NORMAL, wx.DEFAULT)

        self.title = wx.StaticText(self, label=text["title"], style=wx.ALIGN_LEFT)
        self.title.SetFont(titleFont)
        my_sizer.Add(self.title, 0, wx.TOP | wx.LEFT | wx.EXPAND, 8)

        #Add return to manager button
        self.backButton = wx.Button(self, label="Back")
        self.backButton.Bind(wx.EVT_BUTTON, parent.switchPanels)
        my_sizer.Add(self.backButton, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, 8)

        #Add Name Box
        self.appName_Input = wx.TextCtrl(self)
        self.appName_Label = wx.StaticText(self, label="App Name")
        my_sizer.Add(self.appName_Label, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        my_sizer.Add(self.appName_Input, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)
        self.appName_Input.Bind(wx.EVT_TEXT, self.validateText)
        self.appName_Input.SetMaxLength(32)

        #Add URL box
        self.url_Input = wx.TextCtrl(self)
        self.url_Label = wx.StaticText(self, label="App URL")
        my_sizer.Add(self.url_Label, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        my_sizer.Add(self.url_Input, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        #Add Shortcut options
        self.createStartShortcut = wx.CheckBox(self, label = 'Create shortcut on start menu')
        self.createStartShortcut.SetValue(True)
        my_sizer.Add(self.createStartShortcut, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        self.createDesktopShortcut = wx.CheckBox(self, label = 'Create shortcut on desktop')
        my_sizer.Add(self.createDesktopShortcut, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        #Add submit button
        self.submitButton = wx.Button(self, label=text["submit"])
        self.submitButton.Bind(wx.EVT_BUTTON, self.onSubmit)
        my_sizer.Add(self.submitButton, 0, wx.ALL, 8)

        #Add message output
        self.messageBox = wx.StaticText(self)
        self.message = ""
        my_sizer.Add(self.messageBox, 1, wx.ALL | wx.EXPAND, 8)

        #Add progress bar
        self.progressBar = wx.Gauge(self, range=100, style = wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.progressBar.SetValue(0)
        my_sizer.AddStretchSpacer(2)
        my_sizer.Add(self.progressBar, 0, wx.ALL | wx.CENTER | wx.EXPAND, 8)

        self.SetSizer(my_sizer)
    
    def onSubmit(self, event):
        #Get values from form and sanitize
        url = self.sanitizeUrl(self.url_Input.GetValue())
        name = self.sanitizeText(self.appName_Input.GetValue())
        installDir = getAppsDir()

        if not os.path.exists(installDir):
            os.makedirs(installDir, exist_ok=True)

        self.checkName(name)
        self.checkUrl(url)

        #Make sure values are not null and valid
        if self.checkUrl(url) and self.checkName(name):
            self.clearMessage()
            self.submitButton.Disable()
            self.progressBar.Pulse()

            #Start thread to download icon file, write config file, and create shortcuts
            thread = threading.Thread(target=self.desktopifyWebsite, args=(url, name, installDir))
            thread.start()
    
    def desktopifyWebsite(self, url, name, installDir):
        try:
            appDir = getAppDir(name)
            if os.path.exists(appDir) and os.path.exists(os.path.join(appDir, 'config.ini')):
                self.addMessage("Error creating app. App already exists.")
                self.onFinished(False)
                return
            else:
                os.makedirs(appDir, exist_ok=True)
            #Download the websites favicon to use as an icon
            iconFile = self.downloadIcon(url, appDir)
            
            #Update progress bar between tasks
            self.onUpdate(33)

            #Write a config file for this website with web app specific info
            configFile = self.createConfigFile(url, name, iconFile, appDir)
            self.onUpdate(66)

            exeFile = getExePath()
            
            self.createShortcuts(iconFile, exeFile, configFile, name=name, desktop=self.createDesktopShortcut.GetValue(), start=self.createStartShortcut.GetValue())
            self.onUpdate(100)
            self.onFinished()
        except Exception as e:
            self.progressBar.SetValue(0)
            self.addMessage("Error creating app. Make sure you are connected to the internet and the URL is valid.")
            print(str(e))

    def onUpdate(self, percent):
        self.progressBar.SetValue(percent)

    def onFinished(self, success=True):
        self.progressBar.SetValue(100)
        self.submitButton.Enable()
        if success:
            self.addMessage("App created successfully!")
    
    def createShortcuts(self, pathToIcon, pathToExec, pathToConfig, name, desktop, start):
        #Init pythoncom
        pythoncom.CoInitialize()

        #Create a shortcut
        shortcut = pythoncom.CoCreateInstance(
          shell.CLSID_ShellLink,
          None,
          pythoncom.CLSCTX_INPROC_SERVER,
          shell.IID_IShellLink
        )
        
        #Get the desktop and start folders
        desktopDir = winshell.desktop()
        startmenuDir = winshell.start_menu()

        #Set the exe path (to the desktopifyBrowser.exe)
        shortcut.SetPath(pathToExec)

        #Set the icon path for the downloaded favicon
        shortcut.SetIconLocation(pathToIcon,0)

        #Set the config file as an argument

        shortcut.SetArguments(pathToConfig)

        #Save the shortcut
        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        
        if desktop and desktopDir:
            persist_file.Save(os.path.join(desktopDir, name+".lnk"), 0)
        
        if start and startmenuDir:
            persist_file.Save(os.path.join(startmenuDir, name+".lnk"), 0)

    def createConfigFile(self, url, name, iconFile, appDir):
        config = configparser.ConfigParser()

        #Write the url, name and icon so that the destopifyBrowser 
        #will load app sepcific data correctly.
        config["settings"] = {
            'url':url, 
            'name':name, 
            'icon':iconFile
            }

        #TODO: Make sure this overwrites existing config files correctly
        configPath = os.path.join(appDir, "config.ini")
        with open(configPath, 'w+') as configfile:
            config.write(configfile)
        
        return configPath

    def downloadIcon(self, url, appDir):
        #Get all favicons
        icons = favicon.get(url)

        #Find the largest favicon
        icon = icons[0]

        if icon:
            iconPath = os.path.join(appDir, "icon")

            #Remove an existing icon if applicable
            if os.path.exists(iconPath):
                os.remove(iconPath)
            
            #Download the icon and save it
            response = requests.get(icon.url, stream=True)
            origIconPath = iconPath+'.'+icon.format
            with open(origIconPath, 'wb') as image:
                for chunk in response.iter_content(1024):
                    image.write(chunk)
            
            self.onUpdate(16)
            
            #If not already an ico file, convert it
            finalIconPath = iconPath + '.ico'
            if icon.format != 'ico':
                img = Image.open(origIconPath)
                img.save(finalIconPath)
        
            #Return the path to the saved icon
            return finalIconPath

        return None

    def sanitizeUrl(self, url):
        url = url.strip()

        if not (url.startswith('https://') or url.startswith('http://')):
            url = "https://" + url

        self.url_Input.ChangeValue(url)

        return url
    
    def sanitizeText(self, text):
        result = ""

        text = text.lstrip()

        for c in text:
            if c.isalpha() or c==' ':
                result += c

        return result
    
    def validateText(self, event):
        insertPoint = self.appName_Input.GetInsertionPoint()
        val = self.appName_Input.GetValue()
        self.appName_Input.ChangeValue(self.sanitizeText(val))
        if len(val) > len(self.appName_Input.GetValue()):
            self.appName_Input.SetInsertionPoint(insertPoint-1)
    
    def checkUrl(self, url):
        if len(url) == 0 or not (url.startswith('https://') or url.startswith('http://')):
            self.url_Input.SetBackgroundColour("pink")
            return False
        return True
    
    def checkName(self, name):
        if len(name) == 0:
            self.appName_Input.SetBackgroundColour("pink")
            return False
        
        for c in name:
            if not (c.isalpha() or c==' '):
                self.appName_Input.SetBackgroundColour("pink")
                return False

        return True

    def addMessage(self, message):
        self.message += message + '\n'
        self.messageBox.SetLabel(self.message)

    def clearMessage(self):
        self.message = ""
        self.addMessage('')

class AppManager(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        my_sizer = wx.BoxSizer(wx.VERTICAL)

        #Set styles
        self.SetBackgroundColour((44, 137, 160))

        #Add title
        titleFont = wx.Font(35, wx.DEFAULT, wx.NORMAL, wx.DEFAULT)

        self.title = wx.StaticText(self, label=text["title"], style=wx.ALIGN_LEFT)
        self.title.SetFont(titleFont)
        self.title.SetForegroundColour((255,255,255))
        my_sizer.Add(self.title, 0, wx.TOP | wx.LEFT | wx.EXPAND, 8)

        #Add create button
        self.createButton = wx.Button(self, label="Create New App")
        self.createButton.Bind(wx.EVT_BUTTON, parent.switchPanels)
        my_sizer.Add(self.createButton, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, 8)

        #Create the app list
        self.appList = wx.ListCtrl(self, size=wx.DefaultSize, style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_SINGLE_SEL)
        my_sizer.Add(self.appList, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)

        #Create list event callbacks
        self.currentItem = None
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onItemSelected, self.appList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onItemDeselected, self.appList)

        self.populateList()

        buttonPanelSizer = wx.BoxSizer(wx.HORIZONTAL)

        #Add remove button
        self.removeButton = wx.Button(self, label="Remove")
        self.removeButton.Bind(wx.EVT_BUTTON, self.onRemove)
        buttonPanelSizer.Add(self.removeButton, 0, wx.ALL, 5)

        #Add run button
        self.runButton = wx.Button(self, label="Launch")
        self.runButton.Bind(wx.EVT_BUTTON, self.onRun)
        buttonPanelSizer.Add(self.runButton, 0, wx.ALL | wx.EXPAND, 5)

        my_sizer.Add(buttonPanelSizer, 0, wx.ALL | wx.EXPAND, 5)

        #Disable buttons
        self.runButton.Disable()
        self.removeButton.Disable()

        self.SetSizer(my_sizer)
        self.SetAutoLayout(True)
    
    def populateList(self):

        self.appList.ClearAll()

        #Add list columns, currently just name (plus icon) and url
        name = wx.ListItem()
        name.Mask = wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE | wx.LIST_MASK_FORMAT
        name.Image = -1
        name.Align = 0
        name.Text = "App Name"
        self.appList.InsertColumn(0, name)

        url = wx.ListItem()
        url.Align = wx.LIST_FORMAT_RIGHT
        url.Text = "Url"
        self.appList.InsertColumn(1, url)

        self.apps = self.getAppList()

        i = 0
        for app in self.apps:
            index = self.appList.InsertItem(self.appList.GetItemCount(), 0)
            self.appList.SetItem(index, 0, app.name)
            self.appList.SetItem(index, 1, app.url)
            self.appList.SetItemData(index, i)
            i += 1
        
        self.appList.SetColumnWidth(0, 300)
        self.appList.SetColumnWidth(1, wx.LIST_AUTOSIZE)

    #Return a list of installed apps
    def getAppList(self):
        if not os.path.exists(getAppsDir()):
            return []

        files = os.listdir(getAppsPath())
        apps = []

        for f in files:
            folder = os.path.join(getAppsDir(), str(f))
            #If it is a folder
            if os.path.isdir(folder):
                #If a config file exists in the folder assume it is an app
                configFile = os.path.join(folder, 'config.ini')
                if os.path.exists(configFile):
                    #Get data from config file
                    config = configparser.ConfigParser()
                    config.read(configFile)

                    url = config.get("settings", "url", fallback="https://google.com")
                    name = config.get("settings", "name", fallback="SSB Title")
                    icon = config.get("settings", "icon", fallback=None)
                    
                    app = App(name, url, icon)
                    apps.append(app)
        
        return apps

    def onItemSelected(self, event):
        self.runButton.Enable()
        self.removeButton.Enable()
        self.currentItem = event.Index
    
    def onItemDeselected(self, event):
        self.runButton.Disable()
        self.removeButton.Disable()
        self.currentItem = None

    def onRemove(self, event):
        if self.currentItem == None:
            return

        #Remove shortcuts and app folder
        name = self.apps[self.currentItem].name

        #Get the desktop and start folders
        desktopShortcut = os.path.join(winshell.desktop(), name + '.lnk')
        startmenuShortcut = os.path.join(winshell.start_menu(), name + '.lnk')

        #Get the app dir
        appDir = getAppDir(name)

        if os.path.exists(desktopShortcut):
            os.remove(desktopShortcut)
        
        if os.path.exists(startmenuShortcut):
            os.remove(startmenuShortcut)
        
        if os.path.exists(appDir):
            files = os.listdir(appDir)
            for f in files:
                f_path = os.path.join(appDir, f)
                if os.path.isfile(f_path):
                    os.remove(f_path)
            os.rmdir(appDir)
        
        self.populateList()

    def onRun(self, event):
        if self.currentItem == None:
            return

        name = self.apps[self.currentItem].name
        exeFile = getExePath()

        configFile = os.path.join(getAppDir(name), "config.ini")
        sub = Popen([exeFile, configFile])

#Used to store app info
class App():
    def __init__(self, name, url, icon):
        self.name = name
        self.url = url
        self.icon = icon

def checkBrowserExe():
    if not os.path.exists(getExePath()):
        exeZipFile = os.path.join(getDir(), 'DesktopifyBrowser.zip')
        if not os.path.exists(exeZipFile):
            exeZipFile = './DesktopifyBrowser.zip'
        if os.path.exists(exeZipFile):
            with zipfile.ZipFile(exeZipFile, 'r') as zip_ref:
                zip_ref.extractall(getAPPDATADir())

if __name__ == '__main__':
    checkBrowserExe()
    app = wx.App()
    frame = SSBCreator()
    app.MainLoop()