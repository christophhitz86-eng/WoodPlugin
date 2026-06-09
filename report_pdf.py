import os

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A0, A4
from cairosvg import svg2png
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QStandardPaths
from reportlab.lib.utils import ImageReader
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from os import path, startfile
from configparser import ConfigParser
from datetime import date
from decimal import Decimal
import locale
from screeninfo import get_monitors
from qrbill import QRBill
from qgis.PyQt.QtCore import pyqtSignal, QObject, pyqtSlot

class PdfReport(QObject):
    add_invoice = pyqtSignal(str, str)
    def __init__(self, table, overview_list, template_name, wb_kaeufer_data=None, invoice_data=None):
        super().__init__()
        self.logo_path = None
        self.invoice_data = invoice_data
        self.overview_list = overview_list
        self.table = table
        self.template_name = template_name
        self.curr_y = 0
        self.y = 0
        self.logo_path = path.join(path.dirname(__file__), 'logo.png')
        self.wb_kaeufer_data = wb_kaeufer_data
        self.sur_tees_list = None

    def execute(self):
        self.create_new_doc = True
        if 'Lieferschein' in self.template_name:
            self.first_page_invoice_deleviery_note = False
            self.create_delivery_note()
        elif 'Rechnung' in self.template_name:
            self.create_invoice()
        else:
            print('Keine Vorlage gefunden......')

    def setup_dokument(self):
        self.pdfmetrics = pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
        self.listennummer = ''

        if 'Entwurf' in self.template_name:
            download_path = QStandardPaths.standardLocations(QStandardPaths.DownloadLocation)[0]
            self.filename = download_path + f"""/{self.template_name}.pdf"""
        else:
            self.filename, _ = QFileDialog.getSaveFileName(None, "PDF speichern", "", "PDF Files (*.pdf)")
        if not self.filename:
            return  False# User canceled the operation or no file selected
        if self.remove_pdf():
            self.parse_config()
            self.c = canvas.Canvas(self.filename, pagesize=A4)
            self.page_num = 1
            # Insert Logo
            self.set_logo()
            self.set_page_header()
            return True
        else:
            return False

    def get_wb_kae_vars(self):
        ll = len(self.wb_kaeufer_data)-1

        # Kaeufer
        self.buy_id = self.wb_kaeufer_data[0][0]
        self.buy_company = self.wb_kaeufer_data[0][1]
        self.buy_adresse = self.wb_kaeufer_data[0][2]
        self.buy_plz = self.wb_kaeufer_data[0][3]
        self.buy_ort = self.wb_kaeufer_data[0][4]
        self.buy_address = self.wb_kaeufer_data[0][5]
        self.buy_email = self.wb_kaeufer_data[0][6]
        self.buy_mobil = self.wb_kaeufer_data[0][7]
        self.buy_phone = self.wb_kaeufer_data[0][8]
        self.skonto = self.wb_kaeufer_data[0][13]

        if self.skonto and self.skonto != 'kein Skonto':
            self.skonto_percent =  int(self.skonto[0])
        else:
            self.skonto_percent = 0

        self.los = self.wb_kaeufer_data[0][14]
        self.partie = self.wb_kaeufer_data[0][15]

        # Waldbesitzer
        self.wb_id = self.wb_kaeufer_data[ll][0]
        self.wb_company = self.wb_kaeufer_data[ll][1]
        self.wb_adresse = self.wb_kaeufer_data[ll][2]
        self.wb_plz = self.wb_kaeufer_data[ll][3]
        self.wb_ort = self.wb_kaeufer_data[ll][4]
        self.wb_address = self.wb_kaeufer_data[ll][5]
        self.wb_email = self.wb_kaeufer_data[ll][6]
        self.wb_mobil = self.wb_kaeufer_data[ll][7]
        self.wb_phone = self.wb_kaeufer_data[ll][8]
        self.wb_vat_id = self.wb_kaeufer_data[ll][9]
        self.wb_iban_id = self.wb_kaeufer_data[ll][10]
        self.wb_zugunsten_von = self.wb_kaeufer_data[ll][11]
        self.wb_fsc = self.wb_kaeufer_data[ll][12]

        self.invoice_nr = self.invoice_data[0]
        if len(self.invoice_data) > 3:
            self.sur_tees_list = self.invoice_data[6]
        lo = len(self.overview_list)-1
        self.invoice_ammount_netto = self.overview_list[lo][7]

    def draw_multiline_string(self, text, x, y, max_width, line_height):
        lines = text.split('\r\n')  # Teilen Sie den Text an den Zeilenumbrüchen auf
        for line in lines:
            self.c.drawString(x, y, line)  # Zeichnen Sie jede Zeile einzeln
            y -= line_height  # Aktualisieren Sie die Y-Position für die nächste Zeile
        return y

    def get_mwst(self):
        for ls in self.mwst_list:
            mwst_periods = ls.split(',')
            start_year = mwst_periods[0]
            end_year = mwst_periods[1]
            mwst_value = mwst_periods[2]
            inv_date = self.invoice_date_raw.strftime('%Y')
            if inv_date >= start_year and inv_date <= end_year:
                self.mwst = mwst_value

    def get_invoice_user_input(self):
        # Add Dialog and ask for Input (Invoive Date, Polter, Invoice Text, ...)
        if 'Entwurf' not in self.template_name:
            self.invoice_date_raw = self.invoice_data[3]
            locale.setlocale(locale.LC_TIME, 'de_CH')
            self.invoice_date = self.invoice_date_raw.strftime('%d. %B %Y')
            self.print_polter = self.invoice_data[3]
            self.send_invoice_via_email = self.invoice_data[4]
            self.kontierung = self.invoice_data[2]
            self.invoice_text = self.invoice_data[1]
        else:
            self.kontierung = '2.8206.4250.00'
            self.print_polter = False
            self.send_invoice_via_email = False
            locale.setlocale(locale.LC_TIME, 'de_CH')
            self.invoice_date_raw = date.today()
            self.invoice_date = self.invoice_date_raw.strftime('%d. %B %Y')
            self.invoice_text = 'Vielen Dank für Ihr Interesse an unserem Holz!'
        if self.wb_vat_id and self.wb_vat_id != '':
            self.tax_liability = True
        else:
            self.tax_liability = False

    def pdf_to_bytea(self, filename):
        try:
            # Öffne die Datei im Binärmodus und lese den Inhalt
            with open(filename, 'rb') as file:
                bytea_data = file.read()
            return bytea_data
        except FileNotFoundError:
            print("Die angegebene Datei wurde nicht gefunden.")
            return None
    def create_invoice(self):
        if self.setup_dokument():
            self.get_wb_kae_vars()
            self.get_invoice_user_input()
            self.c.drawRightString(560, 15, 'Seite ' + str(self.page_num))
            row_height = 15
            self.y = 690
            self.c.setFont('Helvetica-Bold', 10)
            self.y = self.draw_multiline_string(self.buy_address, 330, self.y, 300, row_height)
            self.invoice_nr_full = f"{str(date.today().strftime('%Y'))}/{str(self.invoice_nr)}"
            self.c.drawString(50, self.y+30, f"""{str(self.template_name)} Nr. {self.invoice_nr_full}""")

            self.y -= row_height*3
            self.set_default_font()

            self.set_beneficiary()

            if self.tax_liability:
                self.get_mwst()
            self.c.drawString(330,self.y-row_height,'Rechnungsdatum: ' + str(self.invoice_date))
            if self.kontierung and self.kontierung != '':
                self.c.drawString(50, self.y, 'Los: ' + str(self.los))
                if self.print_polter:
                    self.y -= row_height
                    self.c.drawString(50, self.y, 'Polter: ' + str(self.partie))
                self.y -= row_height
                self.c.drawString(50, self.y, self.kontierung)
            else:
                if self.print_polter:
                    self.c.drawString(50, self.y, 'Polter: ' + str(self.partie))
                    self.y -= row_height
                self.c.drawString(50, self.y-row_height, self.kontierung)
                self.y -= row_height


            self.set_overview_table(self.y+30, self.template_name)
            self.y = self.curr_y - (row_height*2)
            self.layout_checker( row_height, 180)
            self.set_default_font()
            self.c.setLineWidth(0.5)
            self.y -= row_height
            self.draw_sur_tees_list(True)
            self.y -= row_height*3
            self.layout_checker(row_height, 220)
            self.c.setLineWidth(0.5)
            self.c.line(50, self.y + 5, 560, self.y + 5)

            if self.tax_liability:
                self.y -= 60
                if self.sur_tees_list:
                    self.c.setFont('Helvetica-Bold', 11)
                    self.c.drawString(50, self.y, f"""Gesamtotal""")
                    self.c.drawRightString(560, self.y, str(self.format_and_round_amount(self.invoice_ammount_netto)))
                    self.c.drawRightString(510, self.y, 'CHF')
                    self.set_default_font()
                    self.y -= row_height*3
                self.c.drawString(50, self.y, f"""MwSt. {str(self.mwst)}% von {self.invoice_ammount_netto}""")

                self.c.drawString(50, self.y, f"""MwSt. {str(self.mwst)}% von {self.invoice_ammount_netto}""")
                self.mwst_ammount = round(self.invoice_ammount_netto / 100 * Decimal(self.mwst),2)

                self.c.drawRightString(560, self.y, str(self.mwst_ammount))
                self.c.drawRightString(510, self.y, 'CHF')
                self.invoice_ammount_brutto = Decimal(self.mwst_ammount) + Decimal(self.invoice_ammount_netto)
            else:
                self.invoice_ammount_brutto = self.invoice_ammount_netto
            self.y -= row_height*1.5
            self.draw_sur_tees_list(False)
            self.c.setFont('Helvetica-Bold', 11)
            self.c.drawRightString(560, self.y, self.format_and_round_amount(self.invoice_ammount_brutto))
            self.c.drawRightString(510, self.y, 'Rechnungsbetrag in CHF')
            self.y -= row_height
            self.set_default_font()
            self.y -= row_height
            if self.skonto_percent:
                self.invoice_ammount_skonto = Decimal(self.invoice_ammount_brutto)*((100-Decimal(self.skonto_percent))/100)
                self.c.drawRightString(560, self.y, self.format_and_round_amount(self.invoice_ammount_skonto))
                self.c.drawRightString(510, self.y, f"""Skonto: {self.skonto}     CHF""")
            else:
                self.c.drawRightString(560, self.y, f"""30 Tage netto""")

            self.y -= row_height*3
            self.c.setFont('Helvetica-Bold', 11)
            if self.wb_fsc:
                self.c.drawString(50, self.y, self.wb_fsc)
                self.y -= row_height
            self.c.drawString(50, self.y, self.invoice_text)
            if self.y < 330:
                self.c.showPage()
                self.page_num += 1
            self.get_qr_code()
            self.c.showPage()
            self.page_num += 1
            self.set_logo()
            self.set_page_header()
            self.create_new_doc = False
            self.first_page_invoice_deleviery_note = True
            self.create_delivery_note()
            self.c.showPage()
            self.c.save()
            if not self.skonto_percent:
                self.skonto_percent = 0
            bytea_data = self.pdf_to_bytea(self.filename)
            if 'Entwurf' not in self.template_name:
                sur_tees_sql = ''
                if self.sur_tees_list:
                    has_sur_tees = True
                    for i in self.sur_tees_list:
                        sur_tees_sql =  f"""INSERT INTO holzproduktion.wood_invoice_surcharge_tees 
                        (wood_invoice_id, is_name, quantity, einheit, 
                         ammount, total, mwst, bem) VALUES ((SELECT id FROM new_id),'{i[0]}', {i[1]}, '{i[2]}', {i[3]}, {i[4]}, '{i[5]}', '{i[6]}');"""
                else:
                    has_sur_tees = False
                sql = f"""WITH new_id AS (INSERT INTO holzproduktion.wood_invoices (invoice_nr, invoice_name, invoice_ammount_brutto,
                invoice_ammount_netto,   
                 invoice_skonto,invoice_date, kunden_id, bem, wood_ids, pdf_file, surcharges_tees)
                                               VALUES ('{self.invoice_nr_full}', '{self.los}',{self.invoice_ammount_brutto}, 
                    {self.invoice_ammount_netto}, {self.skonto_percent}, '{self.invoice_date_raw}', {self.buy_id}, 
                         '{self.invoice_text}', %s, %s, '{has_sur_tees}') RETURNING id ) """

                sql = f"{sql} {sur_tees_sql} UPDATE holzproduktion.liegendholzlisten set status = 'verkauft' where id = ANY(%s);"
                self.add_invoice.emit(sql, self.filename)

            startfile(self.filename)
    def draw_sur_tees_list(self, mwst):
        row_height = 15

        mwst_bol = False
        if self.sur_tees_list:
            for i in self.sur_tees_list:
                print(str(i[5]))
                if i[5] == mwst:
                    mwst_bol = True
        if self.sur_tees_list and mwst_bol:
            self.c.setFont('Helvetica-Bold', 11)

            self.c.drawString(50, self.y, f""" Zu- & Abschläge:""")
            self.c.setFont('Helvetica-Bold', 10)
            self.y -= row_height * 1.75
            self.c.setLineWidth(0.5)
            self.c.line(50, self.y + 10, 510, self.y + 10)
            self.c.line(50, self.y - 5, 510, self.y - 5)
            self.c.drawString(50, self.y, "Bezeichnung")
            self.c.drawString(150, self.y, "Menge")
            self.c.drawString(210, self.y, "Einheit")
            self.c.drawString(270, self.y, "Ansatz")
            self.c.drawString(330, self.y, "Total in CHF")
            self.c.drawString(420, self.y, "Bemerkung")
            self.y -= row_height
            total = 0
            self.set_default_font()
            for i in self.sur_tees_list:
                if i[5]:
                    self.c.line(50, self.y -5, 510, self.y -5)
                    self.c.drawString(50, self.y, f"""{i[0]}""")
                    self.c.drawRightString(180, self.y, f"""{i[1]}""")
                    self.c.drawString(220, self.y, f"""{i[2]}""")
                    self.c.drawRightString(295, self.y, f"""{i[3]}""")
                    self.c.drawRightString(370, self.y, f"""{i[4]}""")
                    self.c.drawString(420, self.y, f"""{i[6]}""")
                    total += i[4]

                    self.y -= row_height
            self.c.setLineWidth(1)
            self.c.line(50, self.y-5, 510, self.y-5)
            self.c.setFont('Helvetica-Bold', 10)
            self.c.drawString(50, self.y, "Total")
            self.c.drawRightString(370, self.y, str(total))

            if mwst:
                self.invoice_ammount_netto += Decimal(total)
            self.y -= (row_height * 1.25)

    def layout_checker(self,  row_height, min_y):
        if self.y < min_y:
            self.c.showPage()
            self.page_num += 1
            self.y = 740
            self.y -= row_height
            self.set_logo()
            self.c.drawRightString(560, 15, 'Seite ' + str(self.page_num))
    def pdf_to_bytea(self, filename):
        try:
            # Öffne die Datei im Binärmodus und lese den Inhalt
            with open(filename, 'rb') as file:
                bytea_data = file.read()
            return bytea_data
        except FileNotFoundError:
            print("Die angegebene Datei wurde nicht gefunden.")
            return None
    def format_and_round_amount(self, amount):
        # Runden auf 5 Rappen
        rounded_amount = round((amount*2),1) / 2
        # Formatieren mit 1000er-Zeichen und Rückgabe
        formatted_amount = '{:,.2f}'.format(rounded_amount).replace(',', "'")
        return formatted_amount
    def round_amount(self, amount):
        rounded_amount = round((amount*2),1) / 2
        return rounded_amount
    def format_amount(self, amount):
        # Runden auf 5 Rappen
        formatted_amount = '{:,.2f}'.format(amount).replace(',', "'")
        return formatted_amount
    def get_qr_code(self):
        ammount = self.round_amount(self.invoice_ammount_brutto)
        my_bill = QRBill(
            account=str(self.wb_iban_id).replace(' ',''),
            language='de',
            creditor={
                'name': self.wb_company, 'street' : self.wb_adresse, 'pcode': self.wb_plz, 'city': self.wb_ort,
            },
            debtor={
                'name': self.buy_company, 'street' : self.buy_adresse, 'pcode': self.buy_plz, 'city': self.buy_ort,
            },
            amount=ammount,
        )

        svg_path = path.join(path.dirname(__file__), 'qr_code.svg')
        png_path = path.join(path.dirname(__file__), 'qr_code.png')
        my_bill.as_svg(svg_path)
        svg2png(url=svg_path,write_to=png_path, dpi=300)

        self.c.drawInlineImage(png_path,0,0, 595.842,300.758)

        os.remove(svg_path)
        os.remove(png_path)
    def create_delivery_note(self):
        valid = False
        if self.create_new_doc:
            if self.setup_dokument():
                valid = True
        else:
            valid = True
        if valid:
            # Get the data from the table
            data = []
            cols = [[3,'Los'],[2,'Nr.'],[4,'BA'],[5,'HS'],[7,'Qual'],[6,'QAbz'],[8,'Kl.'],[9,'Länge'],[12,'DM'],[13,'Kubatur'],[14,'Bem.']]
            self.colsAttr = []
            self.sum_x = 0
            sizeObject = QtWidgets.QDesktopWidget().screenGeometry(-1)
            col_width = 4
            for m in get_monitors():
                if m.width_mm < 300:
                    col_width = -18
            for col in cols:
                # Dynamic Column Size
                self.colsAttr.append([col[0],col[1],self.table.horizontalHeader().sectionSize(col[0]) + col_width])
                self.sum_x += self.table.horizontalHeader().sectionSize(col[0]) + col_width
            los = []
            we = []
            buyer = []
            model = self.table.model()
            if not model:
                QMessageBox.critical(None, "Error", "No data available.")
                return
            for row in range(model.rowCount()):
                rowData = []

                for col in self.colsAttr:
                    column = col[0]
                    index = model.index(row, column)
                    item = model.data(index, Qt.DisplayRole)  # Get the data for each cell
                    rowData.append(str(item))
                    if column == 3:
                        los.append(str(item).strip())
                we_i = model.index(row, 15)
                bu_i = model.index(row, 16)
                we.append(str(model.data(we_i, Qt.DisplayRole)).strip())
                buyer.append(str(model.data(bu_i, Qt.DisplayRole)).strip())
                data.append(rowData)

            lose = ','.join(list(dict.fromkeys(los)))
            we = ','.join(list(dict.fromkeys(we)))
            buyer = ','.join(list(dict.fromkeys(buyer)))

            # Create PDF
            try:
                # Set up the header
                self.c.setFont('Helvetica-Bold', 14)
                self.c.drawString(50, 720, str("Rundholzliste " + str(self.listennummer)))
                self.c.setFont('Helvetica-Bold', 11)
                self.c.drawString(50, 705, 'Los:')
                self.c.drawString(50, 690, 'Datum:')
                self.c.drawString(50, 675, 'Waldeigentümer:')
                self.c.drawString(50, 660, 'Käufer:')
                self.set_default_font()
                self.c.drawRightString(560, 15, 'Seite ' + str(self.page_num))
                self.c.drawString(150, 706, lose)
                locale.setlocale(locale.LC_TIME,'de_CH')
                self.c.drawString(150, 691, str(date.today().strftime('%d. %B %Y')))
                self.c.drawString(150, 676, we)
                self.c.drawString(150, 661, buyer)

                # Draw table data
                row_height = 15
                y = 620
                self.set_table_header(y)
                y -= row_height

                for row_data in data:
                    if y < 45:
                        self.c.showPage()
                        self.page_num += 1
                        y = 740
                        self.set_table_header(y)
                        y -= row_height
                        self.set_logo()
                        self.c.drawRightString(560, 15, 'Seite ' + str(self.page_num))
                    for i, (value, col_attr) in enumerate(zip(row_data, self.colsAttr)):
                        col_width = col_attr[2]
                        self.c.drawString(50 + sum((col[2] for col in self.colsAttr[:i])), y, value)
                        self.c.setStrokeColorRGB(0.8,0.8,0.8)

                        self.c.line(50, y-5, 50 + self.sum_x, y -5)
                    y -= row_height
                self.c.setAuthor(self.company)
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Erstellung Holzliste fehlgeschlagen: {str(e)}")
            if self.create_new_doc:
                self.set_overview_table(y, self.template_name)
                self.c.showPage()
                self.c.save()

                # QMessageBox.information(None, "Success", "Lieferschein erfolgreich erstellt.")

                startfile(self.filename)
    def set_logo(self):
        logo = ImageReader(self.logo_path)
        self.c.drawImage(logo, 510, 770, 50, 50, mask='auto')

    def set_overview_table(self, y, template):
        # Determine the starting position of the table
        y -= 50
        x = 50
        if y < 70:
            self.c.showPage()
            self.page_num += 1
            self.set_logo()
            y = 740
        # Define table headers
        if 'Lieferschein' in template:
            headers = [['BA',50], ['HS',115], ['Qual.',180], ['Klasse',245], ['Anzahl',300], ['Kubatur',370], ['%-Anteil',450]]
        elif 'Rechnung' in template:
            headers = [['BA',50], ['HS',110], ['Qual.',170], ['Klasse',230], ['Anzahl',295], ['Kubatur',370], ['Preis/m3',450], ['Preis',530]]
        # Set font for table title
        self.c.setFont('Helvetica-Bold', 12)
        self.c.setStrokeColorRGB(0, 0, 0)
        # Set Table Title
        if 'Lieferschein' in self.template_name:
            self.c.drawString(x, y, 'Zusammenfassung')

        y -= 22

        # Draw table headers
        self.c.setFont('Helvetica-Bold', 10)
        self.c.setStrokeColorRGB(0, 0, 0)

        line_width = 490
        if 'Rechnung' in self.template_name:
            line_width = 560
        self.c.line(50, y - 2, line_width, y - 2)
        self.c.line(50, y + 12, line_width, y + 12)
        for header in headers:
            self.c.drawString(header[1], y, header[0])

        # Set font for table data
        self.c.setFont('Helvetica', 10)
        y -= 15
        # Draw table data
        # Adjust this value to set the vertical spacing between rows
        c1 = 0
        for row in self.overview_list:
            c2 = 0
            bold = False
            if not row[3]:
                bold = True
            for item in row:
                x = headers[c2][1]
                is_nummeric = False
                if self.overview_list and item and bold:
                    # Falls ja, konvertieren Sie es in eine Zeichenkette
                    self.c.setFont('Helvetica-Bold', 10)
                    self.c.setStrokeColorRGB(0, 0, 0)
                    self.c.setFillColorRGB(0, 0, 0)
                    self.c.setLineWidth(0.7)
                    if isinstance(item, Decimal):
                        if 'Rechnung' in self.template_name:
                            item = self.format_amount(item)
                        else:
                            item = str(item)
                        item_unicode = item.encode('utf-8').decode()
                        is_nummeric = True
                    else:
                        item_unicode = item
                    if is_nummeric:
                        self.c.drawRightString(x + 30, y, item_unicode)
                    else:
                        if len(headers)-1 == c2:
                            self.c.drawRightString(x + 40, y, item_unicode)
                        else:
                            self.c.drawString(x, y, item_unicode)
                elif item:
                    self.set_default_font()
                    self.c.setStrokeColorRGB(0.8, 0.8, 0.8)
                    self.c.setLineWidth(0.5)
                    if isinstance(item, Decimal):
                        # Falls ja, konvertieren Sie es in eine Zeichenkette
                        if 'Rechnung' in self.template_name:
                            item = self.format_amount(item)
                        else:
                            item = str(item)
                        item_unicode = item.encode('utf-8').decode()
                        is_nummeric = True
                    else:
                        item_unicode = item
                    if is_nummeric:
                        self.c.drawRightString(x+30, y, item_unicode)
                    else:
                        if len(headers) - 1 == c2:
                            self.c.drawRightString(x + 40, y, item_unicode)
                        else:
                            self.c.drawString(x, y, item_unicode)
                self.c.line(50, y - 5, line_width, y - 5)
                #x += 60  # Adjust the spacing between columns if needed
                c2 += 1
            y -= 15  # Adjust this value to set the vertical spacing between rows
            c1 += 1
            if y < 45:
                self.c.showPage()
                self.page_num += 1
                self.set_logo()
                self.set_default_font()
                self.c.drawRightString(560, 15, 'Seite ' + str(self.page_num))
                if self.page_num == 1:
                    self.c.setFont('Helvetica-Bold', 10)
                    self.c.setStrokeColorRGB(0, 0, 0)
                else:
                    self.c.setFillColorRGB(0.8, 0.8, 0.8)
                    self.c.setFont('Helvetica-Bold', 10)
                    self.c.setStrokeColorRGB(0.8, 0.8, 0.8)
                    self.c.setLineWidth(0.7)
                y = 740
                for header in headers:
                    self.c.drawString(header[1], y, header[0])
                if 'Rechnung' in self.template_name:
                    line_width = 560
                self.c.line(50, y - 2, line_width, y - 2)
                self.c.line(50, y + 12, line_width, y + 12)
                y -= 15
        self.c.setLineWidth(1.75)
        self.c.line(50, y+10, line_width, y+10)
        self.curr_y = y
    def set_table_header(self, y):
        if self.page_num == 1 or self.first_page_invoice_deleviery_note:
            self.c.setFont('Helvetica-Bold', 10)
            self.first_page_invoice_deleviery_note = False
        else:
            self.c.setFillColorRGB(0.8,0.8,0.8)
            self.c.setFont('Helvetica-Bold', 10)
            self.c.setStrokeColorRGB(0.8, 0.8, 0.8)
            self.c.setLineWidth(0.7)

        for i, col_attr in enumerate(self.colsAttr):
            self.c.drawString(50 + sum((col[2] for col in self.colsAttr[:i])), y, col_attr[1])
        self.c.line(50, y-2, 50 + self.sum_x, y-2)
        self.c.line(50, y + 12, 50 + self.sum_x, y + 12)
        self.c.setLineWidth(1)
        self.c.setStrokeColorRGB(0, 0, 0)
        self.set_default_font()

    def set_page_header(self):
        self.c.setFont('Helvetica-Bold', 9)
        self.c.drawString(50, 810, self.company)
        self.c.setFont('Helvetica', 9)
        self.c.drawString(50, 800, self.contact)
        self.c.drawString(50, 790, self.adress)
        self.c.drawString(50, 780, str(self.plz + ' ' + self.location))

        self.c.setFont('Helvetica', 7)
        self.c.drawString(50, 765, 'E-Mail.:')
        self.c.drawString(80, 765, str(self.mail))
        self.c.drawString(50, 757, 'Tel.:')
        self.c.drawString(80, 757,  str(self.tel))
        self.c.drawString(50, 749, 'Mobil:')
        self.c.drawString(80, 749, str(self.cell))
        if 'Rechnung' in self.template_name:
            self.c.setLineWidth(0.3)
            self.c.line(50,745,560,745)
        self.set_default_font()

    def set_beneficiary(self):
        self.c.setFont('Helvetica-Bold', 7)
        y = 810
        self.c.drawString(330, y, u'Begünstigte(r)')
        self.c.setFont('Helvetica', 7)
        for i in str(self.wb_address).splitlines():
            y -= 8
            self.c.drawString(330, y, str(i))
        y -= 8
        self.c.drawString(330, y,self.wb_iban_id)
        if self.wb_vat_id:
            y -= 8
            self.c.drawString(330, y, 'UID: ' + self.wb_vat_id)

        self.set_default_font()


    def parse_config(self):
        self.config = ConfigParser()
        self.config.read((path.join(path.dirname(__file__), 'config.cfg')))
        self.company = self.config.get('wood_app_settings', 'company')
        self.contact = self.config.get('wood_app_settings', 'contact')
        self.adress = self.config.get('wood_app_settings', 'adress')
        self.plz = self.config.get('wood_app_settings', 'plz')
        self.location = self.config.get('wood_app_settings', 'location')
        self.mail = self.config.get('wood_app_settings', 'mail')
        self.tel = self.config.get('wood_app_settings', 'tel')
        self.cell = self.config.get('wood_app_settings', 'cell')
        self.mwst_txt = self.config.get('wood_app_settings','mwst')
        self.mwst_list = self.mwst_txt.split(';')

    def remove_pdf(self):
        try:
            if os.path.exists(self.filename):
                os.remove(self.filename)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Bitte Datei '{str(self.filename)}' schliessen.")
            return False

    def set_default_font(self):
        self.c.setFillColorRGB(0, 0, 0)
        self.c.setFont("Helvetica", 10)

