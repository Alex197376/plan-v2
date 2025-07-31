import sys
import math
import json
import csv
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QPushButton, QVBoxLayout,
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem,
    QListWidget, QMessageBox, QSplitter, QTextEdit, QInputDialog
)
from PyQt6.QtGui import QPixmap, QPen, QColor, QWheelEvent, QPainter, QCursor, QKeyEvent
from PyQt6.QtCore import Qt, QPointF, QRectF
import numpy as np
from PyQt6.QtGui import QPolygonF
from aide import afficher_aide
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QSpacerItem, QSizePolicy


CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".mesure_plan_config.json")

class ImageViewer(QGraphicsView):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.clicks = []
        self.measures = []
        self.temp_line = None
        self.scale_factors = []
        self.scale_set = False
        self._zoom = 0
        self.measure_mode = False
        self.distance_mode = False
        self.surface_mode = False
        self.surface_points = []
        self.complex_points = []
        self.complex_polygon_started = False


        # ⚠️ Ajoute ces lignes
        self.surface_reference = []
        self.surface_stage = 0
        self.surface_length = 0.0
        self.surface_temp_items = []

        self.complex_surface_mode = False
        self.complex_polygon_started = False
        self.complex_points = []
        self.complex_items = []



        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.surface_simple_data = []     # pour stocker les surfaces rectangles
        self.surface_complexe_data = []   # pour stocker les surfaces complexes




    def load_image(self, path):
        self.scene.clear()
        pixmap = QPixmap(path)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.clicks = []
        self.measures = []
        self.scale_factors = []
        self.scale_set = False
        self._zoom = 0
        self.resetTransform()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Control:
            self.measure_mode = not self.measure_mode
            if self.measure_mode:
                self.setCursor(Qt.CursorShape.CrossCursor)
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        elif event.key() == Qt.Key.Key_Delete:
            self.main_window.delete_selected_measure()

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.RightButton and self.complex_surface_mode:
            if self.complex_points:
                if self.complex_items:
                    last_item = self.complex_items.pop()
                    self.scene.removeItem(last_item)
                self.complex_points.pop()
            return


        if event.button() == Qt.MouseButton.LeftButton and self.complex_surface_mode:
            point = self.mapToScene(event.pos())
            if self.complex_points:
                first = self.complex_points[0]
                dist = math.hypot(point.x() - first.x(), point.y() - first.y())
                if dist < 10:  # Seuil de fermeture
                    self.draw_complex_surface()

                    # Nettoyage de l'état temporaire pour démarrer un nouveau tracé
                    self.complex_points = []
                    self.complex_items = []
                    self.complex_polygon_started = False

                    # (Optionnel : si tu veux désactiver le mode après une surface)
                    # self.complex_surface_mode = False
                    # btn = self.main_window.findChild(QPushButton, "btn_surface_complexe")
                    # if btn:
                    #     btn.setChecked(False)

                    return


            if self.complex_points:
                last = self.complex_points[-1]
                pen = QPen(QColor("darkcyan"), 2)
                line = self.scene.addLine(last.x(), last.y(), point.x(), point.y(), pen)
                self.complex_items.append(line)
            self.complex_points.append(point)
            return
    
        if event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.pos())

            # -------- MODE SURFACE SIMPLE --------
            if self.surface_mode:
                point = self.mapToScene(event.pos())
                self.surface_reference.append(point)

                if len(self.surface_reference) == 2:
                    pt1, pt2 = self.surface_reference
                    dist_px = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())
                    scale = np.mean(self.scale_factors) if self.scale_factors else 1.0
                    default_val = dist_px * scale
                    val, ok = QInputDialog.getDouble(
                        self,
                        "Longueur mesurée",
                        "Entrez la longueur réelle (m) :",
                        float(f"{default_val:.2f}".replace(",", ".")), 0.01, 10000, 2
                    )
                    if ok:
                        self.surface_length = val
                        line = self.scene.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), QPen(QColor("blue"), 2))
                        self.surface_temp_items.append(line)
                        self.surface_stage = 1
                        QMessageBox.information(self, "Étape suivante", "Cliquez deux points pour mesurer la largeur.")
                    else:
                        self.surface_reference = []

                elif len(self.surface_reference) == 4:
                    pt3, pt4 = self.surface_reference[2:]
                    dist_px = math.hypot(pt4.x() - pt3.x(), pt4.y() - pt3.y())
                    scale = np.mean(self.scale_factors) if self.scale_factors else 1.0
                    default_val = dist_px * scale
                    val, ok = QInputDialog.getDouble(
                        self,
                        "Largeur mesurée",
                        "Entrez la largeur réelle (m) :",
                        float(f"{default_val:.2f}".replace(",", ".")), 0.01, 10000, 2
                    )
                    if ok:
                        surface = self.surface_length * val
                        line = self.scene.addLine(pt3.x(), pt3.y(), pt4.x(), pt4.y(), QPen(QColor("blue"), 2))
                        self.surface_temp_items.append(line)

                        # Ajout du texte au centre
                        center_x = (pt3.x() + pt4.x()) / 2
                        center_y = (pt3.y() + pt4.y()) / 2
                        text_item = QGraphicsTextItem(f"{surface:.2f} m²".replace(".", ","))
                        text_item.setPos(center_x, center_y)
                        self.scene.addItem(text_item)

                        self.main_window.list_measures.addItem(f"Surface: {surface:.2f} m²")
                    else:
                        # Recommencer uniquement la largeur
                        self.surface_reference = self.surface_reference[:2]
                        return

                    # Réinitialiser pour nouvelle surface
                    self.surface_reference = []
                    self.surface_temp_items = []
                    self.surface_stage = 0
                    return


            # -------- MODE MESURE (ÉCHELLE OU DISTANCE) --------
            if self.measure_mode:
                self.clicks.append(point)
                if len(self.clicks) % 2 == 1:
                    if self.temp_line:
                        self.scene.removeItem(self.temp_line)
                    pen = QPen(QColor("blue"), 2)
                    self.temp_line = self.scene.addLine(point.x(), point.y(), point.x(), point.y(), pen)

                elif len(self.clicks) >= 2:
                    pt1 = self.clicks[-2]
                    pt2 = self.clicks[-1]
                    if self.temp_line:
                        self.scene.removeItem(self.temp_line)
                        self.temp_line = None
                    pen = QPen(QColor("red") if self.distance_mode else QColor("green"), 2)
                    line = self.scene.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), pen)
                    dist_px = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

                    if self.distance_mode:
                        if self.scale_set:
                            scale = np.mean(self.scale_factors)
                            dist_m = dist_px * scale
                            label = QGraphicsTextItem(f"{dist_m:.2f} m".replace(".", ","))
                            label.setPos((pt1.x() + pt2.x()) / 2, (pt1.y() + pt2.y()) / 2)
                            self.scene.addItem(label)
                            self.main_window.list_measures.addItem(f"Mesure: {dist_m:.2f} m")
                            self.measures.append((pt1, pt2, dist_m, line, label))
                        else:
                            QMessageBox.warning(self, "Échelle non définie", "Définissez au moins 3 références avant de mesurer.")
                    else:
                        scale = np.mean(self.scale_factors) if self.scale_factors else 1.0
                        default_val = dist_px * scale
                        val, ok = QInputDialog.getDouble(
                            self,
                            "Entrer distance réelle",
                            "Distance en mètres :",
                            float(f"{default_val:.2f}".replace(",", ".")),  # valeur par défaut
                            0.01,
                            10000,
                            2
                        )

                        if ok:
                            self.scale_factors.append(val / dist_px)
                            label = QGraphicsTextItem(f"{val:.2f} m".replace(".", ","))
                            label.setPos((pt1.x() + pt2.x()) / 2, (pt1.y() + pt2.y()) / 2)
                            self.scene.addItem(label)
                            self.measures.append((pt1, pt2, val, line, label))
                            self.main_window.list_measures.addItem(f"Réf: {val:.2f} m")
                            if len(self.scale_factors) >= 3:
                                self.scale_set = True
                                self.distance_mode = True
                                QMessageBox.information(self, "Échelle définie", "L'échelle est active. Vous pouvez maintenant mesurer librement.")

        super().mousePressEvent(event)

    def draw_complex_surface(self):
        if len(self.complex_points) < 3:
            QMessageBox.warning(self, "Erreur", "Au moins 3 points sont nécessaires.")
            return

        # Ferme le polygone
        pen = QPen(QColor("darkcyan"), 2)
        poly = self.complex_points + [self.complex_points[0]]
        for i in range(len(poly) - 1):
            line = self.scene.addLine(poly[i].x(), poly[i].y(), poly[i+1].x(), poly[i+1].y(), pen)
            self.complex_items.append(line)

        # Calcul et remplissage de surface
        x = [p.x() for p in self.complex_points]
        y = [p.y() for p in self.complex_points]
        area_px = 0.5 * abs(sum(x[i]*y[(i+1)%len(x)] - x[(i+1)%len(x)]*y[i] for i in range(len(x))))
        scale = np.mean(self.scale_factors) if self.scale_factors else 1.0
        area_m2 = area_px * (scale ** 2)

        # Affichage
        polygon = self.scene.addPolygon(QPolygonF(self.complex_points), pen, QColor(0, 255, 255, 100))
        text = QGraphicsTextItem(f"{area_m2:.2f} m²".replace('.', ','))
        cx = sum(x) / len(x)
        cy = sum(y) / len(y)
        text.setPos(cx, cy)
        self.scene.addItem(text)

        self.main_window.list_measures.addItem(f"Surface complexe : {area_m2:.2f} m²")

        # Réinitialise
        self.complex_points = []
        self.complex_items = []


    def calculate_polygon_area(self, points):
        x = [p.x() for p in points]
        y = [p.y() for p in points]
        return abs(0.5 * sum(x[i]*y[i+1] - x[i+1]*y[i] for i in range(-1, len(points)-1))) * np.mean(self.scale_factors)**2

    def calculate_polygon_centroid(self, points):
        x = [p.x() for p in points]
        y = [p.y() for p in points]
        return QPointF(sum(x)/len(x), sum(y)/len(y))

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mesure sur plan photographié")
        self.setGeometry(100, 100, 1600, 900)
        self.last_dir = self.load_last_directory()
        self.viewer = ImageViewer(self)
        self.list_measures = QListWidget() 
        self.list_measures.itemDoubleClicked.connect(self.edit_measure_item)

        self.notes = QTextEdit()
        self.scale_factors = []

        # Déclaration du layout d'abord
        left_layout = QVBoxLayout()

        

        # === Boutons ===
        btn_load = QPushButton("Charger image")
        btn_load.clicked.connect(self.load_image)
        btn_save_project = QPushButton("Sauver projet")
        btn_save_project.clicked.connect(self.save_project)
        btn_load_project = QPushButton("Charger projet")
        btn_load_project.clicked.connect(self.load_project)
        btn_export_csv = QPushButton("Exporter CSV")
        btn_export_csv.clicked.connect(self.export_csv)

        btn_measure_mode = QPushButton("Mode Mesure")
        btn_measure_mode.setCheckable(True)
        btn_measure_mode.clicked.connect(self.toggle_measure_mode)

        btn_update_scale = QPushButton("Recalculer l’échelle")
        btn_update_scale.clicked.connect(self.recalculate_scale)

        btn_reset_scale = QPushButton("Réinitialiser l’échelle")
        btn_reset_scale.clicked.connect(self.reset_scale)

        btn_show_scale_details = QPushButton("Voir détails de l’échelle")
        btn_show_scale_details.clicked.connect(self.show_scale_details)

        self.label_scale = QLabel("Échelle moyenne : n.d.")

        btn_surface_mode = QPushButton("Mode Surface simple")
        btn_surface_mode.setCheckable(True)
        btn_surface_mode.clicked.connect(self.toggle_surface_mode)

        btn_complex_surface = QPushButton("Mode Surface Complexe")
        btn_complex_surface.setCheckable(True)
        btn_complex_surface.setObjectName("btn_surface_complexe")
        btn_complex_surface.clicked.connect(self.toggle_complex_surface_mode)

        btn_help = QPushButton("Aide / Guide utilisateur")
        btn_help.clicked.connect(self.afficher_aide)

        # === Groupes de boutons ===

        # 📂 Groupe : Fichier
        group_file = QGroupBox("📂 Fichier")
        layout_file = QVBoxLayout()
        layout_file.addWidget(btn_load)
        layout_file.addWidget(btn_save_project)
        layout_file.addWidget(btn_load_project)
        layout_file.addWidget(btn_export_csv)
        group_file.setLayout(layout_file)

        # 📏 Groupe : Références & Échelle
        group_scale = QGroupBox("📏 Références & Échelle")
        layout_scale = QVBoxLayout()
        layout_scale.addWidget(btn_measure_mode)
        layout_scale.addWidget(btn_update_scale)
        layout_scale.addWidget(btn_reset_scale)
        layout_scale.addWidget(btn_show_scale_details)
        layout_scale.addWidget(self.label_scale)
        group_scale.setLayout(layout_scale)

        # 📐 Groupe : Surfaces
        group_surface = QGroupBox("📐 Surfaces")
        layout_surface = QVBoxLayout()
        layout_surface.addWidget(btn_surface_mode)
        layout_surface.addWidget(btn_complex_surface)
        group_surface.setLayout(layout_surface)

        # ❓ Groupe : Aide
        group_help = QGroupBox("❓ Aide")
        layout_help = QVBoxLayout()
        layout_help.addWidget(btn_help)
        group_help.setLayout(layout_help)

        # === Layout global gauche ===
        left_layout = QVBoxLayout()
        left_layout.addWidget(group_file)
        left_layout.addWidget(group_scale)
        left_layout.addWidget(group_surface)
        left_layout.addWidget(group_help)
        left_layout.addStretch()


        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Références / mesures :"))
        right_layout.addWidget(self.list_measures)
        right_layout.addWidget(QLabel("Commentaires :"))
        right_layout.addWidget(self.notes)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        right_panel = QWidget()
        right_panel.setLayout(right_layout)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.viewer)
        splitter.addWidget(right_panel)
        splitter.setSizes([150, 1300, 150])

        self.setCentralWidget(splitter)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une image", self.last_dir, "Images (*.png *.jpg *.jpeg)")
        if path:
            self.viewer.load_image(path)
            self.last_dir = os.path.dirname(path)
            self.save_last_directory(self.last_dir)
            self.viewer.image_path = path

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter mesures", os.path.join(self.last_dir, "mesures.csv"), "CSV files (*.csv)")
        if path:
            with open(path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Point A (x, y)", "Point B (x, y)", "Distance (m)", "Commentaire"])
                for i, (pt1, pt2, dist, _, _) in enumerate(self.viewer.measures):
                    note = self.notes.toPlainText().splitlines()
                    comment = note[i] if i < len(note) else ""
                    writer.writerow([(pt1.x(), pt1.y()), (pt2.x(), pt2.y()), f"{dist:.2f}".replace(".", ","), comment])
            QMessageBox.information(self, "Export", "Mesures exportées avec succès.")

    def delete_selected_measure(self):
        row = self.list_measures.currentRow()
        if row >= 0 and row < len(self.viewer.measures):
            _, _, _, line_item, text_item = self.viewer.measures[row]
            self.viewer.scene.removeItem(line_item)
            self.viewer.scene.removeItem(text_item)
            del self.viewer.measures[row]
            self.list_measures.takeItem(row)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder projet", os.path.join(self.last_dir, "projet.json"), "Fichiers JSON (*.json)")
        if path:
            data = {
                "image_path": self.viewer.image_path,
                "scale_factors": self.viewer.scale_factors,
                "measures": [
                    {
                        "pt1": (m[0].x(), m[0].y()),
                        "pt2": (m[1].x(), m[1].y()),
                        "valeur": m[2],
                        "type": "référence" if not self.viewer.distance_mode else "mesure"
                    } for m in self.viewer.measures
                ],
                "surface_simple": getattr(self.viewer, "surface_simple_data", []),
                "surface_complexe": getattr(self.viewer, "surface_complexe_data", []),
                "notes": self.notes.toPlainText()
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "Sauvegarde", "Projet sauvegardé avec succès.")


    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger projet", self.last_dir, "Fichiers JSON (*.json)")
        if path:
            with open(path, "r") as f:
                data = json.load(f)
                self.viewer.measures.clear()
                self.viewer.surface_simple_data.clear()
                self.viewer.surface_complexe_data.clear()
                self.list_measures.clear()
                self.viewer.scene.clear()

                # Restaurer les mesures de distance
                for m in data.get("measures", []):
                    pt1 = QPointF(*m["pt1"])
                    pt2 = QPointF(*m["pt2"])
                    val = m["valeur"]
                    pen = QPen(QColor("red"), 2)
                    line = self.viewer.scene.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), pen)
                    label = QGraphicsTextItem(f"{val:.2f} m")
                    label.setPos((pt1.x() + pt2.x()) / 2, (pt1.y() + pt2.y()) / 2)
                    self.viewer.scene.addItem(label)
                    self.viewer.measures.append((pt1, pt2, val, line, label))
                    self.list_measures.addItem(f"Mesure: {val:.2f} m")

                # Restaurer surfaces simples
                for s in data.get("surface_simple", []):
                    pt1 = QPointF(*s["longueur_pts"][0])
                    pt2 = QPointF(*s["longueur_pts"][1])
                    pt3 = QPointF(*s["largeur_pts"][0])
                    pt4 = QPointF(*s["largeur_pts"][1])
                    val_long = s["longueur_valeur"]
                    val_larg = s["largeur_valeur"]
                    surface = s["surface_m2"]

                    line1 = self.viewer.scene.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), QPen(QColor("blue"), 2))
                    line2 = self.viewer.scene.addLine(pt3.x(), pt3.y(), pt4.x(), pt4.y(), QPen(QColor("blue"), 2))

                    cx = (pt3.x() + pt4.x()) / 2
                    cy = (pt3.y() + pt4.y()) / 2
                    text_item = QGraphicsTextItem(f"{surface:.2f} m²".replace(".", ","))
                    text_item.setPos(cx, cy)
                    self.viewer.scene.addItem(text_item)

                    self.viewer.surface_simple_data.append(s)
                    self.list_measures.addItem(f"Surface: {surface:.2f} m²")

                # Restaurer surfaces complexes
                for sc in data.get("surface_complexe", []):
                    points = [QPointF(*p) for p in sc["points"]]
                    poly = points + [points[0]]
                    pen = QPen(QColor("darkcyan"), 2)

                    for i in range(len(poly) - 1):
                        self.viewer.scene.addLine(poly[i].x(), poly[i].y(), poly[i+1].x(), poly[i+1].y(), pen)

                    polygon = self.viewer.scene.addPolygon(QPolygonF(points), pen, QColor(0, 255, 255, 100))

                    cx = sum(p.x() for p in points) / len(points)
                    cy = sum(p.y() for p in points) / len(points)
                    label = QGraphicsTextItem(f"{sc['surface_m2']:.2f} m²".replace('.', ','))
                    label.setPos(cx, cy)
                    self.viewer.scene.addItem(label)

                    self.viewer.surface_complexe_data.append(sc)
                    self.list_measures.addItem(f"Surface complexe : {sc['surface_m2']:.2f} m²")

    def update_scale_label(self):
        if self.scale_factors:
            scale = np.mean(self.scale_factors)
            self.label_scale.setText(f"Échelle moyenne : {scale:.5f} m/pixel")
        else:
            self.label_scale.setText("Échelle moyenne : n.d.")

    def recalculate_scale(self):
        self.viewer.scale_factors = []
        for i, m in enumerate(self.viewer.measures):
            if self.list_measures.item(i).text().lower().startswith("réf"):
                dist_px = math.hypot(m[1].x() - m[0].x(), m[1].y() - m[0].y())
                self.viewer.scale_factors.append(m[2] / dist_px)
        if len(self.viewer.scale_factors) >= 3:
            self.viewer.scale_set = True
            self.viewer.distance_mode = True
            moyenne = np.mean(self.viewer.scale_factors)
            self.label_scale.setText(f"Échelle moyenne : {moyenne:.5f}")
            QMessageBox.information(self, "Échelle mise à jour", "L'échelle a été recalculée avec succès.")
        else:
            self.label_scale.setText("Échelle moyenne : n.d.")
            QMessageBox.warning(self, "Échelle insuffisante", "Au moins 3 références sont nécessaires.")


    def reset_scale_full(self):
        self.scale_factors = []
        self.scale_set = False
        self.distance_mode = False
        self.update_scale_label()
        QMessageBox.information(self, "Réinitialisé", "L’échelle a été réinitialisée.")

    def show_scale_details(self):
        if not self.scale_factors:
            QMessageBox.information(self, "Détails", "Aucune référence disponible.")
            return
        text = "\n".join([f"{i+1} : {s:.5f} m/pixel" for i, s in enumerate(self.scale_factors)])
        text += f"\n\nMoyenne : {np.mean(self.scale_factors):.5f}"
        QMessageBox.information(self, "Références d’échelle", text)

    def reset_scale(self):
        self.viewer.scale_set = False
        self.viewer.scale_factors = []
        self.viewer.clicks = []
        self.viewer.measures = []
        self.list_measures.clear()
        QMessageBox.information(self, "Réinitialisation", "Échelle réinitialisée. Redessinez 3 traits.")

    def load_last_directory(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                return config.get("last_dir", "")
        return ""

    def save_last_directory(self, directory):
        with open(CONFIG_PATH, "w") as f:
            json.dump({"last_dir": directory}, f)

    def toggle_measure_mode(self, checked):
        self.viewer.distance_mode = checked
        mode = "mesure libre" if checked else "références d'échelle"
        QMessageBox.information(self, "Mode actif", f"Vous êtes en mode : {mode}")

    def toggle_surface_mode(self, checked):
        self.viewer.surface_mode = checked
        self.viewer.surface_stage = 0
        QMessageBox.information(self, "Surface simple", "Cliquez deux points pour mesurer la longueur, puis deux pour la largeur.")

    def toggle_complex_surface_mode(self, checked):
        self.viewer.complex_surface_mode = checked
        mode = "activé" if checked else "désactivé"
        QMessageBox.information(self, "Mode Surface Complexe", f"Mode Surface Complexe {mode}.")
   
    def edit_measure_item(self, item):
        row = self.list_measures.row(item)
        item_text = item.text()

        # Ne traiter que les références d’échelle
        if row < len(self.viewer.measures) and item_text.startswith("Réf:"):
            try:
                # Ancienne valeur (en m)
                old_val = self.viewer.measures[row][2]

                # Boîte de dialogue
                txt, ok = QInputDialog.getText(
                    self, "Modifier la référence", "Nouvelle valeur (m) :", text=str(old_val).replace('.', ',')
                )
                if not ok:
                    return

                # Conversion , → . et validation
                new_val = float(txt.replace(',', '.'))

                # Mise à jour
                pt1, pt2, _, line_item, text_item = self.viewer.measures[row]
                self.viewer.measures[row] = (pt1, pt2, new_val, line_item, text_item)
                text_item.setPlainText(f"{new_val:.2f} m".replace('.', ','))
                item.setText(f"Réf: {new_val:.2f} m")

                # Recalcul des facteurs d’échelle uniquement sur les références
                self.viewer.scale_factors = []
                for i, m in enumerate(self.viewer.measures):
                    if self.list_measures.item(i).text().startswith("Réf:"):
                        dist_px = math.hypot(m[1].x() - m[0].x(), m[1].y() - m[0].y())
                        self.viewer.scale_factors.append(m[2] / dist_px)

                if len(self.viewer.scale_factors) >= 3:
                    self.viewer.scale_set = True
                    self.viewer.distance_mode = True
                    QMessageBox.information(self, "Échelle mise à jour", "L'échelle a été recalculée automatiquement.")
                else:
                    self.viewer.scale_set = False
                    QMessageBox.warning(self, "Références insuffisantes", "Au moins 3 références sont nécessaires.")

                self.update_scale_label()

            except ValueError:
                QMessageBox.warning(self, "Erreur", "Entrée invalide. Veuillez entrer un nombre.")

    def recalculate_scale(self):
        self.viewer.scale_factors = []
        for m in self.viewer.measures:
            item_text = self.list_measures.item(self.viewer.measures.index(m)).text().lower()
            if item_text.startswith("réf"):
                dist_px = math.hypot(m[1].x() - m[0].x(), m[1].y() - m[0].y())
                self.viewer.scale_factors.append(m[2] / dist_px)
        if len(self.viewer.scale_factors) >= 3:
            self.viewer.scale_set = True
            self.viewer.distance_mode = True
            moyenne = np.mean(self.viewer.scale_factors)
            self.label_scale.setText(f"Échelle moyenne : {moyenne:.5f}")
            QMessageBox.information(self, "Échelle mise à jour", "L'échelle a été recalculée avec succès.")
        else:
            self.label_scale.setText("Échelle moyenne : n.d.")
            QMessageBox.warning(self, "Échelle insuffisante", "Au moins 3 références sont nécessaires.")

    def reset_scale_full(self):
        self.viewer.scale_factors = []
        self.viewer.scale_set = False
        self.viewer.distance_mode = False
        self.label_scale.setText("Échelle moyenne : n.d.")
        QMessageBox.information(self, "Réinitialisation", "Toutes les références d’échelle ont été supprimées.")

    def show_scale_details(self):
        if not self.viewer.scale_factors:
            QMessageBox.information(self, "Aucune échelle", "Aucune référence d’échelle disponible.")
        else:
            details = "\n".join([f"{i+1}: {s:.5f}" for i, s in enumerate(self.viewer.scale_factors)])
            moyenne = np.mean(self.viewer.scale_factors)
            QMessageBox.information(self, "Détails de l’échelle", f"{details}\n\nMoyenne : {moyenne:.5f}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())