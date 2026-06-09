import shutil
import os, subprocess
import os


source = "C:/Users/forst04/Documents/PyCharm/QGIS/dev/plugins/theme_catalog"
user_path = "C:/Users/ch/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/theme_catalog"
sys_path = "C:/OSGeo4W/apps/qgis-ltr/python/plugins/theme_catalog"

subprocess.call(source+"/compile.bat")
