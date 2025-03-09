from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFormLayout, QMessageBox, QFileDialog
)

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl, QObject, pyqtSlot
import sys
import os
import folium
import json
from folium.plugins import MarkerCluster
from shutil import copy2  # For copying the file


class Bridge(QObject):
    @pyqtSlot(float, float)
    def send_coordinates(self, lat, lon):
        window.update_inputs(lat, lon)


class MapApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Интерактивная карта")
        self.resize(1200, 800)
        self.map_file = "map.html"
        self.form_visible = False

        # Основной лейаут
        main_layout = QHBoxLayout(self)

        self.map = folium.Map(location=[55.751244, 37.618423], zoom_start=10)
        self.marker_cluster = MarkerCluster().add_to(self.map)

        project_dir = os.path.abspath(os.path.dirname(__file__))

        # Виджет карты (QWebEngineView)
        self.map_view = QWebEngineView()
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.map_view.page().setWebChannel(self.channel)
        self.map_view.load(QUrl.fromLocalFile(project_dir + f"/{self.map_file}"))
        main_layout.addWidget(self.map_view, stretch=5)

        with open("markers.json", "r", encoding="utf-8") as file:
            self.predefined_markers = json.load(file)["locations"]

        # Боковая панель
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_panel.setLayout(side_layout)
        main_layout.addWidget(side_panel, stretch=2)

        # Форма для данных о маркере
        self.form_layout = QFormLayout()
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        self.title_input = QLineEdit()
        self.desc_input = QLineEdit()
        self.image_input = QLineEdit()  # Input field for image filename
        self.image_button = QPushButton("Выбрать изображение")  # Button to open file dialog

        self.form_layout.addRow(QLabel("Широта:"), self.lat_input)
        self.form_layout.addRow(QLabel("Долгота:"), self.lon_input)
        self.form_layout.addRow(QLabel("Заголовок:"), self.title_input)
        self.form_layout.addRow(QLabel("Описание:"), self.desc_input)
        self.form_layout.addRow(QLabel("Изображение:"), self.image_input)
        self.form_layout.addRow(self.image_button)

        self.image_button.clicked.connect(self.select_image)

        self.add_marker_btn = QPushButton("Добавить маркер")
        self.add_marker_btn.clicked.connect(self.add_marker)

        # Кнопка для показа/скрытия формы
        self.toggle_form_btn = QPushButton("Новый Маркер")
        self.toggle_form_btn.clicked.connect(self.toggle_form_visibility)
        side_layout.addWidget(self.toggle_form_btn)

        # Контейнер для формы
        self.form_container = QWidget()
        self.form_layout_container = QVBoxLayout(self.form_container)
        self.form_layout_container.addLayout(self.form_layout)
        self.form_layout_container.addWidget(self.add_marker_btn)
        self.form_container.setVisible(False)

        side_layout.addWidget(self.form_container)

        self.populate_map_with_predefined_markers(True)
        self.add_click_listener()
        self.map.save(self.map_file)

    def toggle_form_visibility(self):
        self.form_visible = not self.form_visible
        self.form_container.setVisible(self.form_visible)

        if self.form_visible:
            self.toggle_form_btn.setText("Отменить Создание")
        else:
            self.toggle_form_btn.setText("Новый Маркер")

    def populate_map_with_predefined_markers(self, ok):
        if not ok:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить карту.")
            return

        for loc in self.predefined_markers:
            # Формируем HTML для pop-up
            popup_content = f"""
            <h3>{loc['title']}</h3>
            <p>{loc['description']}</p>
            <img src="images/{loc['image']}" alt="{loc['title']}" width="200px">
            """
            folium.Marker(
                location=[loc["lat"], loc["lon"]],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=loc["title"]
            ).add_to(self.map)

    def add_marker(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            title = self.title_input.text()
            desc = self.desc_input.text()
            image = self.image_input.text()
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Необходимо ввести числовые значения для широты и долготы!")
            return

        if image:  # If there's an image input, copy the image file
            image_path = os.path.join("images", os.path.basename(image))
            if not os.path.exists(image_path):
                try:
                    copy2(image, image_path)  # Copy the image to the images folder
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить изображение: {e}")
                    return
        else:
            image_path = ""

        with open("markers.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        # Добавляем новый маркер
        new_marker = {
            "lat": lat,
            "lon": lon,
            "title": title,
            "description": desc,
            "image": os.path.basename(image_path)  # Store the image filename
        }
        data["locations"].append(new_marker)

        # Записываем обратно в файл
        with open("markers.json", "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        QMessageBox.information(self, "Успех", f"Маркер '{title}' успешно добавлен! Перезагрузите "
                                               f"приложение чтобы изменения вступили в силу. ")

        self.form_container.setVisible(False)
        self.toggle_form_btn.setText("Новый Маркер")

    def select_image(self):
        # Open file dialog to select an image
        image_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.gif)")
        if image_path:
            self.image_input.setText(image_path)

    def add_click_listener(self):
        script = '''
        map.on('click', function(e) {
            let lat = e.latlng.lat;
            let lon = e.latlng.lng;
            if (window.qtbridge) {
                window.qtbridge.send_coordinates(lat, lon);
            }
        });
        '''
        self.map_view.page().runJavaScript(script)

    def update_inputs(self, lat, lon):
        self.lat_input.setText(str(lat))
        self.lon_input.setText(str(lon))


app = QApplication(sys.argv)
window = MapApp()
window.show()
sys.exit(app.exec_())
