import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QLineEdit, 
    QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QGroupBox, QSpacerItem, QSizePolicy, QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QDateEdit, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QDate, QMutex
from PyQt5.QtGui import QFont, QPixmap, QColor, QPalette
import csv
from AmazonCrawler.sql.amazon_product import AmazonProduct

# 可用爬虫及其参数定义
SPIDERS = {
    'seller_full': [],  # 卖家全流程采集
    'bestseller_full': ['url'],  # 畅销榜全流程采集
    'jpo_brand': ['brand'],
    'tm_brand': ['brand'],
}

# UI显示用的爬虫中文名映射
SPIDER_DISPLAY_NAMES = {
    'seller_full': '卖家产品采集',
    'bestseller_full': '畅销排行采集',
    'jpo_brand': '日本商标查询',
    'tm_brand': '欧盟商标查询',
}

# 国家UI中文名映射
COUNTRY_DISPLAY_NAMES = {
    'US': '美国',
    'UK': '英国',
    'JP': '日本',
    'DE': '德国',
}
COUNTRIES = list(COUNTRY_DISPLAY_NAMES.keys())

class CrawlerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.mutex = QMutex()
        self._running = True

    def run(self):
        process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if not self._running:
                process.terminate()  # 停止进程
                break
            self.output_signal.emit(line)
        process.wait()
        self.finished_signal.emit()

    def stop(self):
        self.mutex.lock()
        self._running = False
        self.mutex.unlock()

class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择导出日期范围')
        self.setFixedSize(420, 240)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.start_date = QDateEdit(self)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit(self)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        form.addRow(QLabel('起始日期:'), self.start_date)
        form.addRow(QLabel('结束日期:'), self.end_date)
        # 快捷按钮区
        quick_layout = QHBoxLayout()
        btn_today = QPushButton('今天')
        btn_yesterday = QPushButton('昨天')
        btn_week = QPushButton('本周')
        btn_month = QPushButton('本月')
        btn_today.clicked.connect(self.set_today)
        btn_yesterday.clicked.connect(self.set_yesterday)
        btn_week.clicked.connect(self.set_week)
        btn_month.clicked.connect(self.set_month)
        for btn in [btn_today, btn_yesterday, btn_week, btn_month]:
            quick_layout.addWidget(btn)
        form.addRow(QLabel('快捷选择:'), quick_layout)
        layout.addLayout(form)
        # 国家筛选区
        group = QGroupBox('国家筛选')
        group_layout = QHBoxLayout()
        self.country_radio_group = QButtonGroup(self)
        self.country_radios = {}
        radio_all = QRadioButton('全部')
        radio_all.setFont(QFont('Microsoft YaHei', 12))
        group_layout.addWidget(radio_all)
        self.country_radio_group.addButton(radio_all)
        self.country_radio_group.setId(radio_all, -1)
        self.country_radios['ALL'] = radio_all
        radio_all.setChecked(True)
        for key in COUNTRIES:
            radio = QRadioButton(COUNTRY_DISPLAY_NAMES[key])
            radio.setFont(QFont('Microsoft YaHei', 12))
            group_layout.addWidget(radio)
            self.country_radio_group.addButton(radio)
            self.country_radio_group.setId(radio, COUNTRIES.index(key))
            self.country_radios[key] = radio
        group.setLayout(group_layout)
        layout.addWidget(group)
        # 确认/取消按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def set_today(self):
        today = QDate.currentDate()
        self.start_date.setDate(today)
        self.end_date.setDate(today)
    def set_yesterday(self):
        yesterday = QDate.currentDate().addDays(-1)
        self.start_date.setDate(yesterday)
        self.end_date.setDate(yesterday)
    def set_week(self):
        today = QDate.currentDate()
        start = today.addDays(-(today.dayOfWeek()-1))
        self.start_date.setDate(start)
        self.end_date.setDate(today)
    def set_month(self):
        today = QDate.currentDate()
        start = QDate(today.year(), today.month(), 1)
        self.start_date.setDate(start)
        self.end_date.setDate(today)
    def get_filters(self):
        # 获取国家
        for key, radio in self.country_radios.items():
            if radio.isChecked():
                country = key
                break
        else:
            country = 'ALL'
        return (self.start_date.date().toString('yyyy-MM-dd'),
                self.end_date.date().toString('yyyy-MM-dd'),
                country)

class CrawlerUI(QWidget):
    def __init__(self):
        super().__init__()

        self.param_inputs = {}  # 确保参数输入字典初始化
        self.setWindowTitle('AmazonCrawler 爬虫运行器')
        self.resize(800, 600)
        self.setWindowIcon(self.style().standardIcon(getattr(self.style(), 'SP_FileDialogInfoView')))
        # Set application style
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei', 'Segoe UI', Arial;
            }
            QGroupBox {
                border: 1px solid #d3d3d3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QTextEdit {
                border: 1px solid #d3d3d3;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit {
                border: 1px solid #d3d3d3;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #4b8df8;
            }
            QComboBox {
                border: 1px solid #d3d3d3;
                border-radius: 3px;
                padding: 5px;
                min-width: 150px;
            }
            QComboBox:focus {
                border: 1px solid #4b8df8;
            }
        """)
        
        self.center()
        self.init_ui()
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_text)
        self.loading_dots = 0

    def center(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section
        header = QHBoxLayout()
        header.setSpacing(20)
        
        # Logo
        logo = QLabel()
        pixmap = self.style().standardIcon(getattr(self.style(), 'SP_ComputerIcon')).pixmap(56, 56)
        logo.setPixmap(pixmap)
        
        # Title
        title = QLabel('AmazonCrawler 爬虫运行器')
        title.setFont(QFont('Microsoft YaHei', 22, QFont.Bold))
        title.setStyleSheet('color: #2c3e50;')
        
        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()
        
        main_layout.addLayout(header)
        
        # Parameters group
        param_group = QGroupBox('参数设置')
        param_group.setFont(QFont('Microsoft YaHei', 13, QFont.Bold))
        param_layout = QFormLayout()
        param_layout.setVerticalSpacing(18)
        param_layout.setHorizontalSpacing(30)
        
        # Spider selection
        self.spider_combo = QComboBox()
        self.spider_combo.setFont(QFont('Microsoft YaHei', 13))
        for key in SPIDERS.keys():
            self.spider_combo.addItem(SPIDER_DISPLAY_NAMES.get(key, key), key)
        self.spider_combo.currentTextChanged.connect(self.update_param_fields)
        spider_label = QLabel('选择爬虫:', self)
        spider_label.setFont(QFont('Microsoft YaHei', 13))
        param_layout.addRow(spider_label, self.spider_combo)
        
        # Country selection（用单选圆点代替下拉框）
        self.country_row_widget = QWidget()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        hbox.setSpacing(10)
        country_label = QLabel('选择国家:', self)
        country_label.setFont(QFont('Microsoft YaHei', 13))
        hbox.addWidget(country_label)
        self.country_radio_group = QButtonGroup(self)
        self.country_radios = {}
        for key in COUNTRIES:
            radio = QRadioButton(COUNTRY_DISPLAY_NAMES[key])
            radio.setFont(QFont('Microsoft YaHei', 13))
            self.country_radio_group.addButton(radio)
            self.country_radio_group.setId(radio, COUNTRIES.index(key))
            hbox.addWidget(radio)
            self.country_radios[key] = radio
        self.country_radios[COUNTRIES[0]].setChecked(True)
        self.country_row_widget.setLayout(hbox)
        
        # 参数输入区
        self.param_layout = QFormLayout()
        self.param_layout.setVerticalSpacing(14)
        self.param_layout.setHorizontalSpacing(30)
        self.param_layout.addRow(self.country_row_widget)
        self.input_area_layout = QFormLayout()
        self.input_area_layout.setVerticalSpacing(14)
        self.input_area_layout.setHorizontalSpacing(30)
        self.param_layout.addRow(self.input_area_layout)
        param_layout.addRow(self.param_layout)
        self.update_param_fields(self.spider_combo.currentText())
        
        # Run, Stop, Export and Clear buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.run_btn = QPushButton('运行爬虫')
        self.run_btn.setFixedSize(170, 46)
        self.run_btn.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.run_btn.clicked.connect(self.run_crawler)

        self.stop_btn = QPushButton('停止爬虫')
        self.stop_btn.setFixedSize(170, 46)
        self.stop_btn.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_crawler)

        self.export_btn = QPushButton('导出数据')
        self.export_btn.setFixedSize(170, 46)
        self.export_btn.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #219150;
            }
        """)
        self.export_btn.clicked.connect(self.export_data)

        self.clear_log_btn = QPushButton('清除日志')
        self.clear_log_btn.setFixedSize(170, 46)
        self.clear_log_btn.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.clear_log_btn.clicked.connect(self.clear_log)

        btn_layout.addWidget(self.run_btn)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.clear_log_btn)
        btn_layout.addStretch()
        param_layout.addRow(btn_layout)
        
        param_group.setLayout(param_layout)
        main_layout.addWidget(param_group)
        
        # Output group
        output_group = QGroupBox('运行日志')
        output_group.setFont(QFont('Microsoft YaHei', 13, QFont.Bold))
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont('Consolas', 14))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #d3d3d3;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        palette = self.output_text.palette()
        palette.setColor(QPalette.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.Text, QColor(220, 220, 220))
        self.output_text.setPalette(palette)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        self.setLayout(main_layout)

    def update_param_fields(self, _):
        for i in reversed(range(self.input_area_layout.count())):
            self.input_area_layout.removeRow(i)
        self.param_inputs.clear()
        spider_key = self.spider_combo.currentData()

        # 控制国家选择显示/隐藏（整体widget）
        self.country_row_widget.setVisible(spider_key not in ['bestseller_full', 'jpo_brand'])

        # 如果是欧盟商标查询，只显示德国和英国
        if spider_key == 'tm_brand':
            for radio in self.country_radios.values():
                radio.setVisible(False)
            self.country_radios['DE'].setVisible(True)
            self.country_radios['UK'].setVisible(True)
            # 默认选中德国
            self.country_radios['DE'].setChecked(True)
        # 如果是日本商标查询，只显示日本
        elif spider_key == 'jpo_brand':
            for radio in self.country_radios.values():
                radio.setVisible(False)
            self.country_radios['JP'].setVisible(True)
            self.country_radios['JP'].setChecked(True)
        # 其他情况显示所有国家
        else:
            for radio in self.country_radios.values():
                radio.setVisible(True)

        # 卖家全流程采集需要asin输入
        if spider_key == 'seller_full':
            line_edit = QLineEdit()
            line_edit.setFont(QFont('Microsoft YaHei', 13))
            line_edit.setPlaceholderText('请输入ASIN（可多个空格分隔）')
            param_label = QLabel('ASIN列表:', self)
            param_label.setFont(QFont('Microsoft YaHei', 13))
            self.input_area_layout.addRow(param_label, line_edit)
            self.param_inputs['asin'] = line_edit
        # 畅销榜采集需要url输入
        elif spider_key == 'bestseller_full':
            line_edit = QLineEdit()
            line_edit.setFont(QFont('Microsoft YaHei', 13))
            line_edit.setPlaceholderText('请输入URL地址')
            param_label = QLabel('URL地址:', self)
            param_label.setFont(QFont('Microsoft YaHei', 13))
            self.input_area_layout.addRow(param_label, line_edit)
            self.param_inputs['url'] = line_edit

    def run_crawler(self):
        spider = self.spider_combo.currentData()
        # 获取当前选中的国家
        for key, radio in self.country_radios.items():
            if radio.isChecked():
                country = key
                break
        else:
            country = COUNTRIES[0]

        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.run_btn.setText('运行中...')
        self.output_text.append(
            f'<span style="color:#888;">开始执行流程: {SPIDER_DISPLAY_NAMES[spider]}，国家: {COUNTRY_DISPLAY_NAMES[country]}</span>')

        if spider == 'seller_full':
            asin = self.param_inputs.get('asin').text().strip() if 'asin' in self.param_inputs else ''
            if not asin:
                self.output_text.append('<span style="color:#e74c3c;">请填写ASIN！</span>')
                self.run_btn.setEnabled(True)
                self.export_btn.setEnabled(True)
                self.run_btn.setText('运行爬虫')
                return
            self.run_seller_full(country, asin)
        elif spider == 'bestseller_full':
            url = self.param_inputs.get('url').text().strip() if 'url' in self.param_inputs else ''
            if not url:
                self.output_text.append('<span style="color:#e74c3c;">请填写URL地址！</span>')
                self.run_btn.setEnabled(True)
                self.export_btn.setEnabled(True)
                self.run_btn.setText('运行爬虫')
                return
            self.run_bestseller_full(country, url)
        elif spider in ['jpo_brand', 'tm_brand']:
            # 仅在选择德国或英国时调用tm_brand
            if country in ['DE','JP','UK']:
                self.run_brand_query(spider, country)  # 传递国家参数
            else:
                self.output_text.append('<span style="color:#e74c3c;">tm_brand仅适用于德国和英国。</span>')
                self.run_btn.setEnabled(True)
                self.export_btn.setEnabled(True)
                self.run_btn.setText('运行爬虫')

    def stop_crawler(self):
        if hasattr(self, 'thread'):
            self.thread.stop()  # 停止爬虫线程
            self.output_text.append('<span style="color:#e74c3c;">爬虫已停止。</span>')

    def clear_log(self):
        self.output_text.clear()  # 清空日志输出区域

    def run_seller_full(self, country, asin):
        # 卖家信息采集 → 卖家ASIN采集 → 商品信息采集 → 商标采集（按国家）
        self.output_text.append('<span style="color:#2ecc71;">[1/4] 卖家信息采集开始...</span>')
        # 将ASIN用引号包裹
        asin_quoted = f'"{asin}"'
        self.run_spider('seller_shop', country, asin=asin_quoted, next_step=lambda: self.run_spider('seller_asin', country, next_step=lambda: self.run_spider('product_info', country, next_step=lambda: self.run_brand_spider(country))))

    def run_bestseller_full(self, country, url):
        # 畅销榜采集 → 商品信息采集 → 商标采集（按国家）
        self.output_text.append('<span style="color:#2ecc71;">[1/3] 畅销榜采集开始...</span>')
        # 从URL解析国家代码
        parsed_country = self.parse_country_from_url(url)
        self.run_spider('best_seller', parsed_country, url=url, 
                    next_step=lambda: self.run_spider('product_info', parsed_country, 
                                                    next_step=lambda: self.run_brand_spider(parsed_country)))

    def parse_country_from_url(self, url):
        """从URL中解析国家代码"""
        if '.com/' in url:
            return 'US'
        elif '.co.uk/' in url:
            return 'UK'
        elif '.co.jp/' in url:
            return 'JP'
        elif '.de/' in url:
            return 'DE'
        else:
            return 'US'  # 默认美国

    def run_brand_spider(self, country):
        # 根据国家自动选择商标采集
        if country == 'JP':
            self.output_text.append('<span style="color:#2ecc71;">[商标采集] 日本商标采集开始...</span>')
            self.run_spider('jpo_brand', country, next_step=self.on_all_finished)
        elif country == 'UK'or'DE':
            self.output_text.append('<span style="color:#2ecc71;">[商标采集] 欧盟商标采集开始...</span>')
            self.run_spider('tm_brand', country, next_step=self.on_all_finished)
        else:
            self.output_text.append('<span style="color:#888;">美国/德国暂不采集商标，流程结束。</span>')
            self.on_all_finished()

    def run_brand_query(self, spider, country):
        self.output_text.append(f'<span style="color:#2ecc71;">{SPIDER_DISPLAY_NAMES[spider]} 开始...</span>')
        # Pass the country parameter to the spider
        self.run_spider(spider, country, next_step=self.on_all_finished)

    def run_spider(self, spider, country, url=None, asin=None, brand=None, next_step=None):
        params = []
        # Include region parameter for all spiders except brand queries
        if spider in ['product_info', 'seller_asin', 'seller_shop'] and country:
            params.append(f'-a region={country}')
        # For brand queries, we pass the country differently
        elif spider in ['jpo_brand', 'tm_brand'] and country:
            params.append(f'-a region={country}')
        if url:
            params.append(f'-a url={url}')
        if asin and spider == 'seller_shop':
            params.append(f'-a asin_all={asin}')
        if brand and spider in ['jpo_brand', 'tm_brand']:
            params.append(f'-a brand={brand}')

        cmd = f'scrapy crawl {spider} ' + ' '.join(params)
        self.output_text.append(f'<span style="color:#7f8c8d;">> 运行命令: {cmd}</span>')
        self.thread = CrawlerThread(cmd)
        self.thread.output_signal.connect(self.append_output)

        def on_finish():
            if next_step:
                next_step()
            else:
                self.on_all_finished()

        self.thread.finished_signal.connect(on_finish)
        self.thread.start()

    def on_all_finished(self):
        self.output_text.append('<span style="color:#0057b7;">\n流程全部完成!</span>')
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.run_btn.setText('运行爬虫')

    def append_output(self, text):
        # Colorize different types of output
        if 'ERROR' in text:
            colored_text = f'<span style="color:#e74c3c;">{text}</span>'
        elif 'WARNING' in text:
            colored_text = f'<span style="color:#f39c12;">{text}</span>'
        elif 'DEBUG' in text:
            colored_text = f'<span style="color:#3498db;">{text}</span>'
        else:
            colored_text = f'<span style="color:#2ecc71;">{text}</span>'
            
        self.output_text.append(colored_text)
        self.output_text.moveCursor(self.output_text.textCursor().End)

    def update_loading_text(self):
        dots = '.' * (self.loading_dots % 4)
        self.run_btn.setText(f'运行中{dots}')
        self.loading_dots += 1

    def export_data(self):
        try:
            # 弹出日期范围选择对话框
            dlg = DateRangeDialog(self)
            if dlg.exec_() != QDialog.Accepted:
                return
            start_date, end_date, country = dlg.get_filters()
            db = AmazonProduct()
            sql = '''SELECT DISTINCT asin, brand, price, sale, region, status, created_at, updated_at FROM amazon_products WHERE (created_at BETWEEN %s AND %s OR updated_at BETWEEN %s AND %s)'''
            params = [start_date + ' 00:00:00', end_date + ' 23:59:59', start_date + ' 00:00:00', end_date + ' 23:59:59']
            if country != 'ALL':
                sql += ' AND region = %s'
                params.append(country)
            db.cursor.execute(sql, params)
            rows = db.cursor.fetchall()
            headers = [desc[0] for desc in db.cursor.description]
            if not rows:
                QMessageBox.information(self, '提示', '所选条件下没有可导出的数据！')
                return
            file_path, _ = QFileDialog.getSaveFileName(self, '保存为CSV文件', f'amazon_products_{start_date}_to_{end_date}_{country}.csv', 'CSV Files (*.csv)')
            if not file_path:
                return
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            self.output_text.append(f'<span style="color:#27ae60;">数据已成功导出到: {file_path}</span>')
            QMessageBox.information(self, '导出成功', f'数据已导出到: {file_path}')
        except Exception as e:
            self.output_text.append(f'<span style="color:#e74c3c;">导出失败: {e}</span>')
            QMessageBox.critical(self, '导出失败', f'导出失败: {e}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create a dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(50, 50, 50))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(50, 50, 50))
    palette.setColor(QPalette.Text, QColor(50, 50, 50))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(50, 50, 50))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = CrawlerUI()
    window.show()
    sys.exit(app.exec_())