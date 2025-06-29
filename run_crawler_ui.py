import sys
import subprocess
import os
import csv
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox,QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
    QDateEdit, QRadioButton, QButtonGroup, QStyle
)
from PySide6.QtCore import QThread, Signal, QTimer, QDate, QMutex
from PySide6.QtGui import QFont, QColor, QPalette, QTextCursor
from AmazonCrawler.sql.amazon_product import AmazonProduct

# 设置环境变量防止 macOS 输入法警告
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.input*.debug=false'

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
    output_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.mutex = QMutex()
        self._running = True
        self.process = None

    def run(self):
        self.process = subprocess.Popen(
            self.cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )

        while self._running:
            line = self.process.stdout.readline()
            if not line:  # 进程结束
                break
            self.output_signal.emit(line.strip())

        # 确保进程被终止
        if self._running and self.process:
            self.process.terminate()
            self.process.wait()

        self.finished_signal.emit()

    def stop(self):
        self._running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()


class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择导出日期范围')
        self.setFixedSize(420, 240)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 日期选择
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
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
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
        start = today.addDays(-(today.dayOfWeek() - 1))
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

        return (
            self.start_date.date().toString('yyyy-MM-dd'),
            self.end_date.date().toString('yyyy-MM-dd'),
            country
        )


class CrawlerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.param_inputs = {}
        self.setWindowTitle('AmazonCrawler')
        self.resize(800, 600)

        # 设置窗口图标 (PySide6方式)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        # 设置应用样式
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
        self.thread = None

    def center(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 标题区域
        header = QHBoxLayout()
        header.setSpacing(20)

        # Logo
        logo = QLabel()
        pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(56, 56)
        logo.setPixmap(pixmap)

        # 标题
        title = QLabel('AmazonCrawler')
        title.setFont(QFont('Microsoft YaHei', 22, QFont.Bold))
        title.setStyleSheet('color: #2c3e50;')

        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()
        main_layout.addLayout(header)

        # 参数设置组
        param_group = QGroupBox('参数设置')
        param_group.setFont(QFont('Microsoft YaHei', 13, QFont.Bold))
        param_layout = QFormLayout()
        param_layout.setVerticalSpacing(18)
        param_layout.setHorizontalSpacing(30)

        # 爬虫选择
        self.spider_combo = QComboBox()
        self.spider_combo.setFont(QFont('Microsoft YaHei', 13))
        for key in SPIDERS.keys():
            self.spider_combo.addItem(SPIDER_DISPLAY_NAMES.get(key, key), key)
        self.spider_combo.currentTextChanged.connect(self.update_param_fields)

        spider_label = QLabel('选择爬虫:', self)
        spider_label.setFont(QFont('Microsoft YaHei', 13))
        param_layout.addRow(spider_label, self.spider_combo)

        # 国家选择
        self.country_row_widget = QWidget()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
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

        # 按钮区域
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

        # 输出日志区域
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
        # 清除现有参数输入
        for i in reversed(range(self.input_area_layout.count())):
            self.input_area_layout.removeRow(i)
        self.param_inputs.clear()

        spider_key = self.spider_combo.currentData()

        # 控制国家选择显示/隐藏
        self.country_row_widget.setVisible(spider_key not in ['bestseller_full', 'jpo_brand'])

        # 欧盟商标查询只显示德国和英国
        if spider_key == 'tm_brand':
            for radio in self.country_radios.values():
                radio.setVisible(False)
            self.country_radios['DE'].setVisible(True)
            self.country_radios['UK'].setVisible(True)
            self.country_radios['DE'].setChecked(True)

        # 日本商标查询只显示日本
        elif spider_key == 'jpo_brand':
            for radio in self.country_radios.values():
                radio.setVisible(False)
            self.country_radios['JP'].setVisible(True)
            self.country_radios['JP'].setChecked(True)

        # 其他情况显示所有国家
        else:
            for radio in self.country_radios.values():
                radio.setVisible(True)

        # 卖家全流程采集需要ASIN输入
        if spider_key == 'seller_full':
            line_edit = QLineEdit()
            line_edit.setFont(QFont('Microsoft YaHei', 13))
            line_edit.setPlaceholderText('请输入ASIN（可多个空格分隔）')
            param_label = QLabel('ASIN列表:', self)
            param_label.setFont(QFont('Microsoft YaHei', 13))
            self.input_area_layout.addRow(param_label, line_edit)
            self.param_inputs['asin'] = line_edit

        # 畅销榜采集需要URL输入
        elif spider_key == 'bestseller_full':
            line_edit = QLineEdit()
            line_edit.setFont(QFont('Microsoft YaHei', 13))
            line_edit.setPlaceholderText('请输入URL地址')
            param_label = QLabel('URL地址:', self)
            param_label.setFont(QFont('Microsoft YaHei', 13))
            self.input_area_layout.addRow(param_label, line_edit)
            self.param_inputs['url'] = line_edit

    def run_crawler(self):
        # 停止现有线程
        if self.thread is not None and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait(1000)

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
            if country in ['DE', 'JP', 'UK']:
                self.run_brand_query(spider, country)
            else:
                self.output_text.append('<span style="color:#e74c3c;">tm_brand仅适用于德国和英国。</span>')
                self.run_btn.setEnabled(True)
                self.export_btn.setEnabled(True)
                self.run_btn.setText('运行爬虫')

    def stop_crawler(self):
        if self.thread is not None:
            self.thread.stop()
            if self.thread.isRunning():
                self.thread.wait(1000)
            self.output_text.append('<span style="color:#e74c3c;">爬虫已停止。</span>')
            self.run_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.run_btn.setText('运行爬虫')

    def clear_log(self):
        self.output_text.clear()

    def run_seller_full(self, country, asin):
        self.output_text.append('<span style="color:#2ecc71;">[1/4] 卖家信息采集开始...</span>')
        asin_quoted = f'"{asin}"'
        self.run_spider('seller_shop', country, asin=asin_quoted,
                        next_step=lambda: self.run_spider('seller_asin', country,
                                                          next_step=lambda: self.run_spider('product_info', country,
                                                                                            next_step=lambda: self.run_brand_spider(
                                                                                                country))))

    def run_bestseller_full(self, country, url):
        self.output_text.append('<span style="color:#2ecc71;">[1/3] 畅销榜采集开始...</span>')
        parsed_country = self.parse_country_from_url(url)
        self.run_spider('best_seller', parsed_country, url=url,
                        next_step=lambda: self.run_spider('product_info', parsed_country,
                                                          next_step=lambda: self.run_brand_spider(parsed_country)))

    def parse_country_from_url(self, url):
        if '.com/' in url:
            return 'US'
        elif '.co.uk/' in url:
            return 'UK'
        elif '.co.jp/' in url:
            return 'JP'
        elif '.de/' in url:
            return 'DE'
        else:
            return 'US'

    def run_brand_spider(self, country):
        if country == 'JP':
            self.output_text.append('<span style="color:#2ecc71;">[商标采集] 日本商标采集开始...</span>')
            self.run_spider('jpo_brand', country, next_step=self.on_all_finished)
        elif country in ['UK', 'DE']:
            self.output_text.append('<span style="color:#2ecc71;">[商标采集] 欧盟商标采集开始...</span>')
            self.run_spider('tm_brand', country, next_step=self.on_all_finished)
        elif country in ['US']:
            self.output_text.append('<span style="color:#888;">[商标采集] 美国商标采集开始...</span>')
            self.run_spider('uspto_spider', country, next_step=self.on_all_finished)
        else:
            self.on_all_finished()

    def run_brand_query(self, spider, country):
        self.output_text.append(f'<span style="color:#2ecc71;">{SPIDER_DISPLAY_NAMES[spider]} 开始...</span>')
        self.run_spider(spider, country, next_step=self.on_all_finished)

    def run_spider(self, spider, country, url=None, asin=None, brand=None, next_step=None):
        params = []
        if spider in ['product_info', 'seller_asin', 'seller_shop'] and country:
            params.append(f'-a region={country}')
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
        if self.thread is not None:
            self.thread = None

    def append_output(self, text):
        if 'ERROR' in text:
            colored_text = f'<span style="color:#e74c3c;">{text}</span>'
        elif 'WARNING' in text:
            colored_text = f'<span style="color:#f39c12;">{text}</span>'
        elif 'DEBUG' in text:
            colored_text = f'<span style="color:#3498db;">{text}</span>'
        else:
            colored_text = f'<span style="color:#2ecc71;">{text}</span>'

        self.output_text.append(colored_text)
        self.output_text.moveCursor(QTextCursor.MoveOperation.End)

    def update_loading_text(self):
        dots = '.' * (self.loading_dots % 4)
        self.run_btn.setText(f'运行中{dots}')
        self.loading_dots += 1

    def export_data(self):
        try:
            dlg = DateRangeDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            start_date, end_date, country = dlg.get_filters()
            db = AmazonProduct()
            sql = '''SELECT DISTINCT asin, \
                                     brand, \
                                     price, \
                                     sale,
                                     region, \
                                     status, \
                                     created_at, \
                                     updated_at
                     FROM amazon_products
                     WHERE (created_at BETWEEN %s AND %s OR updated_at BETWEEN %s AND %s)'''
            params = [start_date + ' 00:00:00', end_date + ' 23:59:59',
                      start_date + ' 00:00:00', end_date + ' 23:59:59']

            if country != 'ALL':
                sql += ' AND region = %s'
                params.append(country)

            db.cursor.execute(sql, params)
            rows = db.cursor.fetchall()
            headers = [desc[0] for desc in db.cursor.description]

            if not rows:
                QMessageBox.information(self, '提示', '所选条件下没有可导出的数据！')
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存为CSV文件',
                f'amazon_products_{start_date}_to_{end_date}_{country}.csv',
                'CSV Files (*.csv)')

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

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait()
        event.accept()


if __name__ == '__main__':
    # 创建应用前设置环境变量
    os.environ['QT_LOGGING_RULES'] = '*.debug=false'

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置调色板
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
    sys.exit(app.exec())