
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Line, Rect
from reportlab.lib.units import mm, inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A0, A4
from qgis.PyQt.QtWidgets import QMessageBox
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.utils import ImageReader
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
from os import path, startfile
from configparser import ConfigParser
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import locale
class PdfReports():
    def __init__(self, table, overview_list, template_name=None, grouped_data=None):
        self.logo_path = None
        self.overview_list = overview_list
        self.table = table
        self.grouped_data = grouped_data
        self.template_name = template_name
        self.create_delivery_note()

    def create_delivery_note(self):
        self.logo_path = path.join(path.dirname(__file__), 'logo.png')
        self.pdfmetrics = pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))

        # Open file dialog to select the file path for the PDF
        self.listennummer = ''
        #filename, _ = QFileDialog.getSaveFileName(None, "Save PDF", "", "PDF Files (*.pdf)")
        filename = 'C:/Users/forst04/Downloads/Test3.pdf'
        if not filename:
            return  # User canceled the operation or no file selected

        # Get the data from the table
        model = self.table.model()
        if not model:
            QMessageBox.critical(None, "Error", "No data available.")
            return

        data = []
        cols = [[13,'Los'],[2,'Nr.'],[3,'BA'],[6,'HS'],[8,'Qual'],[11,'QAbz'],[7,'Kl.'],[4,'Länge'],[29,'DM'],[30,'Kubatur'],[12,'Bem.']]
        self.colsAttr = []
        self.sum_x = 0
        for col in cols:
            # Dynamic Column Size
            self.colsAttr.append([col[0],col[1],self.table.horizontalHeader().sectionSize(col[0]) + 4])
            self.sum_x += self.table.horizontalHeader().sectionSize(col[0]) + 4
        los = []
        we = []
        buyer = []
        for row in range(model.rowCount()):
            rowData = []
            for col in self.colsAttr:
                column = col[0]
                index = model.index(row, column)
                item = model.data(index, Qt.DisplayRole)  # Get the data for each cell
                rowData.append(str(item))
                if column == 13:
                    los.append(str(item).strip())
            we_i = model.index(row, 20)
            bu_i = model.index(row, 23)
            we.append(str(model.data(we_i, Qt.DisplayRole)).strip())
            buyer.append(str(model.data(bu_i, Qt.DisplayRole)).strip())
            data.append(rowData)
        lose = ','.join(list(dict.fromkeys(los)))
        we = ','.join(list(dict.fromkeys(we)))
        buyer = ','.join(list(dict.fromkeys(buyer)))

        # Create PDF
        try:
            self.parse_config()
            self.c = canvas.Canvas(filename, pagesize=A4)
            self.c.linkURL('http://google.com', (mm, mm, 10 * mm, 20 * mm), relative=1)
            # Insert Logo
            self.set_logo()
            self.set_page_header()
            # Set up the header
            self.c.setFont('Helvetica-Bold', 14)
            self.c.drawString(50, 720, str("Rundholzliste " + str(self.listennummer)))
            self.c.setFont('Helvetica-Bold', 11)
            self.c.drawString(50, 705, 'Los:')
            self.c.drawString(50, 690, 'Datum:')
            self.c.drawString(50, 675, 'Waldeigentümer:')
            self.c.drawString(50, 660, 'Käufer:')

            self.set_default_font()
            self.c.drawString(150, 706, lose)
            locale.setlocale(locale.LC_TIME,'de_CH')
            self.c.drawString(150, 691, str(date.today().strftime('%d. %B %Y')))
            self.c.drawString(150, 676, we)
            self.c.drawString(150, 661, buyer)
            # Draw table data
            row_height = 15
            y = 620
            self.page_num = 1
            self.set_table_header(y)
            y -= row_height

            """
            for row_data in data:
                if y < 15:
                    self.c.showPage()
                    self.page_num += 1
                    y = 740
                    self.set_table_header(y)
                    y -= row_height
                    self.set_logo()
                for i, (value, col_attr) in enumerate(zip(row_data, self.colsAttr)):
                    col_width = col_attr[2]
                    self.c.drawString(50 + sum((col[2] for col in self.colsAttr[:i])), y, value)
                    self.c.setStrokeColorRGB(0.8,0.8,0.8)
                    self.c.line(50, y-5, 50 + self.sum_x, y -5)
                y -= row_height
            self.c.setAuthor(self.company)
            """
            elements = []
            t = Table(data, colWidths=[1.9*inch] * 5)
            t.wrapOn(p, width, height)
            t.drawOn(p, x, y)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to create delivery note: {str(e)}")
        self.set_overview_table(y)
        self.c.showPage()
        self.c.save()

        # QMessageBox.information(None, "Success", "Lieferschein erfolgreich erstellt.")

        startfile(filename)
    def set_logo(self):
        logo = ImageReader(self.logo_path)
        self.c.drawImage(logo, 510, 770, 50, 50, mask='auto')

    def set_overview_table(self, y):
        # Determine the starting position of the table
        y -= 20
        if y < 70:
            self.c.showPage()
            self.page_num += 1
            self.set_logo()
            y = 740

        # Define table headers
        headers = ['BA', 'HS', 'Qual.', 'Klasse', 'Anzahl', 'Kubatur', 'Prozentanteil']

        # Set font for table headers
        self.c.setFont('Helvetica-Bold', 10)

        # Draw table headers
        x = 50
        for header in headers:
            self.c.drawString(x, y, header)
            x += 60  # Adjust the spacing between headers if needed

        # Set font for table data
        self.c.setFont('Helvetica', 10)
        y -= 12
        # Draw table data
        # Adjust this value to set the vertical spacing between rows
        c1 = 0
        for row in self.overview_list:
            x = 50
            c2 = 0
            bold = False
            if not row[3]:
                bold = True
            for item in row:
                if self.overview_list and item and bold:
                    # Falls ja, konvertieren Sie es in eine Zeichenkette
                    self.c.setFont('Helvetica-Bold', 10)
                    if isinstance(item, Decimal):
                        item = str(item)
                        item_unicode = item.encode('utf-8').decode()
                    else:
                        item_unicode = item
                    self.c.drawString(x, y, item_unicode)
                elif item:
                    self.set_default_font()
                    if isinstance(item, Decimal):
                        # Falls ja, konvertieren Sie es in eine Zeichenkette
                        item = str(item)
                        item_unicode = item.encode('utf-8').decode()
                    else:
                        item_unicode = item
                    self.c.drawString(x, y, item_unicode)
                x += 60  # Adjust the spacing between columns if needed
                c2 += 1
            y -= 15  # Adjust this value to set the vertical spacing between rows
            c1 += 1
            if y < 15:
                self.c.showPage()
                self.page_num += 1
                self.set_logo()
                y = 740

    def set_table_header(self, y):
        self.c.setFont('Helvetica-Bold', 10)
        for i, col_attr in enumerate(self.colsAttr):
            self.c.drawString(50 + sum((col[2] for col in self.colsAttr[:i])), y, col_attr[1])
        self.c.line(50, y-2, 50 + self.sum_x, y-2)
        self.c.line(50, y + 12, 50 + self.sum_x, y + 12)
        self.set_default_font()

    def set_page_header(self):
        self.c.setFont('Helvetica-Bold', 9)
        self.c.drawString(50, 810, self.company)
        self.c.setFont('Helvetica', 9)
        self.c.drawString(50, 800, self.contact)
        self.c.drawString(50, 790, self.adress)
        self.c.drawString(50, 780, str(self.plz + ' ' + self.location))

        self.set_default_font()

    def parse_config(self):
        self.config = ConfigParser()
        self.config.read((path.join(path.dirname(__file__), 'config.cfg')))
        self.company = self.config.get('wood_app_settings', 'company')
        self.contact = self.config.get('wood_app_settings', 'contact')
        self.adress = self.config.get('wood_app_settings', 'adress')
        self.plz = self.config.get('wood_app_settings', 'plz')
        self.location = self.config.get('wood_app_settings', 'location')
        self.tel = self.config.get('wood_app_settings', 'tel')
        self.cell = self.config.get('wood_app_settings', 'cell')

    def set_default_font(self):
        self.c.setFont("Helvetica", 10)

