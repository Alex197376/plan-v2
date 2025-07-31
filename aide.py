# aide.py
from PyQt6.QtWidgets import QMessageBox

def afficher_aide(parent):
    message = """
<b>Mode Mesure :</b><br>
Permet de tracer une distance entre deux points sur l’image.<br>
▶ Cliquez une première fois pour le point de départ.<br>
▶ Cliquez une seconde fois pour le point d’arrivée.<br>
▶ Si au moins 3 références sont définies, l’échelle est automatiquement calculée.<br><br>

<b>Mode Surface simple :</b><br>
Permet de calculer une surface rectangulaire.<br>
▶ Cliquez deux points pour la longueur, puis validez ou modifiez.<br>
▶ Cliquez deux autres points pour la largeur, puis validez ou modifiez.<br>
▶ La surface est calculée automatiquement.<br><br>

<b>Mode Surface complexe :</b><br>
Permet de calculer la surface d’un polygone libre.<br>
▶ Cliquez pour chaque point de la forme.<br>
▶ Cliquez près du premier point pour fermer.<br>
▶ Clic droit : supprime le dernier point ajouté.<br><br>

<b>Références :</b><br>
▶ Les références sont des mesures réelles que vous entrez.<br>
▶ Vous pouvez modifier les références par double-clic dans la liste.<br>
▶ Le recalcul d’échelle se fait automatiquement après modification.<br><br>

<b>Autres boutons :</b><br>
• Recalculer échelle : recalcul manuel si besoin<br>
• Voir détails échelle : affiche les références utilisées<br>
• Réinitialiser échelle : supprime toutes les références<br>
    """
    QMessageBox.information(parent, "Aide - Mode d'emploi", message)
