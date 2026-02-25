# Funzione di stile per i confini dei comuni
def style_function(feature):
    return {
        "fillColor": "grey",  # Colore di riempimento (bianco)
        "color": "black",  # Colore del contorno (nero)
        "weight": 2,  # Spessore del contorno
        "dashArray": "2, 8",  # Linea tratteggiata (opzionale)
        "fillOpacity": 0.1,  # Opacità del riempimento
    }


def player_style_function(feature, a, b):
    return {
        "fillColor": "green",  # Colore di riempimento (bianco)
        "color": "black",  # Colore del contorno (nero)
        "weight": 2,  # Spessore del contorno
        # 'dashArray': '5, 5',         # Linea tratteggiata (opzionale)
        "fillOpacity": 0.15 + (a / b) * 0.85,  # Opacità del riempimento
    }
