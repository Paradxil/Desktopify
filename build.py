from subprocess import Popen
import PyInstaller
import os, sys
import zipfile

def getDir():
    dirname = os.path.dirname(os.path.abspath(__file__))
    return dirname

#Use pyinstaller to build the desktopifyBrowser and desktopify
def build(version="current"):
    desktopifySpecFile = os.path.join(getDir(), "src\\desktopify.spec")
    browserSpecFile = os.path.join(getDir(), "src\\desktopifyBrowser.spec")

    
    distDir ="./dist/" + str(version)

    sub = Popen(["pyinstaller",  "--distpath", distDir, "--clean", "--onefile", desktopifySpecFile], env=os.environ)
    sub.communicate()

    sub = Popen(["pyinstaller", "--distpath", distDir, "--clean", browserSpecFile], env=os.environ)
    sub.communicate()

    print("Zipping DesktopifyBrowser")
    zipdir(os.path.join(distDir, "DesktopifyBrowser"), os.path.join(distDir,'DesktopifyBrowser.zip'))

    print("Done building release")

def zipdir(path, filename):
    ziph = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))
    
    ziph.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        build(sys.argv[1])
    else:
        build()