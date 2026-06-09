@echo off
call "C:\OSGeo4W\bin\o4w_env.bat"
call "C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat"

@echo on
pyrcc5 -o resources.py resources.qrc