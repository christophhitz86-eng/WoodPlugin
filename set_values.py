
from PyQt5.QtWidgets import QDialog
from qgis.PyQt.QtWidgets import (QAction,QComboBox,QTableWidgetItem, QTableView,QMenu, QLabel,
                                 QFileDialog, QPushButton, QLineEdit, QGridLayout)
from qgis.PyQt.QtCore import Qt
from psycopg2 import connect

class SetValues(object):

    def __init__(self, table, bulk_upd=None, pg_conn=None, new_dialog=False, column_index=None, value=None):
        self.bulk_upd = bulk_upd
        self.table_view = table
        if pg_conn:
            self.conn = connect(pg_conn)
            self.cursor = self.conn.cursor()
        else:
            self.conn = None
            self.cursor = None
        self.new_dialog = new_dialog
        if not self.new_dialog:
            self.open_set_value_dialog()
        else:
            self.edit_column_value(column_index, value)



    def open_set_value_dialog(self):
        """
        Öffnet ein Dialogfenster zum Bearbeiten einer Spalte.
        """
        self.line_to_combo = False
        dialog = QDialog()
        dialog.setWindowTitle("Werte setzten")
        layout = QGridLayout()

        # QLabel für Beschreibung

        # Label und QComboBox in Grid Layout hinzufügen
        label_combo = QLabel("Spalte auswählen:")
        layout.addWidget(label_combo, 1, 0)
        self.combo_box = QComboBox()  # Hier self.combo_box, um von set_line_edit darauf zuzugreifen
        for i in range(self.table_view.model().columnCount()):
            self.combo_box.addItem(self.table_view.model().headerData(i, Qt.Horizontal))
        layout.addWidget(self.combo_box, 1, 1)

        # Label und QLineEdit in Grid Layout hinzufügen
        self.label_lineedit = QLabel("Wert:")
        layout.addWidget(self.label_lineedit, 2, 0)
        self.line_edit = QLineEdit()
        layout.addWidget(self.line_edit, 2, 1)

        # QPushButton für OK
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(
            lambda: self.on_ok_button_clicked(dialog, self.combo_box.currentIndex(), self.get_current_value()))
        layout.addWidget(ok_button, 3, 0)

        # QPushButton für Abbrechen
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(dialog.reject)
        layout.addWidget(cancel_button, 3, 1)

        self.combo_box.currentTextChanged.connect(self.set_line_edit)

        dialog.setLayout(layout)
        dialog.exec_()

    def on_ok_button_clicked(self, dialog, column_index, new_value):

        self.edit_column_value(column_index, new_value)
        dialog.accept()
        self.table_view.update()

    def edit_column_value(self, column_index, new_value):
        if column_index < 0 or column_index >= self.table_view.model().columnCount():
            print("Ungültiger Spaltenindex.")
            return

        selected_indexes = self.table_view.selectionModel().selectedIndexes()

        if not selected_indexes:
            print("Keine Zellen ausgewählt.")
            return

        original_indexes = []  # Liste zum Speichern der ursprünglichen Indizes

        for index in selected_indexes:
            # Umwandlung des Indexes in den ursprünglichen Index im Proxy-Modell
            original_index = self.table_view.model().mapToSource(index)
            original_indexes.append(original_index)

        ind_list = []
        # Ändern der Werte basierend auf den ursprünglichen Indizes
        for index in original_indexes:
            if index.isValid() and index.column() == column_index and not self.bulk_upd:
                self.table_view.model().sourceModel().setData(index, new_value, Qt.EditRole)
            elif index.isValid() and self.bulk_upd:
                first_column_index = index.sibling(index.row(), 0)
                # Hier wird der Wert der Zelle in der ersten Spalte abgerufen
                cell_value = first_column_index.data(Qt.DisplayRole)
                ind_list.append(cell_value)
        unique_ids = list(dict.fromkeys(ind_list))

        if self.bulk_upd:
            header_title = self.table_view.model().headerData(column_index, Qt.Horizontal)

            query_col_comment = f""" SELECT c.column_name, c.data_type FROM pg_catalog.pg_statio_all_tables AS st
                    INNER JOIN information_schema.columns c ON c.table_schema = st.schemaname
                    AND c.table_name = st.relname LEFT join pg_catalog.pg_description pgd
                    ON pgd.objoid=st.relid AND pgd.objsubid=c.ordinal_position
                    WHERE st.relname = 'liegendholzlisten' and pgd.description = '{header_title}';"""

            self.cursor.execute(query_col_comment)
            tbl_attr = self.cursor.fetchall()
            selected_column = tbl_attr[0][0]
            data_type = tbl_attr[0][1]
            if 'character vary' in data_type:
                new_value = f"'{new_value}'"
            query_update = f"""Update holzproduktion.liegendholzlisten set {selected_column} = {new_value} where id = ANY(Array[{unique_ids}])"""
            self.cursor.execute(query_update)
            self.conn.commit()

    def set_line_edit(self, text):
        """
        Ändert das Widget im line_edit je nach Auswahl in der combo_box.
        """
        if text in ['WB', 'Käufer'] and self.bulk_upd:
            # Wenn 'Waldbesitzer' oder 'Käufer' ausgewählt sind, ändere das Widget zu QComboBox
            layout = self.line_edit.parent().layout()
            layout.removeWidget(self.line_edit)
            self.line_edit.deleteLater()
            self.combo_box_line_edit = QComboBox()
            if text == 'WB':
                first_vals = [['Forstbetrieb Siggenberg',732],['Ortsbürgergemeinde Freienwil',503]]
                sql = f"""SELECT k.name, k.id from kimai.kimai_customers k 
                            LEFT JOIN kimai.kimai_customers_meta km ON 
                            k.id = km.customer_id WHERE km.value = ANY(ARRAY['Privatwaldbesitzer','öffentliche Waldbesitzer']) and k.visible = True order by k.name asc"""
            elif text == 'Käufer':
                sql = f"""SELECT k.name, k.id from kimai.kimai_customers k 
                    LEFT JOIN kimai.kimai_customers_meta km ON 
                    k.id = km.customer_id WHERE km.value = 'Holzkäufer' and k.visible = True order by k.name asc"""
                first_vals = [['WM-Holz AG', 311], ['Schwere AG', 607], ['Sägerei Trachsel AG', 552]]
            self.cursor.execute(sql)
            res = self.cursor.fetchall()
            for v in first_vals:
                self.combo_box_line_edit.addItem(v[0], v[1])
            self.combo_box_line_edit.insertSeparator(len(first_vals))
            for r in res:
                if r[0] not in first_vals:
                    self.combo_box_line_edit.addItem(r[0], r[1])



            layout.addWidget(self.combo_box_line_edit, 2, 1)
            self.label_lineedit.setText("Wert auswählen:")
            self.line_to_combo = True
        elif self.line_to_combo and self.bulk_upd:
            # Andernfalls ändere das Widget zurück zu QLineEdit
            layout = self.combo_box_line_edit.parent().layout()
            layout.removeWidget(self.combo_box_line_edit)
            self.combo_box_line_edit.deleteLater()
            self.line_edit = QLineEdit()
            layout.addWidget(self.line_edit, 2, 1)
            self.label_lineedit.setText("Wert:")

    def get_current_value(self):
        """
        Gibt den aktuellen Wert zurück, abhängig davon, ob QLineEdit oder QComboBox verwendet wird.
        """
        if hasattr(self, 'combo_box_line_edit'):
            return self.combo_box_line_edit.currentText()
        else:
            return self.line_edit.text()
