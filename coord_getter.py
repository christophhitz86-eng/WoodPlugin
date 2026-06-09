
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QColor
from qgis.PyQt.QtCore import QObject, pyqtSignal, Qt, QVariant
from qgis.core import (QgsSymbol, QgsSingleSymbolRenderer, QgsCoordinateTransform,
                       QgsCoordinateReferenceSystem, QgsProject,
                        QgsVectorLayer, QgsField, QgsPointXY, QgsGeometry, QgsFeature)
from collections import defaultdict
from psycopg2 import connect
class CoordinateGetter(QObject):
    coordinatesClicked = pyqtSignal(float, float)

    def __init__(self, canvas, view, layer_name, required_columns, pg_conn=None, bulk_upd=None):
        super().__init__()
        self.view = view
        self.conn = pg_conn
        self.bulk_upd = bulk_upd
        self.required_columns = required_columns
        self.layer_name = layer_name
        self.canvas = canvas
        self.map_tool = QgsMapToolEmitPoint(self.canvas)
        self.map_tool.canvasClicked.connect(self.canvas_clicked)
        self.canvas.setMapTool(self.map_tool)

        self.index_ba = self.required_columns[0]
        self.index_laenge = self.required_columns[1]
        self.index_sortiment = self.required_columns[2]
        self.index_vol = self.required_columns[3]
        self.index_y = self.required_columns[4]
        self.index_x = self.required_columns[5]

    def canvas_clicked(self, point, button):
        if button == Qt.LeftButton:
            x = point.x()
            y = point.y()
            self.coordinatesClicked.emit(x, y)


    def create_temp_layer(self):
        self.index_ba = self.required_columns[0]
        self.index_laenge = self.required_columns[1]
        self.index_sortiment = self.required_columns[2]
        self.index_vol = self.required_columns[3]
        if self.bulk_upd:
            self.index_y = self.required_columns[5]
            self.index_x = self.required_columns[4]
        else:
            self.index_y = self.required_columns[4]
            self.index_x = self.required_columns[5]
        existing_layers = QgsProject.instance().mapLayersByName(self.layer_name)
        for layer in existing_layers:
            QgsProject.instance().removeMapLayer(layer)

        if not self.view.model():
            print("Keine Daten vorhanden.")
            return

        missing_columns = [col for col in self.required_columns if not self.view.model().headerData(col, Qt.Horizontal)]
        if missing_columns:
            print("Fehlende Spalten:", missing_columns)
            return

        grouped_data = self.group_and_aggregate_data()

        temp_layer = self.create_temp_layer_from_grouped_data(grouped_data)

        print("Temporärer Layer erfolgreich erstellt und zur Karte hinzugefügt.")

    def group_and_aggregate_data(self):
        grouped_data = defaultdict(lambda: {"sum_col13": 0, "count": 0, "BA": set(), "sortimente": set()})
        for row in range(self.view.model().rowCount()):
            y = float(self.view.model().index(row, self.index_y).data())
            x = float(self.view.model().index(row, self.index_x).data())
            key = (y, x)
            grouped_data[key]["sum_col13"] += float(self.view.model().index(row, self.index_vol).data())
            grouped_data[key]["count"] += 1
            grouped_data[key]["BA"].add(str(self.view.model().index(row, self.index_ba).data()))
            grouped_data[key]["sortimente"].add(str(self.view.model().index(row, self.index_sortiment).data()))
        return grouped_data

    def on_coordinates_clicked(self, x, y):
        self.edit_column_value(self.index_y, str(y), 'y')
        self.edit_column_value(self.index_x, str(x), 'x')
        if not self.bulk_upd:
            self.create_temp_layer()

    def create_temp_layer_from_grouped_data(self, grouped_data):
            temp_layer = QgsVectorLayer("Point?crs=EPSG:2056", self.layer_name, "memory")
            temp_layer.dataProvider().addAttributes([
                QgsField("Summe", QVariant.Double),
                QgsField("Anzahl", QVariant.Int),
                QgsField("BA", QVariant.String),
                QgsField("Sortimente", QVariant.String)
            ])

            QgsProject.instance().addMapLayer(temp_layer)

            symbol = QgsSymbol.defaultSymbol(temp_layer.geometryType())
            symbol.setColor(QColor("#b75820"))
            renderer = QgsSingleSymbolRenderer(symbol)
            temp_layer.setRenderer(renderer)
            temp_layer.updateFields()

            provider = temp_layer.dataProvider()
            features = []
            for key, data in grouped_data.items():
                y, x = key
                dest_crs = QgsCoordinateReferenceSystem('EPSG:2056')
                source_crs = temp_layer.crs()
                transformer = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
                pt = transformer.transform(QgsPointXY(x, y))
                attrs = [data["sum_col13"], data["count"], ",".join(data["BA"]), ",".join(data["sortimente"])]
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPointXY(pt))
                feature.setAttributes(attrs)
                features.append(feature)

            provider.addFeatures(features)
            return temp_layer

    def edit_column_value(self, column_index, new_value, x_y):
        if column_index < 0 or column_index >= self.view.model().columnCount():
            print("Ungültiger Spaltenindex.")
            return

        selected_indexes = self.view.selectionModel().selectedIndexes()

        if not selected_indexes:
            print("Keine Zellen ausgewählt.")
            return

        original_indexes = []  # Liste zum Speichern der ursprünglichen Indizes

        for index in selected_indexes:
            # Umwandlung des Indexes in den ursprünglichen Index im Proxy-Modell
            original_index = self.view.model().mapToSource(index)
            original_indexes.append(original_index)

        ind_list = []
        # Ändern der Werte basierend auf den ursprünglichen Indizes
        for index in original_indexes:
            if index.isValid() and index.column() == column_index and not self.bulk_upd:
                self.view.model().sourceModel().setData(index, new_value, Qt.EditRole)
            elif index.isValid() and self.bulk_upd:
                first_column_index = index.sibling(index.row(), 0)
                # Hier wird der Wert der Zelle in der ersten Spalte abgerufen
                cell_value = first_column_index.data(Qt.DisplayRole)
                ind_list.append(cell_value)
        unique_ids = list(dict.fromkeys(ind_list))

        if self.bulk_upd:
            conn = self.conn
            cursor = conn.cursor()
            xy_column = None
            if x_y.lower() == 'y':
                xy_column = 'y'
            elif x_y.lower() == 'x':
                xy_column = 'x'
            query_update = f"""Update holzproduktion.liegendholzlisten set {xy_column} = {new_value} where id = ANY(Array[{unique_ids}])"""
            cursor.execute(query_update)
            conn.commit()